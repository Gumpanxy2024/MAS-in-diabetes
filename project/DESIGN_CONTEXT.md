```markdown
# 系统设计摘要（第四章精华）— Cursor协作上下文

## 一、技术栈

- 后端：Python 3.x + Django 4.x
- Agent编排：LangGraph
- 数据库：SQLite（开发）/ MySQL（生产）
- 前端：Django Template + HTML/CSS/JS
- LLM：大语言模型API（语音文本 → 结构化JSON）

---

## 二、项目目录结构（建议）

```
cdm_system/
├── manage.py
├── cdm_system/                # Django项目配置
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── accounts/                  # 用户认证模块
│   ├── models.py
│   ├── views.py
│   └── templates/accounts/
├── patients/                  # 患者端（健康数据 + 打卡）
│   ├── models.py              # Patient, HealthRecord, MedicationRecord
│   ├── views.py
│   └── templates/patients/
├── doctors/                   # 医生端（工作台 + 档案管理）
│   ├── models.py              # Doctor, VisitTask, MedicationPlan
│   ├── views.py
│   └── templates/doctors/
├── agents/                    # 五个核心Agent
│   ├── patient_agent.py
│   ├── triage_agent.py
│   ├── scheduler_agent.py
│   ├── doctor_agent.py
│   ├── medication_agent.py
│   ├── graph.py               # LangGraph有向图定义
│   └── state.py               # SystemState定义
├── risk/                      # 风险评估模块
│   └── models.py              # RiskRecord
└── static/                    # CSS/JS/图片
```

---

## 三、七张核心数据表

### 3.1 Patient（患者表）

| 字段名 | 数据类型 | 约束 | 说明 |
|---|---|---|---|
| patient_id | INT | PK, AUTO_INCREMENT | 患者唯一标识 |
| doctor_id | INT | FK → Doctor, NOT NULL | 责任医生ID |
| name | VARCHAR(50) | NOT NULL | 患者姓名 |
| age | INT | NOT NULL | 年龄 |
| gender | VARCHAR(4) | NOT NULL | 性别（男/女） |
| diagnosis_year | INT | NOT NULL | 确诊2型糖尿病年份 |
| phone | VARCHAR(20) | NOT NULL | 联系电话 |
| account | VARCHAR(50) | UNIQUE, NOT NULL | 登录账号 |
| password_hash | VARCHAR(128) | NOT NULL | 密码哈希值 |
| is_active | BOOLEAN | DEFAULT TRUE | 在管状态 |
| created_at | DATETIME | AUTO_NOW_ADD | 建档时间 |

### 3.2 Doctor（医生表）

| 字段名 | 数据类型 | 约束 | 说明 |
|---|---|---|---|
| doctor_id | INT | PK, AUTO_INCREMENT | 医生唯一标识 |
| name | VARCHAR(50) | NOT NULL | 姓名 |
| phone | VARCHAR(20) | NOT NULL | 联系电话 |
| account | VARCHAR(50) | UNIQUE, NOT NULL | 登录账号 |
| password_hash | VARCHAR(128) | NOT NULL | 密码哈希值 |
| created_at | DATETIME | AUTO_NOW_ADD | 创建时间 |

### 3.3 HealthRecord（健康记录表）

| 字段名 | 数据类型 | 约束 | 说明 |
|---|---|---|---|
| record_id | INT | PK, AUTO_INCREMENT | 记录唯一标识 |
| patient_id | INT | FK → Patient, NOT NULL | 所属患者 |
| fasting_glucose | DECIMAL(4,1) | NULL | 空腹血糖 mmol/L |
| postmeal_glucose | DECIMAL(4,1) | NULL | 餐后2h血糖 mmol/L |
| systolic_bp | INT | NULL | 收缩压 mmHg |
| diastolic_bp | INT | NULL | 舒张压 mmHg |
| weight | DECIMAL(4,1) | NULL | 体重 kg |
| input_type | VARCHAR(10) | NOT NULL | 录入方式 voice/text |
| recorded_at | DATETIME | NOT NULL | 录入时间 |

### 3.4 RiskRecord（风险评估记录表）

| 字段名 | 数据类型 | 约束 | 说明 |
|---|---|---|---|
| risk_id | INT | PK, AUTO_INCREMENT | 评估唯一标识 |
| patient_id | INT | FK → Patient, NOT NULL | 所属患者 |
| health_record_id | INT | FK → HealthRecord, NOT NULL | 关联健康记录 |
| risk_level | VARCHAR(10) | NOT NULL | green/yellow/red |
| risk_score | DECIMAL(3,2) | NOT NULL | 加权评分值 |
| trigger_indicators | TEXT(JSON) | NULL | 异常指标JSON列表 |
| evaluated_at | DATETIME | AUTO_NOW_ADD | 评估时间 |

### 3.5 VisitTask（随访任务表）

| 字段名 | 数据类型 | 约束 | 说明 |
|---|---|---|---|
| task_id | INT | PK, AUTO_INCREMENT | 任务唯一标识 |
| patient_id | INT | FK → Patient, NOT NULL | 所属患者 |
| doctor_id | INT | FK → Doctor, NOT NULL | 负责医生 |
| visit_type | VARCHAR(20) | NOT NULL | online/offline/home |
| priority | VARCHAR(10) | DEFAULT 'normal' | normal/urgent |
| due_date | DATE | NOT NULL | 截止日期 |
| status | VARCHAR(20) | DEFAULT 'pending' | pending/completed/deferred |
| remark | TEXT | NULL | 随访备注 |
| created_at | DATETIME | AUTO_NOW_ADD | 创建时间 |
| completed_at | DATETIME | NULL | 完成时间 |

### 3.6 MedicationPlan（用药方案表）

| 字段名 | 数据类型 | 约束 | 说明 |
|---|---|---|---|
| plan_id | INT | PK, AUTO_INCREMENT | 方案唯一标识 |
| patient_id | INT | FK → Patient, NOT NULL | 所属患者 |
| drug_name | VARCHAR(100) | NOT NULL | 药品名称 |
| dosage | VARCHAR(50) | NOT NULL | 剂量如500mg |
| frequency | VARCHAR(20) | NOT NULL | 每日服药频次 |
| remind_times | VARCHAR(100) | NOT NULL | 提醒时间如08:00,20:00 |
| total_days | INT | NOT NULL | 处方总天数 |
| start_date | DATE | NOT NULL | 方案起始日期 |
| is_active | BOOLEAN | DEFAULT TRUE | 是否生效 |
| created_at | DATETIME | AUTO_NOW_ADD | 创建时间 |

### 3.7 MedicationRecord（用药打卡记录表）

| 字段名 | 数据类型 | 约束 | 说明 |
|---|---|---|---|
| record_id | INT | PK, AUTO_INCREMENT | 打卡唯一标识 |
| plan_id | INT | FK → MedicationPlan, NOT NULL | 所属方案 |
| patient_id | INT | FK → Patient, NOT NULL | 所属患者 |
| scheduled_time | DATETIME | NOT NULL | 计划服药时间 |
| checked_at | DATETIME | NULL | 实际打卡时间 |
| status | VARCHAR(10) | NOT NULL | taken/missed/skipped |

---

## 四、SystemState定义

```python
from typing import TypedDict, Optional
from datetime import date

class SystemState(TypedDict):
    patient_id: int
    patient_name: str           # 冗余缓存，避免Agent内重复查库
    health_record: dict         # PatientAgent解析后的结构化体征数据
    risk_level: str             # green / yellow / red
    risk_score: float           # 加权风险评分值
    trigger_indicators: list    # 触发预警的异常指标列表
    visit_task_id: int          # SchedulerAgent创建/更新的任务ID
    next_visit_date: str        # 下次随访日期 YYYY-MM-DD
    medication_alert: bool      # 是否触发续方提醒
    flow_log: list              # 各Agent执行日志
```

---

## 五、Agent职责与接口

| Agent | 入口方法 | 输入来源 | 输出到state | 触发下游 |
|---|---|---|---|---|
| PatientAgent | run(state) → state | 原始文本或表单数据 | health_record | → TriageAgent |
| TriageAgent | run(state) → state | state.health_record | risk_level, risk_score, trigger_indicators | → SchedulerAgent（等级变更时） |
| SchedulerAgent | run(state) → state | state.risk_level, patient_id | visit_task_id, next_visit_date | → DoctorAgent |
| DoctorAgent | run(state) → state | 预警/任务/续方通知 | 更新看板数据 | → END |
| MedicationAgent | run_reminder_task() | 定时触发（独立路径） | medication_alert | → DoctorAgent（续方时） |

---

## 六、LangGraph有向图结构

### 主流程（健康数据录入触发）
```
START → PatientAgent → TriageAgent → [条件：风险等级变更？]
  ├─ 是 → SchedulerAgent → DoctorAgent → END
  └─ 否 → DoctorAgent → END
```

### 用药路径（定时任务触发）
```
START → MedicationAgent → [条件：剩余药量 ≤ 阈值？]
  ├─ 是 → DoctorAgent → END
  └─ 否 → END
```

---

## 七、风险评分规则

### 各指标评分区间

| 指标 | 绿色(1分) | 黄色(2分) | 红色(3分) | 权重 |
|---|---|---|---|---|
| 空腹血糖 mmol/L | < 7.0 | 7.0 ~ 13.9 | >= 13.9 | 0.35 |
| 餐后2h血糖 mmol/L | < 10.0 | 10.0 ~ 16.7 | >= 16.7 | 0.25 |
| 收缩压 mmHg | < 130 | 130 ~ 160 | >= 160 | 0.20 |
| 舒张压 mmHg | < 80 | 80 ~ 100 | >= 100 | 0.10 |
| BMI | < 24 | 24 ~ 28 | >= 28 | 0.10 |

### 等级映射
- 加权总分 < 1.5 → 绿码（正常）
- 加权总分 1.5 ~ 2.2 → 黄码（警示）
- 加权总分 > 2.2 → 红码（危险）

---

## 八、随访周期规则

| 风险等级 | 随访方式 | 随访周期 |
|---|---|---|
| 绿码 | 线上轻问诊（online） | 30天 |
| 黄码 | 线上轻问诊（online） | 14天 |
| 红码 | 线下门诊/上门巡诊（offline/home） | 立即生成紧急任务 |

---

## 九、续方预警规则

- 剩余天数 = start_date + total_days - 当前日期
- 阈值：剩余天数 <= 3天 触发续方预警
- 续方后：start_date重置为当日，total_days恢复处方总天数

---

## 十、LLM Prompt模板（PatientAgent语音解析）

```
你是一个医疗数据解析助手。请从以下患者口述文字中提取体征数据，
以JSON格式输出，字段包括：
- fasting_glucose（空腹血糖，单位mmol/L）
- postmeal_glucose（餐后血糖，单位mmol/L）
- systolic_bp（收缩压，单位mmHg）
- diastolic_bp（舒张压，单位mmHg）
- weight（体重，单位kg）
若某字段未提及，值填null。仅输出JSON，不要任何解释。
患者描述：{input_text}
```

---

## 十一、依从率计算公式

```
依从率 = 实际打卡次数(status=taken) / 应打卡总次数 × 100%
```

---

## 十二、功能模块与处理组件对应

| 功能模块 | 处理组件 | 备注 |
|---|---|---|
| 用户认证 | Django View | 无Agent |
| 健康数据管理 | PatientAgent | 语音/文字录入 + 趋势图 |
| 风险评估与预警 | TriageAgent | 加权评分 + 三色看板 |
| 随访调度管理 | SchedulerAgent | 周期计算 + 任务生成 |
| 医生工作台 | DoctorAgent | 预警/随访/用药看板汇聚 |
| 用药管理 | MedicationAgent | 提醒 + 打卡 + 续方 |
| 患者档案管理 | Django View | 无Agent，基础CRUD |
```

---

以上就是完整的 `DESIGN_CONTEXT.md`，直接复制到Cursor项目根目录即可。在Cursor中开始协作时，可以用这段启动：

```
请阅读项目根目录的 DESIGN_CONTEXT.md，这是我毕业设计的系统设计摘要。
请基于该文档，帮我从创建Django项目骨架和定义Models开始实现。
```

需要我同时输出第五章骨架的md版本吗？

```markdown
# 系统设计摘要（第四章精华）

## 技术栈
- 后端：Python 3.x + Django 4.x
- Agent编排：LangGraph
- 数据库：SQLite（开发）/ MySQL（生产）
- 前端：Django Template + HTML/CSS/JS
- LLM：大语言模型API（语音文本→结构化JSON）

## 项目结构（建议）

cdm_system/
├── manage.py
├── cdm_system/              # Django项目配置
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── accounts/                # 用户认证模块
│   ├── models.py
│   ├── views.py
│   └── templates/accounts/
├── patients/                # 患者端（健康数据 + 打卡）
│   ├── models.py            # Patient, HealthRecord, MedicationRecord
│   ├── views.py
│   └── templates/patients/
├── doctors/                 # 医生端（工作台 + 档案管理）
│   ├── models.py            # Doctor, VisitTask, MedicationPlan
│   ├── views.py
│   └── templates/doctors/
├── agents/                  # 五个核心Agent
│   ├── patient_agent.py
│   ├── triage_agent.py
│   ├── scheduler_agent.py
│   ├── doctor_agent.py
│   ├── medication_agent.py
│   ├── graph.py             # LangGraph有向图定义
│   └── state.py             # SystemState定义
├── risk/                    # 风险评估模块
│   └── models.py            # RiskRecord
└── static/                  # CSS/JS/图片


## 七张核心数据表

### Patient（患者主表）
| 字段 | 类型 | 约束 | 说明 |
|:---|:---|:---|:---|
| patient_id | INT | PK, AUTO_INCREMENT | 患者唯一标识 |
| doctor_id | INT | FK → Doctor, NOT NULL | 责任医生ID |
| name | VARCHAR(50) | NOT NULL | 姓名 |
| age | INT | NOT NULL | 年龄 |
| gender | VARCHAR(4) | NOT NULL | 性别 |
| diagnosis_year | INT | NOT NULL | 确诊年份 |
| phone | VARCHAR(20) | NOT NULL | 联系电话 |
| account | VARCHAR(50) | UNIQUE, NOT NULL | 登录账号 |
| password_hash | VARCHAR(128) | NOT NULL | 密码哈希 |
| is_active | BOOLEAN | DEFAULT TRUE | 在管/归档 |
| created_at | DATETIME | AUTO_NOW_ADD | 建档时间 |

### Doctor（医生表）
| 字段 | 类型 | 约束 | 说明 |
|:---|:---|:---|:---|
| doctor_id | INT | PK, AUTO_INCREMENT | 医生唯一标识 |
| name | VARCHAR(50) | NOT NULL | 姓名 |
| phone | VARCHAR(20) | NOT NULL | 联系电话 |
| account | VARCHAR(50) | UNIQUE, NOT NULL | 登录账号 |
| password_hash | VARCHAR(128) | NOT NULL | 密码哈希 |
| created_at | DATETIME | AUTO_NOW_ADD | 创建时间 |

### HealthRecord（健康记录表）
| 字段 | 类型 | 约束 | 说明 |
|:---|:---|:---|:---|
| record_id | INT | PK, AUTO_INCREMENT | 记录ID |
| patient_id | INT | FK → Patient, NOT NULL | 所属患者 |
| fasting_glucose | DECIMAL(4,1) | NULL | 空腹血糖 mmol/L |
| postmeal_glucose | DECIMAL(4,1) | NULL | 餐后血糖 mmol/L |
| systolic_bp | INT | NULL | 收缩压 mmHg |
| diastolic_bp | INT | NULL | 舒张压 mmHg |
| weight | DECIMAL(4,1) | NULL | 体重 kg |
| input_type | VARCHAR(10) | NOT NULL | 录入方式 voice/text |
| recorded_at | DATETIME | NOT NULL | 录入时间 |

### RiskRecord（风险评估记录表）
| 字段 | 类型 | 约束 | 说明 |
|:---|:---|:---|:---|
| risk_id | INT | PK, AUTO_INCREMENT | 评估ID |
| patient_id | INT | FK → Patient, NOT NULL | 所属患者 |
| health_record_id | INT | FK → HealthRecord, NOT NULL | 关联健康记录 |
| risk_level | VARCHAR(10) | NOT NULL | green/yellow/red |
| risk_score | DECIMAL(3,2) | NOT NULL | 加权评分 |
| trigger_indicators | TEXT | NULL | 异常指标JSON |
| evaluated_at | DATETIME | AUTO_NOW_ADD | 评估时间 |

### VisitTask（随访任务表）
| 字段 | 类型 | 约束 | 说明 |
|:---|:---|:---|:---|
| task_id | INT | PK, AUTO_INCREMENT | 任务ID |
| patient_id | INT | FK → Patient, NOT NULL | 所属患者 |
| doctor_id | INT | FK → Doctor, NOT NULL | 负责医生 |
| visit_type | VARCHAR(20) | NOT NULL | online/offline/home |
| priority | VARCHAR(10) | DEFAULT 'normal' | normal/urgent |
| due_date | DATE | NOT NULL | 截止日期 |
| status | VARCHAR(20) | DEFAULT 'pending' | pending/completed/deferred |
| remark | TEXT | NULL | 随访备注 |
| created_at | DATETIME | AUTO_NOW_ADD | 创建时间 |
| completed_at | DATETIME | NULL | 完成时间 |

### MedicationPlan（用药方案表）
| 字段 | 类型 | 约束 | 说明 |
|:---|:---|:---|:---|
| plan_id | INT | PK, AUTO_INCREMENT | 方案ID |
| patient_id | INT | FK → Patient, NOT NULL | 所属患者 |
| drug_name | VARCHAR(100) | NOT NULL | 药品名称 |
| dosage | VARCHAR(50) | NOT NULL | 剂量如500mg |
| frequency | VARCHAR(20) | NOT NULL | 每日2次 |
| remind_times | VARCHAR(100) | NOT NULL | 08:00,20:00 |
| total_days | INT | NOT NULL | 处方总天数 |
| start_date | DATE | NOT NULL | 方案起始日期 |
| is_active | BOOLEAN | DEFAULT TRUE | 是否生效 |
| created_at | DATETIME | AUTO_NOW_ADD | 创建时间 |

### MedicationRecord（用药打卡记录表）
| 字段 | 类型 | 约束 | 说明 |
|:---|:---|:---|:---|
| record_id | INT | PK, AUTO_INCREMENT | 打卡ID |
| plan_id | INT | FK → MedicationPlan, NOT NULL | 所属方案 |
| patient_id | INT | FK → Patient, NOT NULL | 所属患者 |
| scheduled_time | DATETIME | NOT NULL | 计划服药时间 |
| checked_at | DATETIME | NULL | 实际打卡时间 |
| status | VARCHAR(10) | NOT NULL | taken/missed/skipped |


## SystemState定义

```python
from typing import TypedDict, Optional
from datetime import date

class SystemState(TypedDict):
    patient_id: int
    patient_name: str                    # 冗余缓存避免重复查库
    health_record: dict                  # PatientAgent解析后的结构化体征
    risk_level: str                      # green / yellow / red
    risk_score: float                    # 加权评分值
    trigger_indicators: list             # 异常指标列表
    visit_task_id: Optional[int]         # 随访任务ID
    next_visit_date: Optional[str]       # 下次随访日期
    medication_alert: bool               # 是否触发续方提醒
    flow_log: list                       # Agent执行日志
```


## Agent职责与接口

### PatientAgent
- 入口：run(state: dict) -> dict
- 职责：解析语音/文字输入，存储HealthRecord
- 关键方法：
  - parse_voice_text(text) -> dict  （调用LLM）
  - parse_form_data(data) -> dict
  - validate_health_data(data) -> bool
  - save_health_record(data) -> HealthRecord
- 输出：state.health_record 写入结构化数据
- 触发下游：→ TriageAgent

### TriageAgent
- 入口：run(state: dict) -> dict
- 职责：加权风险评分，生成三色等级
- 关键方法：
  - evaluate(record) -> RiskRecord
  - calculate_weighted_score(data) -> float
  - get_trigger_indicators(data) -> list
  - map_score_to_level(score) -> str
  - update_patient_profile(patient_id) -> None
- 输出：state.risk_level / risk_score / trigger_indicators
- 触发下游：→ SchedulerAgent（等级变更时）/ DoctorAgent（等级未变时）

### SchedulerAgent
- 入口：run(state: dict) -> dict
- 职责：动态计算随访周期，创建/更新VisitTask
- 关键逻辑：
  - 查询当前未完成任务，存在则更新，不存在则新建
  - 红码立即生成紧急任务
- 输出：state.visit_task_id / next_visit_date
- 触发下游：→ DoctorAgent

### DoctorAgent
- 入口：run(state: dict) -> dict
- 职责：汇聚预警/任务/续方通知，更新医生看板数据
- 关键逻辑：
  - 红码患者置顶显示
  - 接收随访任务更新
  - 接收续方待办
- 输出：更新相关数据库记录
- 触发下游：→ END

### MedicationAgent
- 入口：run_reminder_task()（独立定时任务）
- 职责：用药提醒推送、打卡记录、依从率计算、续方预警
- 关键方法：
  - handle_checkin(plan_id, status) -> MedicationRecord
  - calculate_adherence_rate(patient_id, days) -> float
  - estimate_remaining_days(plan_id) -> int
  - check_refill_needed(plan_id) -> bool
- 触发下游：→ DoctorAgent（续方时）


## LangGraph流转定义

### 主流程（健康数据录入触发）
PatientAgent → TriageAgent → [条件：等级变更?]
  - 是 → SchedulerAgent → DoctorAgent → END
  - 否 → DoctorAgent → END

### 用药路径（定时任务触发）
MedicationAgent → [条件：剩余药量≤阈值?]
  - 是 → DoctorAgent → END
  - 否 → END

### graph.py 伪代码
```python
from langgraph.graph import StateGraph, END
from agents.state import SystemState

graph = StateGraph(SystemState)

# 添加节点
graph.add_node("patient_agent", patient_agent_run)
graph.add_node("triage_agent", triage_agent_run)
graph.add_node("scheduler_agent", scheduler_agent_run)
graph.add_node("doctor_agent", doctor_agent_run)

# 添加边
graph.set_entry_point("patient_agent")
graph.add_edge("patient_agent", "triage_agent")
graph.add_conditional_edges(
    "triage_agent",
    should_reschedule,    # 判断风险等级是否变更
    {True: "scheduler_agent", False: "doctor_agent"}
)
graph.add_edge("scheduler_agent", "doctor_agent")
graph.add_edge("doctor_agent", END)

app = graph.compile()
```


## 风险评分规则

| 指标 | 绿色(正常) | 黄色(警示) | 红色(危险) | 权重 |
|:---|:---|:---|:---|:---|
| 空腹血糖 mmol/L | <7.0 | 7.0~13.9 | ≥13.9 | 0.35 |
| 餐后血糖 mmol/L | <10.0 | 10.0~16.7 | ≥16.7 | 0.25 |
| 收缩压 mmHg | <130 | 130~160 | ≥160 | 0.20 |
| 舒张压 mmHg | <80 | 80~100 | ≥100 | 0.10 |
| BMI | <24 | 24~28 | ≥28 | 0.10 |

评分规则：绿=1分，黄=2分，红=3分
加权总分：<1.5=绿码，1.5~2.2=黄码，>2.2=红码


## 随访周期规则

| 等级 | 随访方式 | 周期 |
|:---|:---|:---|
| 绿码 | 线上轻问诊 | 30天 |
| 黄码 | 线上轻问诊 | 14天 |
| 红码 | 线下门诊/上门巡诊 | 立即生成紧急任务 |


## 续方预警规则
- 阈值：剩余天数 ≤ 3天
- 剩余天数 = start_date + total_days - 当前日期
- 触发时：同时通知患者端 + 医生端
- 续方后：reset start_date为当日


## 依从率计算
依从率 = 实际打卡次数(status=taken) / 应打卡总次数 × 100%


## LLM Prompt模板（PatientAgent语音解析）
```
你是一个医疗数据解析助手。请从以下患者口述文字中提取体征数据，
以JSON格式输出，字段包括：
- fasting_glucose（空腹血糖，单位mmol/L）
- postmeal_glucose（餐后血糖）
- systolic_bp（收缩压）
- diastolic_bp（舒张压）
- weight（体重，单位kg）
若某字段未提及，值填null。仅输出JSON，不要额外解释。

患者描述：{input_text}
```


## 功能模块与处理组件对应

| 功能模块 | 处理组件 | 协作关系 |
|:---|:---|:---|
| 用户认证模块 | Django View | 按角色路由 |
| 健康数据管理模块 | PatientAgent | → TriageAgent |
| 风险评估与预警模块 | TriageAgent | → SchedulerAgent |
| 随访调度管理模块 | SchedulerAgent | → DoctorAgent |
| 用药管理模块 | MedicationAgent | 独立定时，续方→DoctorAgent |
| 医生工作台 | DoctorAgent | 汇聚多模块推送 |
| 患者档案管理模块 | Django View | 建档后同步MedicationAgent |
```

以上就是完整的 `DESIGN_CONTEXT.md` 内容，可以直接复制到Cursor项目根目录使用。需要我继续输出第五章骨架的md版本吗？

```markdown
# 系统设计摘要（第四章精华）

## 技术栈
- 后端：Python 3.x + Django 4.x
- Agent编排：LangGraph
- 数据库：SQLite（开发）/ MySQL（生产）
- 前端：Django Template + HTML/CSS/JS
- LLM：大语言模型API（语音文本→结构化JSON）

## 项目结构（建议）

cdm_system/
├── manage.py
├── cdm_system/              # Django项目配置
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── accounts/                # 用户认证模块
│   ├── models.py
│   ├── views.py
│   └── templates/accounts/
├── patients/                # 患者端（健康数据 + 打卡）
│   ├── models.py            # Patient, HealthRecord, MedicationRecord
│   ├── views.py
│   └── templates/patients/
├── doctors/                 # 医生端（工作台 + 档案管理）
│   ├── models.py            # Doctor, VisitTask, MedicationPlan
│   ├── views.py
│   └── templates/doctors/
├── agents/                  # 五个核心Agent
│   ├── patient_agent.py
│   ├── triage_agent.py
│   ├── scheduler_agent.py
│   ├── doctor_agent.py
│   ├── medication_agent.py
│   ├── graph.py             # LangGraph有向图定义
│   └── state.py             # SystemState定义
├── risk/                    # 风险评估模块
│   └── models.py            # RiskRecord
└── static/                  # CSS/JS/图片


## 七张核心数据表

### Patient（患者表）
| 字段名 | 数据类型 | 约束 | 说明 |
|:---|:---:|:---:|:---|
| patient_id | INT | PK, AUTO_INCREMENT | 患者唯一标识 |
| doctor_id | INT | FK → Doctor, NOT NULL | 责任医生ID |
| name | VARCHAR(50) | NOT NULL | 患者姓名 |
| age | INT | NOT NULL | 患者年龄 |
| gender | VARCHAR(4) | NOT NULL | 性别（男/女） |
| diagnosis_year | INT | NOT NULL | 确诊2型糖尿病年份 |
| phone | VARCHAR(20) | NOT NULL | 联系电话 |
| account | VARCHAR(50) | UNIQUE, NOT NULL | 登录账号 |
| password_hash | VARCHAR(128) | NOT NULL | 密码哈希值 |
| is_active | BOOLEAN | DEFAULT TRUE | 在管状态 |
| created_at | DATETIME | AUTO_NOW_ADD | 建档时间 |

### Doctor（医生表）
| 字段名 | 数据类型 | 约束 | 说明 |
|:---|:---:|:---:|:---|
| doctor_id | INT | PK, AUTO_INCREMENT | 医生唯一标识 |
| name | VARCHAR(50) | NOT NULL | 医生姓名 |
| phone | VARCHAR(20) | NOT NULL | 联系电话 |
| account | VARCHAR(50) | UNIQUE, NOT NULL | 登录账号 |
| password_hash | VARCHAR(128) | NOT NULL | 密码哈希值 |
| created_at | DATETIME | AUTO_NOW_ADD | 账号创建时间 |

### HealthRecord（健康记录表）
| 字段名 | 数据类型 | 约束 | 说明 |
|:---|:---:|:---:|:---|
| record_id | INT | PK, AUTO_INCREMENT | 记录唯一标识 |
| patient_id | INT | FK → Patient, NOT NULL | 所属患者ID |
| fasting_glucose | DECIMAL(4,1) | NULL | 空腹血糖（mmol/L） |
| postmeal_glucose | DECIMAL(4,1) | NULL | 餐后2h血糖（mmol/L） |
| systolic_bp | INT | NULL | 收缩压（mmHg） |
| diastolic_bp | INT | NULL | 舒张压（mmHg） |
| weight | DECIMAL(4,1) | NULL | 体重（kg） |
| input_type | VARCHAR(10) | NOT NULL | 录入方式（voice/text） |
| recorded_at | DATETIME | NOT NULL | 数据录入时间 |

### RiskRecord（风险评估记录表）
| 字段名 | 数据类型 | 约束 | 说明 |
|:---|:---:|:---:|:---|
| risk_id | INT | PK, AUTO_INCREMENT | 评估记录唯一标识 |
| patient_id | INT | FK → Patient, NOT NULL | 所属患者ID |
| health_record_id | INT | FK → HealthRecord, NOT NULL | 关联的健康记录ID |
| risk_level | VARCHAR(10) | NOT NULL | 风险等级（green/yellow/red） |
| risk_score | DECIMAL(3,2) | NOT NULL | 加权风险评分值 |
| trigger_indicators | TEXT | NULL | 触发预警的异常指标JSON列表 |
| evaluated_at | DATETIME | AUTO_NOW_ADD | 评估时间 |

### VisitTask（随访任务表）
| 字段名 | 数据类型 | 约束 | 说明 |
|:---|:---:|:---:|:---|
| task_id | INT | PK, AUTO_INCREMENT | 任务唯一标识 |
| patient_id | INT | FK → Patient, NOT NULL | 所属患者ID |
| doctor_id | INT | FK → Doctor, NOT NULL | 负责医生ID |
| visit_type | VARCHAR(20) | NOT NULL | 随访方式（online/offline/home） |
| priority | VARCHAR(10) | DEFAULT 'normal' | 优先级（normal/urgent） |
| due_date | DATE | NOT NULL | 任务截止日期 |
| status | VARCHAR(20) | DEFAULT 'pending' | 任务状态（pending/completed/deferred） |
| remark | TEXT | NULL | 随访备注 |
| created_at | DATETIME | AUTO_NOW_ADD | 任务创建时间 |
| completed_at | DATETIME | NULL | 任务完成时间 |

### MedicationPlan（用药方案表）
| 字段名 | 数据类型 | 约束 | 说明 |
|:---|:---:|:---:|:---|
| plan_id | INT | PK, AUTO_INCREMENT | 方案唯一标识 |
| patient_id | INT | FK → Patient, NOT NULL | 所属患者ID |
| drug_name | VARCHAR(100) | NOT NULL | 药品名称 |
| dosage | VARCHAR(50) | NOT NULL | 剂量规格 |
| frequency | VARCHAR(20) | NOT NULL | 每日服药频次 |
| remind_times | VARCHAR(100) | NOT NULL | 提醒时间点（如"08:00,20:00"） |
| total_days | INT | NOT NULL | 处方总天数 |
| start_date | DATE | NOT NULL | 方案起始日期 |
| is_active | BOOLEAN | DEFAULT TRUE | 方案是否生效 |
| created_at | DATETIME | AUTO_NOW_ADD | 方案创建时间 |

### MedicationRecord（用药打卡记录表）
| 字段名 | 数据类型 | 约束 | 说明 |
|:---|:---:|:---:|:---|
| record_id | INT | PK, AUTO_INCREMENT | 打卡记录唯一标识 |
| plan_id | INT | FK → MedicationPlan, NOT NULL | 所属用药方案ID |
| patient_id | INT | FK → Patient, NOT NULL | 所属患者ID |
| scheduled_time | DATETIME | NOT NULL | 计划服药时间 |
| checked_at | DATETIME | NULL | 实际打卡时间 |
| status | VARCHAR(10) | NOT NULL | 打卡状态（taken/missed/skipped） |


## SystemState定义

```python
from typing import TypedDict, Optional
from datetime import date

class SystemState(TypedDict):
    patient_id: int
    patient_name: str                    # 冗余缓存，避免重复查库
    health_record: dict                  # PatientAgent解析后的结构化体征数据
    risk_level: str                      # green / yellow / red
    risk_score: float                    # 加权风险评分值
    trigger_indicators: list             # 触发预警的异常指标列表
    visit_task_id: Optional[int]         # SchedulerAgent创建或更新的随访任务ID
    next_visit_date: Optional[str]       # 下次随访计划日期
    medication_alert: bool               # 是否触发续方提醒
    flow_log: list                       # 各Agent节点的执行日志
```


## Agent职责与接口

### PatientAgent
- 入口：run(state: SystemState) -> SystemState
- 职责：接收语音/文字输入，调用LLM解析为结构化JSON，校验数据范围，存入HealthRecord
- 输出：state.health_record 写入解析后的体征数据
- 下游：→ TriageAgent

### TriageAgent
- 入口：run(state: SystemState) -> SystemState
- 职责：读取state.health_record，执行加权风险评分，生成三色等级
- 输出：state.risk_level, state.risk_score, state.trigger_indicators
- 下游：→ SchedulerAgent（仅风险等级变更时）/ DoctorAgent（等级未变时）

### SchedulerAgent
- 入口：run(state: SystemState) -> SystemState
- 职责：根据risk_level查表确定随访周期，创建/更新VisitTask
- 输出：state.visit_task_id, state.next_visit_date
- 下游：→ DoctorAgent

### DoctorAgent
- 入口：run(state: SystemState) -> SystemState
- 职责：接收预警/任务/续方通知，更新看板数据
- 输出：更新数据库记录，返回看板数据
- 下游：→ END

### MedicationAgent
- 入口：run_reminder_task()（定时任务，独立于主流程）
- 职责：按用药方案推送服药提醒，记录打卡，计算依从率，估算剩余药量
- 续方触发条件：剩余天数 ≤ 3天（REFILL_THRESHOLD）
- 下游：→ DoctorAgent（仅续方预警时）


## LangGraph有向图结构

### 主业务流程（健康数据录入触发）
PatientAgent → TriageAgent → [条件：等级是否变更]
  - 是 → SchedulerAgent → DoctorAgent → END
  - 否 → DoctorAgent → END

### 用药管理路径（定时任务独立触发）
MedicationAgent → [条件：剩余药量≤阈值]
  - 是 → DoctorAgent → END
  - 否 → END


## 风险评分规则

### 指标阈值与权重
| 指标 | 绿色（1分） | 黄色（2分） | 红色（3分） | 权重 |
|:---|:---|:---|:---|:---|
| 空腹血糖(mmol/L) | <7.0 | 7.0~13.9 | ≥13.9 | 0.35 |
| 餐后血糖(mmol/L) | <10.0 | 10.0~16.7 | ≥16.7 | 0.25 |
| 收缩压(mmHg) | <130 | 130~160 | ≥160 | 0.20 |
| 舒张压(mmHg) | <80 | 80~100 | ≥100 | 0.10 |
| BMI | <24 | 24~28 | ≥28 | 0.10 |

### 等级映射
- 加权总分 < 1.5 → 绿码（green）
- 1.5 ≤ 加权总分 ≤ 2.2 → 黄码（yellow）
- 加权总分 > 2.2 → 红码（red）


## 随访周期规则
| 风险等级 | 随访方式 | 随访周期 |
|:---|:---|:---|
| 绿码 | 线上轻问诊（online） | 30天 |
| 黄码 | 线上轻问诊（online） | 14天 |
| 红码 | 线下门诊/上门巡诊（offline/home） | 立即（priority=urgent） |


## LLM Prompt模板（PatientAgent语音解析用）

你是一个医疗数据解析助手。请从以下患者口述文字中提取体征数据，
以JSON格式输出，字段包括：
- fasting_glucose（空腹血糖，单位mmol/L）
- postmeal_glucose（餐后血糖，单位mmol/L）
- systolic_bp（收缩压，单位mmHg）
- diastolic_bp（舒张压，单位mmHg）
- weight（体重，单位kg）
若某字段未提及，值填null。仅输出JSON，不要添加任何解释文字。

患者描述：{input_text}


## 依从率计算公式
依从率 = 实际打卡次数（status=taken） / 应打卡总次数 × 100%

## 剩余药量估算
剩余天数 = (start_date + total_days) - 当前日期
续方触发条件：剩余天数 ≤ REFILL_THRESHOLD（默认3天）
```

---

以上就是完整的 `DESIGN_CONTEXT.md`，直接复制粘贴到Cursor即可。需要我再输出第五章骨架的纯markdown版本吗？