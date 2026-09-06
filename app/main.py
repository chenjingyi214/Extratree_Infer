"""FastAPI entry point for the CAP ExtraTrees web UI."""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import service

MAX_UPLOAD_BYTES = 20 * 1024 * 1024
STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="CAP ExtraTrees 推理服务")


def _validate_threshold(threshold: float | None) -> float | None:
    if threshold is not None and not 0 <= threshold <= 1:
        raise HTTPException(status_code=400, detail="threshold 必须在 0 到 1 之间")
    return threshold


async def _save_upload(upload: UploadFile, directory: Path, field_name: str) -> Path:
    filename = upload.filename or ""
    if not filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail=f"{field_name} 必须是 CSV 文件")
    content = await upload.read()
    if not content:
        raise HTTPException(status_code=400, detail=f"{field_name} 内容为空")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail=f"{field_name} 超过 20MB 限制")
    path = directory / f"{field_name}.csv"
    path.write_bytes(content)
    return path


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


@app.post("/api/predict")
async def predict(
    symptom_file: UploadFile,
    lab_file: UploadFile,
    threshold: float | None = Query(default=None),
):
    threshold = _validate_threshold(threshold)
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        symptom_path = await _save_upload(symptom_file, tmp, "symptom_file")
        lab_path = await _save_upload(lab_file, tmp, "lab_file")
        return _run_or_400(service.run_prediction, symptom_path, lab_path, threshold)


@app.post("/api/predict/demo")
async def predict_demo(threshold: float | None = Query(default=None)):
    threshold = _validate_threshold(threshold)
    return _run_or_400(service.run_demo, threshold)


@app.get("/api/demo/files/{kind}")
async def demo_file(kind: str):
    paths = {"symptoms": service.DEMO_SYMPTOMS_PATH, "labs": service.DEMO_LABS_PATH}
    path = paths.get(kind)
    if path is None:
        raise HTTPException(status_code=404, detail="未知的示例文件类型")
    return FileResponse(path, media_type="text/csv", filename=path.name)


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
