# 毕业论文进度追踪日志

> 论文题目：基于多智能体系统的社区老年糖尿病智能随访管理平台设计与实现

---

## 2026-04-16 Session 4：多供应商语音服务 + 论文章节更新（ch02/03/04/05）

### 本次目标
1. speech_service.py 增加火山引擎（字节豆包）和通义千问（阿里云 DashScope）ASR/TTS 供应商支持
2. 完成 ch02/03/04/05 四个论文章节中 ASR/TTS + AgentLog 相关内容的修改

### 代码改动

| 文件 | 操作 | 说明 |
|------|------|------|
| `agents/speech_service.py` | 重写 | 增加策略模式多供应商分派。ASR 新增 `_asr_volcano()`（火山引擎）、`_asr_dashscope()`（通义听悟 Paraformer）。TTS 新增 `_tts_volcano()`（火山引擎）、`_tts_dashscope()`（CosyVoice）。提取 `_get_cache_path()` 公共缓存函数。增加 `PROVIDER_CONFIGS` 供应商配置参考字典。|
| `settings.py` | 修改 | ASR_PROVIDER/TTS_PROVIDER 注释增加可选值说明；新增 VOLCANO_APP_ID/VOLCANO_ACCESS_TOKEN/DASHSCOPE_API_KEY 配置项模板（注释状态）。|

### 论文章节改动

| 章节 | 改动内容 | 新增量 |
|------|----------|--------|
| **ch02（技术综述）** | 新增 `\section{语音识别与语音合成技术}`，含 ASR 小节（Whisper/Paraformer/火山引擎技术综述 + 服务端架构说明）和 TTS 小节（Neural TTS/Edge TTS/CosyVoice 技术综述 + 缓存策略说明）。| ~1.5 页 |
| **ch03（需求分析）** | ① 性能需求补充 ASR 延迟<3s、TTS 延迟<3s。② 可用性需求补充 TTS 播报需求。③ 可维护性需求补充 ASR/TTS 供应商无关性 + AgentLog 可追溯性要求。④ 语音录入用例更新为"录音→上传→ASR→AI解析"7步流程。| ~15 行修改 |
| **ch04（系统设计）** | ① 健康数据管理模块重写语音录入描述（Web Speech API → 服务端 ASR），新增 TTS 播报 + AgentLog 持久化段落。② 新增 `\subsection{语音交互服务设计}`（供应商策略表 + ASR 链路 + TTS 缓存机制）。③ 新增 `\subsection{Agent交互日志设计}`（定位、类型、容错机制）。④ E-R 模型更新实体数量（7→8）。⑤ 新增 AgentLog 数据表结构设计（11 字段 + 业务说明）。| ~2.5 页 |
| **ch05（系统实现）** | ① 环境依赖更新。② 新增 `\subsection{语音交互服务实现}` TODO 框架。③ 新增 `\subsection{Agent交互日志实现}` TODO 框架。④ 健康数据管理模块实现说明更新。| ~1 页框架 |

---

## 2026-04-16 Session 3：ASR/TTS + AgentLog + 日志系统

### 本次目标
结合三项功能需求（ASR 语音识别、TTS 语音合成、Agent 交互历史持久化、运维日志系统），一次性完成代码改造与前端规划更新。

### 改动清单

#### 1. AgentLog 模型（Agent 交互历史持久化）
| 文件 | 操作 | 说明 |
|------|------|------|
| `agents/models.py` | 新建 | AgentLog 模型：patient, log_type, agent_name, raw_input, raw_output, context_snapshot, health_record, created_by, duration_ms, created_at。7 种日志类型（voice_parse / health_feedback / doctor_summary / risk_eval / asr / tts / flow）。含数据库索引。|
| `agents/admin.py` | 修改 | 注册 AgentLogAdmin（list_display, list_filter, search_fields, readonly_fields, date_hierarchy）|
| `agents/migrations/0001_initial.py` | 自动生成 | CREATE TABLE agents_agentlog |

#### 2. 语音服务模块（ASR + TTS）
| 文件 | 操作 | 说明 |
|------|------|------|
| `agents/speech_service.py` | 新建 | 统一封装 ASR（OpenAI Whisper API）和 TTS（edge-tts）。ASR: `transcribe_audio()` → 接收音频字节流 → Whisper API 转写。TTS: `synthesize_speech()` → edge-tts 合成 MP3 → 文件缓存（MD5 hash 去重）。支持异步事件循环兼容（Django 同步视图中调用 async edge-tts）。|
| `requirements.txt` | 修改 | 新增 `edge-tts==7.2.8` |

#### 3. Settings 配置
| 文件 | 操作 | 说明 |
|------|------|------|
| `cdm_system/settings.py` | 修改 | 新增：MEDIA_URL/MEDIA_ROOT、LLM_MODEL/LLM_API_KEY/LLM_BASE_URL、ASR_PROVIDER/ASR_MODEL/ASR_BASE_URL、TTS_PROVIDER/TTS_VOICE、LOGGING（双 handler: file + console，loggers: django.request + agents）|

#### 4. Agent 日志嵌入
| 文件 | 操作 | 说明 |
|------|------|------|
| `agents/patient_agent.py` | 修改 | `generate_health_feedback()` 增加 patient_id/user 参数，执行后自动写入 health_feedback 类型 AgentLog（含耗时）。新增 `_write_log()` 通用日志写入工具函数。`run()` 中语音解析后写入 voice_parse 类型日志。|
| `agents/triage_agent.py` | 修改 | `run()` 风险评估完成后写入 risk_eval 类型 AgentLog。|
| `agents/doctor_agent.py` | 修改 | `generate_patient_summary()` 增加 patient_id/user 参数，执行后写入 doctor_summary 类型 AgentLog（含耗时）。|

#### 5. View 层改造
| 文件 | 操作 | 说明 |
|------|------|------|
| `patients/views.py` | 修改 | ① `health_input()`: `generate_health_feedback()` 调用增加 patient_id/user 参数。② 新增 `voice_upload_api()`: 接收音频文件 → 调用 `speech_service.transcribe_audio()` → 写 ASR 日志 → 返回文本。③ 新增 `tts_api()`: 接收文本 → 调用 `speech_service.synthesize_speech()` → 返回音频 URL。④ 新增 `ai_history()`: 患者查看自己的 AI 交互历史。|
| `patients/urls.py` | 修改 | 新增路由：`api/voice-upload/`, `api/tts/`, `ai-history/` |
| `doctors/views.py` | 修改 | `patient_detail()`: `generate_patient_summary()` 传入 patient_id/user；查询并传递 agent_logs 到模板。|
| `cdm_system/urls.py` | 修改 | 开发环境下添加 MEDIA 文件服务。|

#### 6. 前端规划更新
| 文件 | 操作 | 说明 |
|------|------|------|
| `FRONTEND_PLAN.md` | 修改 | 技术栈更新（MediaRecorder + edge-tts 替代 Web Speech API）；P-02 录音流程改为"录音→上传→服务端 ASR"；P-03 新增 TTS 播报按钮；新增 P-07 AI 交互历史页面；D-03 新增"AI 交互记录"Tab；路由表新增 3 条 API + 1 条页面；技术要点新增 ASR/TTS/AgentLog/运维日志。|

### 验证结果
- `python manage.py check` → 0 issues
- `python manage.py migrate` → agents.0001_initial OK
- AgentLog 模型字段验证 → 11 字段正确
- speech_service 导入验证 → OK
- 所有新 View 函数导入验证 → OK
- Linter → 0 errors

### 新增文件统计
| 类别 | 新增 | 修改 |
|------|------|------|
| Python 文件 | 2（agents/models.py, agents/speech_service.py） | 7（settings, patient_agent, triage_agent, doctor_agent, patients/views, doctors/views, urls） |
| Markdown | 0 | 2（FRONTEND_PLAN.md, PROGRESS.md）|
| 配置 | 0 | 1（requirements.txt）|
| Migration | 1（自动生成） | 0 |

---

## 2026-04-16 | RAG 知识服务全链路集成

### 本次更新内容

**1. 代码：RAG 知识服务模块** (`agents/rag_service.py`，224行)

- 基于 ChromaDB 的向量知识库存储，支持持久化 + 语义检索
- `init_knowledge_base()`：扫描 `knowledge_base/` 目录，按文件名前缀自动标记 audience（patient/doctor/both），段落切分后写入 ChromaDB
- `retrieve()`：按 audience 过滤的 Top-K 语义检索
- `generate_with_context()`：将检索结果拼入 LLM Prompt 生成回答
- `generate_patient_feedback()`：患者端健康反馈（科普化、适老化表达 + 免责提示）
- `generate_doctor_summary()`：医生端诊疗辅助摘要（专业结构化 + 指南出处标注）
- Django management command `init_kb` 一键初始化知识库

**2. 代码：Agent 集成 RAG**

- PatientAgent 新增 `generate_health_feedback()` 方法
- DoctorAgent 新增 `generate_patient_summary()` 方法
- `patients/views.py`：评估结果页增加 `health_feedback` 字段
- `doctors/views.py`：患者详情页增加 `ai_summary` 字段

**3. 知识库文档**（`knowledge_base/` 目录）

| 文件 | audience | 段落数 |
|---|---|---|
| `patient_education.txt` | patient | 8 |
| `doctor_guidelines.txt` | doctor | 8 |

已通过 `python manage.py init_kb` 成功导入 ChromaDB，共 16 条记录。

**4. 依赖更新**

- `requirements.txt` 新增 `chromadb==1.5.7`

**5. 论文 ch04 改动**（系统设计）

- §4.1.1 数据支撑层：补充 ChromaDB 向量知识库说明
- §4.2.1 MAS设计思路：补充 RAG 作为共享基础设施的定位说明
- §4.2.4 PatientAgent：新增"健康反馈生成"处理逻辑段
- §4.2.4 DoctorAgent：新增"患者智能摘要生成"处理逻辑段
- §4.3.1 功能模块表：新增"RAG知识辅助服务"行
- §4.3 新增 §4.3.8 "RAG知识辅助服务设计"完整小节（含服务定位、知识库结构表、RAGService接口表）

**6. 论文 ch03 改动**（系统需求分析）

- §3.1 新增 §3.1.6 "知识辅助服务需求"小节
- §3.3 新增用例"查看健康反馈建议"用例描述表

**7. 论文 ch05 改动**（系统实现）

- §5.1 依赖列表注释更新（chromadb 版本）
- §5.3 新增 §5.3.6 "DoctorAgent实现" 子节骨架
- §5.3 新增 §5.3.7 "RAG知识服务实现" 子节骨架
- §5.4.2 健康数据管理模块截图注释补充

---

## 2026-04-16 | 后端 Views/URLs 完成 & 前端页面规划

### 本次更新内容

**1. 后端 Views + URL 路由全部完成**

- `accounts/`: 登录/登出/角色路由（`login_view`, `logout_view`, `role_router`）
- `accounts/decorators.py`: `@patient_required` / `@doctor_required` 权限装饰器
- `patients/views.py`: 患者首页、健康录入（语音+表单双模式）、评估结果、健康记录趋势、用药管理+打卡、我的随访（6个View + 3个API）
- `doctors/views.py`: 工作台看板、患者列表(搜索+筛选)、患者详情(多Tab)、新增/编辑患者、风险预警、随访任务(完成/延期)、用药监控、用药方案管理（14个View + 4个API）
- `doctors/forms.py`: `PatientForm` + `MedicationPlanForm`（Bootstrap 5 widget attrs）
- `cdm_system/urls.py`: 主路由串联 accounts/patients/doctors 三个app

**2. JSON API 接口设计完成**（共 9 个 AJAX 端点）

| 端点 | 说明 |
|---|---|
| `POST /patient/api/voice-parse/` | 语音文本→结构化数据预览 |
| `GET /patient/api/health-trend/` | 患者自己的趋势数据 |
| `POST /patient/api/medication/checkin/` | 用药打卡 |
| `GET /doctor/api/stats/` | 工作台统计 |
| `GET /doctor/patients/<id>/api/health-trend/` | 某患者健康趋势 |
| `GET /doctor/patients/<id>/api/risk-history/` | 某患者风险历史 |
| `GET /doctor/patients/<id>/api/adherence/` | 某患者依从率(按周) |
| `POST /doctor/visits/<id>/complete/` | 完成随访(支持AJAX) |
| `POST /doctor/visits/<id>/defer/` | 延期随访(支持AJAX) |

**3. 前端页面规划文档** (`cdm_system/FRONTEND_PLAN.md`)

输出完整的前端页面规划，包含：
- 全局设计规范（适老化、响应式、色彩系统、导航模式）
- 模板继承结构（base → base_patient/base_doctor → 具体页面）
- 15个页面清单（1个公共 + 6个患者端 + 8个医生端），每个页面定义了 UI 元素、交互逻辑、后端依赖
- 完整 API 路由表（18个页面路由 + 9个 JSON API）
- 关键交互流程图（患者录入→评估、医生处理预警）
- 技术要点备忘（Chart.js / Web Speech API / CSRF 等）

**4. Django system check 通过**，0 errors，0 warnings

---

## 2026-04-15 | 第四章系统设计完整整合（第一版文字定稿）

### 本次更新内容

**1. 第4章系统设计 → LaTeX 第一版文字完成** (`ch04_design.tex`，637行)

基于 `brainstorm/第四章/` 中的5份讨论记录，整合并融入全部A/B/C类交叉核验修正，完成4.1～4.4节正文：

- 4.1 系统总体架构设计
  - 4.1.1 三层技术架构（含C1修正：B-C-E→技术架构演进映射表）
  - 4.1.2 Django MVT架构映射
  - 4.1.3 系统技术架构图（含C4修正：主流程实线/定时任务虚线区分）
- 4.2 多智能体系统设计
  - 4.2.1 MAS整体设计思路
  - 4.2.2 LangGraph状态设计（含C3修正：patient_name字段+关联查询说明）
  - 4.2.3 LangGraph状态流转图（含A3修正：拆分为主流程+用药管理两张独立活动图）
  - 4.2.4 各Agent详细设计（PatientAgent/TriageAgent/SchedulerAgent/DoctorAgent/MedicationAgent）
- 4.3 功能模块详细设计
  - 4.3.1 系统功能模块划分（含A5修正：功能模块与Agent对应表补全至7行）
  - 4.3.2 用户认证模块
  - 4.3.3 健康数据管理模块
  - 4.3.4 风险评估与预警模块（含B1-①修正：引用4.2.4权重表）
  - 4.3.5 随访调度管理模块（含B1-②修正：引用4.2.4周期表）
  - 4.3.6 用药管理模块（含B1-③修正：引用4.2.4续方阈值）
  - 4.3.7 患者档案管理模块（含A1-④修正：建档环节补充指定责任医生）
  - 4.3.8 设计类图（含B2修正：ORM自动字段省略说明；A2修正：风险评估类图移除错误依赖+增加HealthRecord）
- 4.4 数据库设计
  - 选型说明（含C2修正：MongoDB对比排除论证）
  - 4.4.1 E-R模型设计（含A1-①修正：Doctor→Patient管辖关系；A4修正：HR-RR一对零或一关系文字）
  - 4.4.2 数据表结构设计 × 7张表（含A1-③修正：Patient表增加doctor_id字段）
- 4.5 界面设计 → 暂放（已注释）

**2. 新建 `diagrams/ch04/` 文件夹 → 8个PlantUML源文件**

| tex中图表标记 | 源文件 |
|---|---|
| 系统总体技术架构图 | `diagrams/ch04/architecture.puml` |
| 主业务流程Agent状态流转图 | `diagrams/ch04/langgraph-main-flow.puml` |
| 用药管理定时任务Agent状态流转图 | `diagrams/ch04/langgraph-medication-flow.puml` |
| 系统功能模块图（WBS） | `diagrams/ch04/function-modules-wbs.puml` |
| 健康数据管理模块设计类图 | `diagrams/ch04/class-health-data.puml` |
| 风险评估与预警模块设计类图 | `diagrams/ch04/class-risk-assessment.puml` |
| 用药管理模块设计类图 | `diagrams/ch04/class-medication.puml` |
| 系统E-R图 | `diagrams/ch04/er-diagram.puml` |

tex文件中所有图表位置以 `\todofig{}` + 红色 `[TODO-FIGURE: 图名 → 源文件路径]` 标记，后续渲染出图后替换 `\includegraphics` 即可。

**3. 讨论素材归档**

- `brainstorm/第四章/4.1系统总体架构设计与4.2多智能体系统设计.md`
- `brainstorm/第四章/4.3 功能模块详细设计.md`
- `brainstorm/第四章/4.3.8 设计类图.md`
- `brainstorm/第四章/4.1～4.4全部内容进行了逐条交叉核验.md`
- `brainstorm/第四章/次优先级修改文本.md`

### 已融入的交叉核验修正清单

| 类别 | 编号 | 修正内容 | 涉及位置 |
|---|---|---|---|
| A类 | A1 | Patient表增加doctor_id + E-R图增加管辖关系 + 建档补充指定责任医生 | 4.3.7 / 4.4.1 / 4.4.2 |
| A类 | A2 | 风险评估设计类图移除错误依赖，增加HealthRecord查询 | 4.3.8 |
| A类 | A3 | LangGraph状态流转图拆分为两张独立活动图 | 4.2.3 |
| A类 | A4 | E-R图HealthRecord-RiskRecord关系文字修正为一对零或一 | 4.4.1 |
| A类 | A5 | 功能模块与Agent对应表补全认证模块和档案管理模块 | 4.3.1 |
| B类 | B1 | 4.3.4/4.3.5/4.3.6重复内容改为引用4.2.4 | 4.3.4～4.3.6 |
| B类 | B2 | 设计类图说明补充ORM自动字段省略声明 | 4.3.8 |
| C类 | C1 | 4.1.1段首增加B-C-E→技术架构演进映射表 | 4.1.1 |
| C类 | C2 | 数据库选型说明增加MongoDB对比排除 | 4.4 |
| C类 | C3 | SystemState增加patient_name字段+关联查询说明 | 4.2.2 |
| C类 | C4 | 技术架构图区分主流程实线与定时任务虚线 | 4.1.3 |

---

## 2026-04-13 | 论文LaTeX框架搭建 & 内容首版整理

### 本次更新内容

**1. 建立 Overleaf 兼容的 LaTeX 论文项目结构**
- 创建 `thesis/` 目录，包含主文件 `main.tex` 和分章节文件
- 配置 XeLaTeX 编译、GB/T 7714-2015 引用格式、ctexbook 文档类
- 封面页、目录、图表目录框架就绪

**2. 第1章 绪论 → LaTeX 转换完成** (`ch01_introduction.tex`)
- 1.1 研究背景（老龄化、基层困境、AI政策机遇）
- 1.2 研究意义（理论意义 + 实践意义）
- 1.3 国内外研究现状（5个子节全部转换）
- 1.4 相关技术与理论基础（6个子节全部转换）
- 1.5 研究内容与论文结构（框架）
- 引用标记：全部使用 `\todocite{}` 占位，待补充 BibTeX 条目

**3. 第3章 系统需求分析 → LaTeX 首版完成** (`ch03_analysis.tex`)
- 3.1 系统功能需求分析（5个子模块需求描述，已润色为论文语言）
- 3.2 系统非功能需求分析（性能/安全/可用性/可维护性，框架）
- 3.3 系统用例分析（参与者识别 + 3个核心用例描述表）
- 用例图位置已标记 TODO，待 draw.io 绘制后插入

**4. 其余章节框架占位**
- 第2章 相关技术（视学校要求决定是否独立成章）
- 第4章 系统设计（TODO 标记，待基于 DESIGN_CONTEXT.md 扩写）
- 第5章 系统实现（待开发完成后填写）
- 第6章 系统测试（待开发完成后填写）
- 第7章 总结与展望
- 摘要（中英文草稿）
- 参考文献 `references.bib`（示例条目，待逐条补充）

**5. 素材文件整理**
- `essay/毕业论文第一章：绪论.md` → 原始 Markdown 素材（含75条参考文献链接）
- `systemmodeling/系统功能需求分析.md` → 第3章聊天记录提炼稿
- `systemmodeling/系统分析与设计（已经交叉检验过版本）.md` → 系统设计讨论记录

### 待办清单（按优先级）

| 优先级 | 任务 | 状态 |
|---|---|---|
| P0 | MAS系统Django项目开发 | 未开始 |
| P0 | 第4章UML图渲染（8张PlantUML→draw.io/PNG） | 源码就绪 |
| P0 | 第3章UML图绘制（用例图等） | 未开始 |
| P1 | 第5章系统实现正文扩写 | 框架已建 |
| P1 | 参考文献 BibTeX 化（75条） | 未开始 |
| P2 | 第2章相关技术（视学校格式要求） | 占位 |
| P2 | 第4章4.5界面设计 | 暂放 |
| P2 | 第6章系统测试 | 待开发完成 |
| P3 | 摘要定稿 | 草稿 |
| P3 | 第7章总结与展望 | 占位 |
| P3 | 致谢 | 占位 |

### 文件结构

```
MasInDiabetes/
├── essay/
│   ├── PROGRESS.md              ← 本文件（进度日志）
│   └── 毕业论文第一章：绪论.md   ← 原始素材
├── systemmodeling/
│   ├── 系统功能需求分析.md
│   └── 系统分析与设计（已经交叉检验过版本）.md
├── brainstorm/
│   └── 第四章/                   ← 第四章讨论素材（5份）
├── diagrams/
│   └── ch04/                    ← 第四章UML图PlantUML源码（8份）
├── project/
│   └── DESIGN_CONTEXT.md        ← 系统设计摘要（开发蓝图）
├── cdm_system/                  ← Django 项目（后端已完成）
│   ├── cdm_system/              ← 项目配置
│   │   ├── settings.py
│   │   └── urls.py              ✅ 主路由
│   ├── accounts/                ✅ 认证app（views + urls + decorators）
│   ├── patients/                ✅ 患者app（models + views + urls）
│   ├── doctors/                 ✅ 医生app（models + views + urls + forms）
│   ├── risk/                    ✅ 风险app（models）
│   ├── agents/                  ✅ 智能体app（5 agents + graph + state + AgentLog + speech_service）
│   ├── templates/               📝 待建（前端模板）
│   ├── static/                  📝 待建（静态资源）
│   ├── logs/                    ✅ 运维日志目录
│   ├── media/tts_cache/         ✅ TTS 音频缓存目录
│   ├── FRONTEND_PLAN.md         ✅ 前端页面规划文档（已更新 v2）
│   └── requirements.txt
└── thesis/                      ← LaTeX 论文项目
    ├── main.tex
    ├── references.bib
    ├── figures/
    └── chapters/
        ├── cover.tex
        ├── abstract.tex
        ├── ch01_introduction.tex  ✅
        ├── ch02_technology.tex    ✅ 完整重写（对标示例论文ch02格式）
        ├── ch03_analysis.tex      ✅
        ├── ch04_design.tex        ✅ 含RAG/语音/AgentLog扩写（885行）
        ├── ch05_implementation.tex 📝 框架
        ├── ch06_testing.tex       ✅ 完整重写（对标示例论文ch06格式，含20+测试用例）
        ├── ch07_conclusion.tex    📝 占位
        ├── appendix.tex
        └── acknowledgement.tex
```

---

## 2026-04-16 Session 5：ch02/ch06 重写 + Seed 脚本 + 前端规划

### 1. ch06 测试章节重写
- **对标示例论文**：测试目的 → 测试环境 → 功能测试 → 性能测试 → 兼容性测试 → 测试结论
- 功能测试设计了 **20 个测试用例**，覆盖：
  - 用户认证模块（T-01~T-04）
  - 健康数据录入模块（T-05~T-09，含语音录入 ASR/LLM 解析）
  - 风险评估与健康反馈模块（T-10~T-14，含 TTS 播报）
  - 医生端功能模块（T-15~T-18）
  - AI 交互历史模块（T-19~T-20）
- 性能测试设计了 6 个场景（P-01~P-06），与 ch03 非功能需求一一对应
- 兼容性测试覆盖 Edge/Chrome/移动端/MediaRecorder API
- 所有"通过"列为 TODO，待系统开发完成后实测填写

### 2. ch02 关键技术章节完整重写
- **对标示例论文格式**：每个技术独立 section，先原理后应用场景
- 章节结构：
  - 2.1 系统架构——B/S
  - 2.2 Web框架——Django
  - 2.3 大语言模型技术
  - 2.4 多智能体系统与LangGraph框架（含 MAS + LangGraph 两个 subsection）
  - 2.5 检索增强生成技术（RAG）
  - 2.6 语音识别与语音合成技术（ASR + TTS，保留之前内容）
  - 2.7 前端技术栈（HTML/CSS/JS + Bootstrap + Chart.js）
- ch01 1.4 节的深层技术内容保留不动（偏医学知识基础+理论），ch02 侧重工程技术栈
- 待补：每个 section 的 `\todocite{}` 参考文献

### 3. Seed 数据脚本
- 新建 `agents/management/commands/seed.py`
- `python manage.py seed` 一键创建：
  - 1 名医生（张建国，账号 doctor_zhang / demo1234）
  - 5 名患者（李淑芬、王德明、陈秀英、赵国强、刘玉兰，账号 patient_xxx / demo1234）
  - 每名患者 15 条健康记录（跨 30 天，随机血糖/血压/体重）
  - 每条记录对应 1 条风险评估（自动计算绿/黄/红码）
  - 每名患者 1 个用药方案 + 7 天打卡记录
  - 每名患者 1 条随访任务
  - 每名患者 4 条 AgentLog（asr/voice_parse/risk_eval/health_feedback）
- 支持 `--reset` 参数清空后重建
- 已执行验证：75 条记录 + 75 条风险 + 5 方案 + 5 任务 + 20 条 AgentLog ✅

### 4. API Key 需求清单
- **必须**：1 个 OpenAI 兼容 API Key（LLM + ASR Whisper 共用）
- **TTS**：Edge TTS 免费无需 Key
- **可选**：火山引擎 AppID/Token、DashScope Key（切换供应商时用）

### 5. 前端 Pencil MCP 评估
- Pencil MCP 可用于创建 UI 设计稿（.pen 文件），具备组件库、布局系统、截图导出能力
- **可行方案**：用 Pencil 设计核心页面的 UI 原型/示意图，导出为图片用于论文 ch04/ch05
- **前端开发**不使用 Pencil，仍用 Django Templates + Bootstrap + JS 实现
- 需要提供给 Pencil 的信息：页面列表、每页的布局结构、组件需求、配色方案

---

## 2026-04-16 Session 6：Qwen 全家桶切换 + 适老化设计标准

### 1. LLM/ASR/TTS 统一切换为阿里云 DashScope（Qwen 全家桶）
- **settings.py** 修改：
  - `LLM_MODEL` → `qwen3.5-plus`（通义千问 3.5 商业版）
  - `LLM_BASE_URL` → `https://dashscope.aliyuncs.com/compatible-mode/v1`
  - `ASR_PROVIDER` → `dashscope`，`ASR_MODEL` → `paraformer-v2`
  - `TTS_PROVIDER` → `dashscope`，`TTS_MODEL` → `cosyvoice-v2`，`TTS_VOICE` → `longxiaochun`（温和女声）
  - 新增 `DASHSCOPE_API_KEY` 配置项（LLM/ASR/TTS 三合一共用）
  - 保留了切换回 OpenAI/火山引擎的注释示例
- **speech_service.py** 修改：
  - `_asr_dashscope`: 统一使用 `DASHSCOPE_API_KEY` 或 `LLM_API_KEY`
  - `_tts_dashscope`: 新增 `TTS_MODEL` 配置读取（默认 cosyvoice-v2），不再硬编码模型名
  - `PROVIDER_CONFIGS` 更新：DashScope 配置置顶，补充 LLM_MODEL/LLM_BASE_URL 信息

### 2. 适老化设计标准补充到 FRONTEND_PLAN.md
- 基于《互联网应用适老化及无障碍改造指南》五大维度（可感知/可操作/可理解/兼容性/安全性），逐条对标本系统实现
- 新增**暖色调设计系统**：
  - 主色：暖橙 #D35400 + 琥珀 #E67E22
  - 背景：暖白奶油色 #FFF8F0
  - 文字：暖深棕 #2C1810（对比度 13.5:1）
  - 风险三色：生命绿 #27AE60 · 暖金黄 #F39C12 · 沉稳红 #C0392B
  - 导航：深棕木色 #3E2723
  - 所有色彩组合通过 WCAG AA 对比度验证
- 排版规范：正文 18px、行高 1.6、无衬线中文字体、卡片圆角 12px、8px 间距基数
- 操作规范：核心按钮 ≥ 60×60px、录音按钮 80×80px、所有可点击 ≥ 44×44px

### 3. 论文 ch02 同步更新
- LLM 小节：更新为"选用通义千问 Qwen3.5"，说明选择原因（中文能力/三合一/合规性）
- TTS 小节：更新为"采用 CosyVoice 作为默认 TTS"
- Bootstrap 小节：新增适老化标准引用和暖色调配色描述

### 需要你准备的
- **1 个 DashScope API Key**：在 [阿里云百炼](https://bailian.console.aliyun.com/) 获取
  - 填入 `cdm_system/.env` 的 `DASHSCOPE_API_KEY`
  - LLM + ASR + TTS 三个服务共用同一个 Key

---

## 2026-04-13 环境变量脱敏 + Git 仓库初始化

### 改动内容
1. **settings.py 脱敏**：
   - 引入 `python-dotenv`，所有敏感配置改为 `os.getenv()` 从 `.env` 文件读取
   - `SECRET_KEY`、`DASHSCOPE_API_KEY`、`LLM_API_KEY`、`VOLCANO_*` 等全部脱敏
   - LLM/ASR/TTS 模型名称、供应商等也支持通过环境变量覆盖（默认值保持 Qwen 全家桶）
2. **新增文件**：
   - `cdm_system/.env` — 实际环境变量文件（已加入 .gitignore，不会提交）
   - `cdm_system/.env.example` — 环境变量模板，供团队成员参考
   - `.gitignore` — 忽略 `.env`、`__pycache__`、`db.sqlite3`、IDE 文件、LaTeX 编译产物等
3. **requirements.txt** 新增 `python-dotenv==1.0.1`
4. **Git 仓库初始化**：首次提交并推送到 `https://github.com/Gumpanxy2024/MAS-in-diabetes.git`

---

## 2026-04-16 基础功能测试 + Bug 修复

### 测试结果：10/10 通过（100%）

| 编号 | 测试项 | 耗时 | 说明 |
|------|--------|------|------|
| T-01 | Django 启动 + .env 加载 | 387ms | 配置读取正常 |
| T-02 | 数据库迁移 & ORM | 494ms | CRUD 正常 |
| T-03 | LLM API (Qwen3.5) | 25s | 基础对话正常 |
| T-04 | LLM 语音文本解析 | 29s | 口语→JSON 正确解析 |
| T-05 | 风险评估算法 | 1ms | 绿/红分级准确 |
| T-06 | RAG 知识库 | 1s | 16段落，语义检索正常 |
| T-07 | TTS (DashScope CosyVoice) | 5.5s | 56KB MP3 生成成功 |
| T-08 | TTS (Edge TTS 备选) | 2s | 免费方案可用 |
| T-09 | RAG + LLM 健康反馈 | 79s | 完整链路生成合理建议 |
| T-10 | Seed 数据脚本 | 6s | 1医生/5患者/75条记录 |

### 测试中发现并修复的 Bug

1. **settings.py: `LLM_API_KEY` 为空导致 LLM 调用 401**
   - 原因：`LLM_API_KEY` 默认为空，但 `patient_agent.py` 和 `rag_service.py` 读的是 `LLM_API_KEY` 而非 `DASHSCOPE_API_KEY`
   - 修复：`DASHSCOPE_API_KEY` 提前声明，`LLM_API_KEY` fallback 到 `DASHSCOPE_API_KEY`
2. **DashScope TTS API 格式错误（400 Bad Request）**
   - 原因 1：旧 URL (`/aigc/text2audio/generation`) 已废弃，需用新端点 (`/audio/tts/SpeechSynthesizer`)
   - 原因 2：`voice` 和 `format` 参数应放在 `input` 对象内，而非 `parameters`
   - 原因 3：非流式模式返回 JSON（含音频 URL），不是直接返回二进制音频
   - 修复：重写 `_tts_dashscope()` 函数，两步获取（调 API → 下载音频）
3. **CosyVoice 音色版本不匹配**
   - 原因：`cosyvoice-v2` 模型在当前 API 已不可用；`cosyvoice-v3-flash` 的音色需要 `_v3` 后缀
   - 修复：模型改为 `cosyvoice-v3-flash`，音色改为 `longxiaochun_v3`（温和女声）

### 新增文件
- `test/basefunction/test_plan.md` — 测试方案
- `test/basefunction/run_tests.py` — 自动化测试脚本（10 个用例）
- `test/basefunction/report.md` — 测试报告（自动生成）
- `test/basefunction/results.json` — 原始数据
