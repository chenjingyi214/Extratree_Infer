"""FastAPI entry point for the CAP ExtraTrees web UI."""

from __future__ import annotations

from pathlib import Path

from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles

from app import service

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="CAP ExtraTrees 推理服务")


def _validate_threshold(threshold: float | None) -> float | None:
    if threshold is not None and not 0 <= threshold <= 1:
        raise HTTPException(status_code=400, detail="threshold 必须在 0 到 1 之间")
    return threshold


def _run_or_400(func, *args):
    try:
        return func(*args)
    except HTTPException:
        raise
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail="模型加载失败，请联系管理员") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (FileNotFoundError, OSError) as exc:
        raise HTTPException(status_code=500, detail="服务内部错误，请联系管理员") from exc


@app.post("/api/predict/form")
async def predict_form(
    payload: dict = Body(...),
    threshold: float | None = Query(default=None),
):
    threshold = _validate_threshold(threshold)
    return _run_or_400(service.run_form_prediction, payload, threshold)


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
