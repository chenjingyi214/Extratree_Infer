import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# 表单路径只填检验原始值（归一化值留空由模型填补），基准得分与 CSV 路径不同，
# 以下为实测值（详见 README 第 7 节）。
EXAMPLE_FY13 = {
    "age": 91,
    "gender": "女",
    "symptoms": {
        "乏力": True, "低热": True, "呼吸困难": True, "咳嗽": True,
        "头晕/疼": True, "憋气": True, "气短": True, "意识模糊/嗜睡": True,
    },
    "labs": {
        "白细胞计数": 6.93, "红细胞比容": 35.4, "淋巴细胞计数": 1.3,
        "单核细胞计数": 0.43, "中性粒细胞计数": 5.06, "血小板分布宽度": 10.8,
        "血小板计数": 137, "淀粉样蛋白A": 11.273, "C反应蛋白": 2.2,
    },
}

EXAMPLE_SG106 = {
    "age": 68,
    "gender": "男",
    "symptoms": {},
    "labs": {
        "白细胞计数": 11.46, "红细胞比容": 38.2, "淋巴细胞计数": 2.5,
        "单核细胞计数": 0.56, "中性粒细胞计数": 8.19, "血小板分布宽度": 16.8,
        "血小板计数": 215, "淀粉样蛋白A": 38.333, "C反应蛋白": 14.0,
        "肺炎支原体抗体.IgM": "阴性",
    },
}


def _single(result_json):
    patients = result_json["patients"]
    assert len(patients) == 1
    return patients[0]


def test_form_example_pneumonia_patient():
    resp = client.post("/api/predict/form", json=EXAMPLE_FY13, params={"threshold": 0.16})
    assert resp.status_code == 200
    patient = _single(resp.json())
    assert patient["score"] == pytest.approx(0.7125, abs=1e-6)
    assert patient["label"] == "肺炎"
    assert patient["detail"]["age"] == 91.0
    assert patient["detail"]["gender"] == "女"
    assert set(patient["detail"]["symptoms_positive"]) == set(EXAMPLE_FY13["symptoms"])
    measured = {lab["name"]: lab["measured"] for lab in patient["detail"]["labs"]}
    assert measured["白细胞计数"] is True
    assert measured["肺炎支原体抗体.IgM"] is False


def test_form_example_uri_patient():
    resp = client.post("/api/predict/form", json=EXAMPLE_SG106, params={"threshold": 0.16})
    assert resp.status_code == 200
    patient = _single(resp.json())
    assert patient["score"] == pytest.approx(0.155, abs=1e-6)
    assert patient["label"] == "上感"
    igm = next(lab for lab in patient["detail"]["labs"] if lab["name"] == "肺炎支原体抗体.IgM")
    assert igm["measured"] is True
    assert igm["positive"] is False


def test_form_minimal_payload_only_age_and_gender():
    resp = client.post("/api/predict/form", json={"age": 50, "gender": "男"}, params={"threshold": 0.16})
    assert resp.status_code == 200
    patient = _single(resp.json())
    assert patient["label"] == "上感"
    assert patient["detail"]["symptoms_positive"] == []
    assert all(lab["measured"] is False for lab in patient["detail"]["labs"])


def test_form_without_threshold_has_null_label():
    resp = client.post("/api/predict/form", json={"age": 50, "gender": "男"})
    assert resp.status_code == 200
    assert _single(resp.json())["label"] is None


def test_form_derives_ratios_and_indices_from_counts():
    resp = client.post("/api/predict/form", json=EXAMPLE_FY13, params={"threshold": 0.16})
    assert resp.status_code == 200
    labs = {lab["name"]: lab for lab in _single(resp.json())["detail"]["labs"]}
    assert labs["单核细胞/淋巴细胞比值"]["value"] == pytest.approx(0.43 / 1.3)
    assert labs["中性粒细胞/淋巴细胞比值"]["value"] == pytest.approx(5.06 / 1.3)
    assert labs["血小板/淋巴细胞比值"]["value"] == pytest.approx(137 / 1.3)
    assert labs["系统性免疫炎症指数"]["value"] == pytest.approx(137 * 5.06 / 1.3)
    assert labs["系统性炎症反应指数"]["value"] == pytest.approx(5.06 * 0.43 / 1.3)


def test_form_derived_labs_unmeasured_without_lymphocyte_count():
    payload = {"age": 50, "gender": "男", "labs": {"白细胞计数": 8.0, "淋巴细胞计数": 0}}
    resp = client.post("/api/predict/form", json=payload, params={"threshold": 0.16})
    assert resp.status_code == 200
    labs = {lab["name"]: lab for lab in _single(resp.json())["detail"]["labs"]}
    assert labs["中性粒细胞/淋巴细胞比值"]["measured"] is False
    assert labs["系统性免疫炎症指数"]["measured"] is False


@pytest.mark.parametrize(
    "payload, message",
    [
        ({"gender": "男"}, "年龄必填"),
        ({"age": "abc", "gender": "男"}, "年龄必填"),
        ({"age": 0, "gender": "男"}, "0 到 150"),
        ({"age": 50}, "性别必填"),
        ({"age": 50, "gender": "未知"}, "性别必填"),
        ({"age": 50, "gender": "男", "symptoms": {"打呼": True}}, "未登记的症状名称"),
        ({"age": 50, "gender": "男", "labs": {"血糖": 5.0}}, "未登记的检验项目"),
        ({"age": 50, "gender": "男", "labs": {"白细胞计数": "很多"}}, "必须是数值"),
        ({"age": 50, "gender": "男", "labs": {"肺炎支原体抗体.IgM": "不确定"}}, "阳性/阴性"),
    ],
)
def test_form_validation_errors(payload, message):
    resp = client.post("/api/predict/form", json=payload)
    assert resp.status_code == 400
    assert message in resp.json()["detail"]


def test_form_rejects_out_of_range_threshold():
    resp = client.post("/api/predict/form", json={"age": 50, "gender": "男"}, params={"threshold": 1.5})
    assert resp.status_code == 400
