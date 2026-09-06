# CAP ExtraTrees 推理 Web UI 设计文档

日期：2026-09-06
状态：已与用户确认

## 背景与目标

当前项目是一个纯 CLI 的肺炎/上感二分类推理包（`preprocessing.py` + `infer.py` + 冻结的
ExtraTrees 权重）。目标是新增一个**简洁美观的单页 Web 界面**，让用户上传原始症状/检验
CSV 后在浏览器中完成预处理与推理，并查看患者级得分与特征详情。

本项目没有现有后端，需要新增一层 FastAPI 服务包装现有脚本；现有两个脚本**不做任何修改**，
API 层只 import 其函数并组装结果。

## 已确认的决策

- 输入方式：上传两张原始 CSV（症状长表 + 检验长表）
- 结果展示：批量结果表格 + 点击行查看患者详情
- 技术栈：FastAPI + 免构建单页（HTML + 原生 JS + CSS），FastAPI 直接托管静态文件
- 阈值：页面提供可调阈值输入（默认 0.16），超过阈值标"肺炎"并高亮，同时始终显示原始得分
- 工作流：一步式单页（方案 A），另有"载入示例数据"按钮
- 示例模式：展示样例 CSV 内容预览（作为格式模板）+ 下载链接 + 自动跑推理出结果

## 1. 页面布局与交互

- 顶部：标题 + 一句话说明（"基于 ExtraTrees 的肺炎/上感辅助评分，结果非诊断结论"）
- 输入卡片：
  - 两个文件上传区（症状 CSV / 检验 CSV，支持拖拽与点击选择）
  - 阈值输入框（默认 0.16，范围 0–1）
  - "载入示例数据"、"开始分析"按钮
- 示例模式：点击"载入示例数据"后显示两份样例 CSV 的前 5 行预览（表格形式）+
  下载链接，并自动调用推理接口展示结果
- 结果区：患者表格（patient_id、得分、按阈值判断的标签——"肺炎"红色高亮 / "上感"绿色），
  支持按得分排序，可导出预测 CSV
- 患者详情：点击表格行展开侧栏/抽屉，显示年龄、性别、阳性症状列表、检验值表
  （含"未测量"标记）
- 页面常驻免责声明：得分为非校准模型输出，不能替代医生诊断
- 视觉：浅色背景、卡片式布局、医疗感蓝绿主色、大号得分数字；免构建
  （HTML + 原生 JS + CSS），静态文件由 FastAPI 托管

## 2. API 契约

API 层直接 import `preprocessing.run_preprocessing` 与 `infer.py` 中的加载/打分逻辑
（`load_feature_names`、`prepare_features`、`positive_scores`），不启动子进程。
上传内容写入临时文件后再调用（`run_preprocessing` 需要文件路径），响应后清理。

### `POST /api/predict`

- 请求：multipart 表单，`symptom_file` + `lab_file`（均为 CSV，单个 ≤ 20MB）；
  query 参数 `threshold`（可选，0–1，默认 0.16）
- 内部流程：`run_preprocessing()` → 58 特征 DataFrame → 复用 infer 的校验与打分
- 响应 200：

```json
{
  "patients": [
    {
      "patient_id": "KJSQ-FY-13",
      "score": 0.80375,
      "label": "肺炎",
      "detail": {
        "age": 91.0,
        "gender": "女",
        "symptoms_positive": ["咳嗽", "低热"],
        "labs": [
          { "name": "白细胞计数", "measured": true, "value": 6.93, "normalized": 0.5717, "positive": null }
        ]
      }
    }
  ]
}
```

- 未传 `threshold` 时 `label` 为 `null`；症状/检验展示名使用中文（通过
  preprocessing 中既有的 `SYMPTOM_NAME_MAP` / `LAB_NAME_MAP` 反向映射）

### `POST /api/predict/demo`

- 无输入；用内置 `test_cases_raw_symptoms.csv` / `test_cases_raw_labs.csv` 跑同样流程
- 响应在 `/api/predict` 结构基础上额外包含：
  `symptoms_preview` 和 `labs_preview`（两张 CSV 的前 5 行，按列数组形式返回）

### `GET /api/demo/files/{symptoms|labs}`

- 下载对应的示例 CSV 文件

## 3. 错误处理

- 预处理/推理现有的 `ValueError`（缺列、无法解析的值、未登记的症状名、患者 ID 冲突等）
  统一转为 400，前端在输入卡片下方以红条显示中文错误消息
- 文件非 `.csv` 后缀或超过 20MB：400；阈值越界：400
- 模型文件缺失或 joblib 反序列化失败：500 + 通用提示（不向客户端暴露堆栈）
- 前端对网络失败、空结果（0 位患者）分别给出明确提示

## 4. 项目结构与运行

```text
Extratree_infer/
├── preprocessing.py          # 不改动
├── infer.py                  # 不改动
├── app/
│   ├── main.py               # FastAPI 应用与上述三个端点
│   └── static/
│       ├── index.html
│       ├── app.js
│       └── style.css
```

- 依赖：requirements.txt 追加固定版本的 `fastapi`、`uvicorn`、`python-multipart`
  （上传需要）；复用现有 `.venv`
- 启动：`cd Extratree_infer && .venv/bin/uvicorn app.main:app --port 8000`
- 验证标准：示例数据走通页面与 API，得分与 `test_cases_reference.csv` 一致
  （0.80375 / 0.035625，小数点后 6 位以内）；手工上传同两份 CSV 结果一致

## 非目标（YAGNI）

- 不做手工填写表单录入、不做历史批次记录、不做用户体系与权限
- 不做模型重训练、校准、临床决策支持
- 不引入 node 构建链
