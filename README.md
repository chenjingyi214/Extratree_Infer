# ExtraTrees 独立预处理与推理包

本目录可独立完成两步流程：先把原始症状长表和检验长表转换为模型要求的 58 个特征，再使用冻结的 ExtraTrees 权重计算肺炎类得分。

模型目标是二分类：`target=1` 表示肺炎，`target=0` 表示上感。输出的 `pneumonia_score` 是模型得分，不是经过校准的临床概率，也不能替代医生诊断。

## 目录内容

| 文件 | 用途 |
| --- | --- |
| `preprocessing.py` | 将原始症状、检验长表转换为患者级 58 特征 CSV |
| `infer.py` | 读取 58 特征 CSV 并运行冻结的 ExtraTrees 模型 |
| `extra_trees_sqrt_logloss.joblib` | 正式 ExtraTrees Pipeline 权重（800 棵树） |
| `feature_list.json` | 模型要求的 58 个特征及其固定顺序 |
| `feature_name_mapping.csv` | 58 个特征的中文含义、来源和编码规则 |
| `test_cases_raw_symptoms.csv` | 从测试集抽取的两位患者原始症状记录 |
| `test_cases_raw_labs.csv` | 同两位患者的原始检验记录 |
| `test_cases_reference.csv` | 样例来源、真实标签和预期得分，仅用于核对 |
| `requirements.txt` | 与当前权重兼容的 Python 依赖版本 |
| `app/` | FastAPI 后端 + 问卷式单页前端（Web 界面，见"快速开始"） |
| `tests/` | Web API 的 pytest 测试 |

## 快速开始（Web 界面）

需要 64 位 Python 3.11。推荐使用 [uv](https://docs.astral.sh/uv/) 创建环境：

```bash
cd Extratree_infer
uv venv --python 3.11 .venv
UV_HTTP_TIMEOUT=180 uv pip install --python .venv/bin/python -r requirements.txt
```

（也可以按第 1 节用标准 venv + pip 安装；依赖版本必须固定，否则模型权重可能无法加载或结果漂移。）

启动服务：

```bash
.venv/bin/uvicorn app.main:app --port 8000
```

浏览器打开 **http://127.0.0.1:8000**，在问卷表单中填写患者信息并提交：

- **必填**：年龄、性别
- **选填**：13 项症状（默认"无"）、10 项检验（没测留空即可，由模型内置规则填补）；
  单核/淋巴、中性粒/淋巴、血小板/淋巴三个比值与系统性免疫炎症指数（SII）、
  系统性炎症反应指数（SIRI）无需填写，由基础计数按训练数据的公式自动计算
- 「示例·肺炎患者」按钮可一键填入样例数据后提交

停止服务：在终端按 `Ctrl+C`。

运行测试（可选）：

```bash
.venv/bin/python -m pytest tests/ -q
```

第 1–6 节为命令行（CLI）用法与数据格式说明，Web 界面不影响这些既有功能。

数据流如下：

```text
原始症状 CSV + 原始检验 CSV
              |
              v
      preprocessing.py
              |
              v
 preprocessed_features.csv（58特征）
              |
              v
          infer.py
              |
              v
        肺炎类模型得分
```

## 1. 安装环境

建议使用 64 位 Python 3.11。权重是在 Python 3.11、scikit-learn 1.9.0 环境中保存的；为避免 Joblib 反序列化失败或结果漂移，请使用 `requirements.txt` 中的固定版本。

### macOS / Linux

```bash
cd Extratree_infer
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Windows PowerShell

```powershell
cd Extratree_infer
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

检查版本：

```bash
python --version
python -c "import joblib, numpy, pandas, sklearn, scipy; print(joblib.__version__, numpy.__version__, pandas.__version__, sklearn.__version__, scipy.__version__)"
```

## 2. 使用两条原始样例运行

必须先运行预处理，再运行推理。

### 第一步：原始数据转为 58 个特征

直接运行：

```bash
python preprocessing.py
```

默认读取：

- `test_cases_raw_symptoms.csv`
- `test_cases_raw_labs.csv`

默认生成：

- `preprocessed_features.csv`

成功时会显示：

```text
已写入: .../preprocessed_features.csv（2 位患者，58 个特征）
```

### 第二步：运行 ExtraTrees 推理

```bash
python infer.py
```

`infer.py` 默认读取上一步生成的 `preprocessed_features.csv`，并把结果写到终端。结果应接近：

```text
patient_id,pneumonia_score
KJSQ-FY-13,0.80375
KJSQ-SG-106,0.035625
```

保存预测结果：

```bash
python infer.py --output predictions.csv
```

完整指定两步的输入输出路径：

```bash
python preprocessing.py \
  --symptom-input test_cases_raw_symptoms.csv \
  --lab-input test_cases_raw_labs.csv \
  --output test_cases_features.csv

python infer.py \
  --input test_cases_features.csv \
  --output predictions.csv
```

查看全部参数：

```bash
python preprocessing.py --help
python infer.py --help
```

## 3. 准备自己的原始输入

预处理器接收两张 UTF-8 CSV 长表。一条症状或检验记录占一行；同一患者可有多行。两张表通过患者 ID 合并，患者最终在输出中只占一行。

### 3.1 症状 CSV 必需字段

| 字段 | 含义与允许值 |
| --- | --- |
| `PatientID` | 患者唯一标识，不得为空 |
| `Gender` | `男/女`、`male/female`、`m/f` 或 `1/0` |
| `Age` | 年龄，单位为岁，必须可转为数值 |
| `症状与体征-中文` | 原始症状名称 |
| `查体结果` | `是/否`、`有/无`、`阳性/阴性`、`1/0`、`true/false` 等 |

支持的 13 个症状名称：

```text
乏力、低热、呼吸困难、咳嗽、咳痰、喷嚏、头晕/疼、憋气、气短、
流涕、胸痛、鼻塞、意识模糊/嗜睡
```

同一患者、同一症状有多条记录时取最大值，即任一记录为阳性则该症状为 `1`。没有对应症状行或结果留空时按 `0` 处理。三个系统汇总特征由成员症状的最大值生成：

- 呼吸系统：咳嗽、咳痰、呼吸困难、憋气、气短、胸痛。
- 上气道：喷嚏、流涕、鼻塞。
- 全身：乏力、低热、头晕/疼、意识模糊/嗜睡。

样例中的 `Hospital` 和 `Target` 是原始测试集附带字段，预处理和推理均不会使用它们。

### 3.2 检验 CSV 必需字段

| 字段 | 含义 |
| --- | --- |
| `patientId` | 患者标识，与症状表的 `PatientID` 对应 |
| `gender` | 性别，编码规则同症状表 |
| `age` | 年龄，单位为岁 |
| `resultDateTime` | 结果时间，可为空 |
| `reportDateTime` | 报告时间，可为空；优先作为记录排序时间 |
| `laboratoryName` | 标准检验项目名 |
| `standardResult` | 标准化后的结果；定量结果的后备数值来源 |
| `standardResultNorm` | 标准化结果；定量时优先取数值，定性时用于判断阳性/阴性 |
| `standardNormalizedQuantitative` | 按参考区间归一化的定量结果，可为空 |
| `abnormal` | 异常标记；定性结果无法识别时作为后备来源 |
| `standardResultType` | `QUANTIFY` 或 `QUALITATIVE` |

模型固定使用以下 15 个检验项目：

```text
C反应蛋白、红细胞比容、淋巴细胞计数、单核细胞计数、
单核细胞/淋巴细胞比值、肺炎支原体抗体.IgM、中性粒细胞计数、
中性粒细胞/淋巴细胞比值、血小板计数、血小板分布宽度、
血小板/淋巴细胞比值、淀粉样蛋白A、系统性免疫炎症指数、
系统性炎症反应指数、白细胞计数
```

其他检验项目可以保留在原始 CSV 中，预处理器会忽略。每位患者、每个模型检验项目只保留最新有效记录：优先按 `reportDateTime` 排序，缺失时使用 `resultDateTime`，时间相同时保留文件中靠后的记录。

检验特征编码规则：

| 特征组 | 生成规则 |
| --- | --- |
| `lab_measured_*` | 有有效检验记录为 `1`，无记录为 `0` |
| `lab_value_*` | 定量记录优先取 `standardResultNorm` 数值，否则取 `standardResult` 数值 |
| `lab_normalized_*` | 取 `standardNormalizedQuantitative` |
| `lab_positive_*` | 定性结果阳性为 `1`，阴性为 `0`，无法判定或未测量为空 |

部署时使用训练阶段已经固定的 15 个检验项目和 58 列顺序。脚本不会在新数据上重新计算“检验缺失率小于等于 40%”的筛选规则，否则不同批次会生成不同的模型输入结构。

### 3.3 运行自己的数据

```bash
python preprocessing.py \
  --symptom-input my_raw_symptoms.csv \
  --lab-input my_raw_labs.csv \
  --output my_features.csv

python infer.py \
  --input my_features.csv \
  --output my_predictions.csv
```

预处理输出中的数值缺失会保留为空。不要在模型外自行用均值、0 或其他规则填补，因为保存的模型 Pipeline 已包含：

```text
SimpleImputer(strategy="median", add_indicator=True)
-> VarianceThreshold(threshold=0)
-> ExtraTreesClassifier(criterion="log_loss", n_estimators=800, max_features="sqrt")
```

## 4. 可选分类阈值

默认只输出模型得分。如需把得分转换为标签，必须显式指定阈值。例如：

```bash
python infer.py \
  --input preprocessed_features.csv \
  --threshold 0.16 \
  --output predictions_with_label.csv
```

输出会增加：

```text
threshold,predicted_label,predicted_class
0.16,1,肺炎
0.16,0,上感
```

项目中曾基于完整内部测试集的 Youden 指数选择过 `0.16`，但该阈值不是独立验证后的临床推荐值。默认不设置阈值是为了避免把模型分数误读为直接诊断结果。

## 5. 样例来源和复现核对

两组原始样例均来自正式模型的 `external_test_kjsq`，且在正式训练中 `included_in_training=False`：

| patient_id | 真实标签 | 预期得分 |
| --- | ---: | ---: |
| `KJSQ-FY-13` | 1（肺炎） | 0.80375 |
| `KJSQ-SG-106` | 0（上感） | 0.035625 |

`test_cases_reference.csv` 只用于人工核对，预处理和推理都不会读取真实标签。相同依赖版本和权重下，得分应与上表一致到小数点后 6 位以内。

## 6. 安全与方法学限制

- `joblib.load` 会反序列化 Python 对象，只应加载可信的 `extra_trees_sqrt_logloss.joblib`。
- ExtraTrees 输出没有做概率校准；`pneumonia_score=0.8` 不应直接解释为“80% 患病概率”。
- 本包不负责从医院原始单位和参考区间重新清洗检验结果，也不包含重新训练、模型校准、临床决策支持或数据脱敏流程。

## 7. Web 界面（可选）

安装依赖后启动本地服务：

```bash
.venv/bin/uvicorn app.main:app --port 8000
```

浏览器打开 http://127.0.0.1:8000 即可在问卷式表单中手填单例患者数据并查看评分结果：
年龄和性别为必填，症状默认为"无"，检验项目没测可留空（由模型内置中位数填补）；
"示例·肺炎患者 / 示例·上感患者"按钮可一键填入样例数据。Web 层把表单内容重建为
症状/检验长表后调用 `preprocessing.py` 与 `infer.py` 的既有逻辑，不改变模型行为。

注意：表单只填检验原始值，原 CSV 中的归一化列（`standardNormalizedQuantitative`）
在表单路径下为空并被模型填补，因此示例患者走表单的得分（0.7125 / 0.155）与第 5 节
CSV 路径的参考得分（0.80375 / 0.035625）不同，两者均为各自输入下的正确输出。
