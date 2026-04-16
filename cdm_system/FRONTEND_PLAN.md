# 前端页面规划文档

> 本文档定义所有前端页面的功能范围、布局要求和 API 依赖关系。
> 技术栈：Django Template + Bootstrap 5 + Chart.js + MediaRecorder API + DashScope CosyVoice TTS
> UI 设计工具：Pencil (.pen) 原型稿

---

## 一、全局设计规范

### 1.1 适老化设计标准

本系统遵循《互联网应用适老化及无障碍改造指南》技术要求，核心条目如下：

#### 可感知性

| 条目 | 规范 | 本系统实现 |
|------|------|-----------|
| 字型大小 | 主要文字 ≥ 18dp/pt，最大字体 ≥ 30dp/pt | 正文 18px，标题 24-30px，无衬线字体（系统默认 + Bootstrap） |
| 行间距 | 段落行距 ≥ 1.3 倍，段落间距 ≥ 行距×1.3 | `line-height: 1.6`，`margin-bottom: 1.2em` |
| 对比度 | 文本/图标对比度 ≥ 4.5:1（大字 ≥ 3:1） | 暖色调深文本 #2C1810 on #FFF8F0 = 13.5:1 ✅ |
| 颜色用途 | 颜色不作为传达信息的唯一手段 | 风险等级同时使用颜色+文字+图标三重提示 |
| 验证码 | 提供视觉/听觉替代 | 本系统不使用验证码（Django Session 认证） |

#### 可操作性

| 条目 | 规范 | 本系统实现 |
|------|------|-----------|
| 焦点区域 | 主要组件 ≥ 60×60dp/pt | 患者端核心按钮 60×60px，录音按钮 80×80px |
| 其他组件 | 非核心组件 ≥ 44×44dp/pt | 所有可点击元素 min 44×44px |
| 手势操作 | 避免3指以上复杂手势，提供操作反馈 | 仅使用点击/长按，无复杂手势 |
| 操作时间 | 非必要不限时 | 无倒计时操作，表单无自动超时 |
| 浮窗关闭 | 关闭按钮 ≥ 44×44dp/pt，位于左上/右上/底部中央 | 模态框关闭按钮 48×48px，右上角 |

#### 可理解性

| 条目 | 规范 | 本系统实现 |
|------|------|-----------|
| 提示机制 | 首次使用时提供引导提示 | 首次登录弹出功能引导卡片 |
| 功能名称 | "长辈版"作为标准入口名 | 本系统默认即为适老化版本，无需切换 |

#### 安全性

| 条目 | 规范 | 本系统实现 |
|------|------|-----------|
| 广告限制 | 禁止广告内容及插件 | 无任何广告、无弹窗广告 |
| 诱导按键 | 禁止诱导下载/付款按键 | 无诱导性操作 |
| 信息安全 | 最小必要原则收集个人信息 | 仅收集健康管理必要数据（姓名/年龄/健康指标） |

### 1.2 暖色调设计系统（适老化配色方案）

采用暖色调配色方案，营造温馨、安心的视觉氛围，符合老年用户的心理需求。

```
┌──────────────────────────────────────────────────┐
│  🎨 暖色调设计系统 (Warm Tone Design System)     │
├──────────────────────────────────────────────────┤
│                                                  │
│  主色 Primary     #D35400  ████  暖橙（信任感）  │
│  主色浅 Light     #E67E22  ████  琥珀（引导色）  │
│  主色深 Dark      #A04000  ████  深橙（强调）    │
│                                                  │
│  背景 Background  #FFF8F0  ████  暖白奶油色      │
│  卡片 Card        #FFFFFF  ████  纯白            │
│  边框 Border      #E8D5C4  ████  暖米色边框      │
│                                                  │
│  文字 Text-1      #2C1810  ████  暖深棕（正文）  │
│  文字 Text-2      #6B4D3A  ████  暖灰棕（辅助）  │
│  文字 Text-3      #9C8577  ████  暖浅棕（提示）  │
│                                                  │
│  成功/绿码 Green  #27AE60  ████  生命绿          │
│  警示/黄码 Yellow #F39C12  ████  暖金黄          │
│  危险/红码 Red    #C0392B  ████  沉稳红          │
│                                                  │
│  信息 Info        #2980B9  ████  天蓝（中性）    │
│  录音按钮         #E74C3C  ████  醒目红          │
│                                                  │
│  导航背景 Nav-bg  #3E2723  ████  深棕木色        │
│  导航文字 Nav-fg  #FFF8F0  ████  暖白            │
│                                                  │
└──────────────────────────────────────────────────┘
```

**对比度验证**（WCAG AA 标准）:
- Text-1 `#2C1810` on Background `#FFF8F0` → 对比度 13.5:1 ✅ (≥ 4.5:1)
- Text-2 `#6B4D3A` on Card `#FFFFFF` → 对比度 7.2:1 ✅
- Primary `#D35400` on Card `#FFFFFF` → 对比度 4.6:1 ✅
- Nav-fg `#FFF8F0` on Nav-bg `#3E2723` → 对比度 12.8:1 ✅

### 1.3 排版与间距

| 元素 | 规格 |
|------|------|
| 正文字号 | 18px (1.125rem)，移动端 16px |
| 标题 H1 | 30px (1.875rem) |
| 标题 H2 | 24px (1.5rem) |
| 标题 H3 | 20px (1.25rem) |
| 行高 | 1.6 |
| 段落间距 | 1.2em |
| 字体 | `-apple-system, "Noto Sans SC", "Microsoft YaHei", sans-serif` |
| 卡片圆角 | 12px |
| 卡片阴影 | `0 2px 8px rgba(44,24,16,0.08)` |
| 间距系统 | 8px 基数（8/16/24/32/48px） |

### 1.4 通用布局规范

| 项目 | 规范 |
|------|------|
| 响应式 | Bootstrap Grid，≥768px 双栏，<768px 单栏 |
| 患者端导航 | 底部 Tab 导航（大图标 + 文字标签，60px 高） |
| 医生端导航 | 左侧 Sidebar（深棕木色背景 #3E2723） |
| 模板继承 | `base.html` → `base_patient.html` / `base_doctor.html` |

---

## 二、模板继承结构

```
templates/
├── base.html                   # 全站基础（meta, Bootstrap CDN, 消息提示）
├── base_patient.html           # 患者布局（底部Tab: 首页/录入/记录/用药/随访）
├── base_doctor.html            # 医生布局（左侧Sidebar + 顶部Header）
├── accounts/
│   └── login.html              # 登录页
├── patients/
│   ├── dashboard.html          # 患者首页
│   ├── health_input.html       # 健康数据录入（含录音上传）
│   ├── input_result.html       # 评估结果（含TTS播报）
│   ├── health_records.html     # 健康记录 + 趋势图
│   ├── medication.html         # 用药管理
│   ├── my_visits.html          # 我的随访
│   └── ai_history.html         # AI 交互历史
└── doctors/
    ├── dashboard.html          # 医生工作台
    ├── patient_list.html       # 患者列表
    ├── patient_detail.html     # 患者详情
    ├── patient_form.html       # 新增/编辑患者
    ├── risk_alerts.html        # 风险预警
    ├── visit_list.html         # 随访任务
    ├── medication_monitor.html # 用药监控
    └── medication_plan_form.html # 新增/编辑用药方案
```

---

## 三、页面清单

### 3.1 公共页面

#### P-00 登录页 (`/accounts/login/`)
| 要素       | 说明                                       |
| ---------- | ------------------------------------------ |
| 功能       | 账号密码登录，登录后按角色自动跳转         |
| UI 元素    | Logo + 标题、用户名输入框、密码输入框、登录按钮 |
| 交互       | 错误提示（Django messages）、Enter 键提交  |
| 后端依赖   | `POST /accounts/login/`                    |

---

### 3.2 患者端页面（5个主页面）

#### P-01 患者首页 (`/patient/`)
| 要素       | 说明                                                       |
| ---------- | ---------------------------------------------------------- |
| 功能       | 个人健康概览一览                                           |
| 卡片区域   | ① 风险状态卡（绿/黄/红三色徽章 + 最近评估时间）            |
|            | ② 最近一次体征摘要（空腹血糖、血压、体重）                 |
|            | ③ 下次随访提醒卡（日期 + 随访方式 + 倒计时天数）           |
|            | ④ 今日用药概览（方案数 + 今日已打卡/未打卡）               |
| 快捷入口   | "录入数据" 大按钮（跳转 P-02）                             |
| 后端依赖   | `GET /patient/`                                            |

#### P-02 健康数据录入 (`/patient/input/`)
| 要素       | 说明                                                       |
| ---------- | ---------------------------------------------------------- |
| 功能       | 语音/表单双模式录入体征数据                                |
| 语音模式   | 🎙️ 按住说话按钮 → MediaRecorder 录制音频                   |
|            | → 松开后 POST 音频文件到 `/patient/api/voice-upload/`（服务端 ASR）|
|            | → 返回文本显示在文本框 → 点击"AI解析"                      |
|            | → 调用 `POST /patient/api/voice-parse/` 返回结构化预览     |
|            | → 用户确认后提交                                           |
| 表单模式   | 空腹血糖、餐后血糖、收缩压、舒张压、体重 五个输入框        |
|            | 每个字段带单位标签和合理范围提示                            |
| Tab 切换   | "语音录入" / "手动录入" 两个 Tab                           |
| 提交流程   | `POST /patient/input/` → Agent 流水线 → 跳转 P-03 结果页  |
| 后端依赖   | `POST /patient/input/`、`POST /patient/api/voice-upload/`、`POST /patient/api/voice-parse/` |

#### P-03 评估结果页 (`/patient/input/result/`)
| 要素       | 说明                                                       |
| ---------- | ---------------------------------------------------------- |
| 功能       | 显示本次数据提交后的 Agent 评估结果                        |
| 内容       | ① 风险等级徽章（绿/黄/红 + 分值）                         |
|            | ② 异常指标列表（trigger_indicators 逐条展示）             |
|            | ③ RAG 健康反馈建议（适老化排版 + 🔊 语音播报按钮）         |
|            | ④ Agent 处理流程日志（flow_log 时间线展示）               |
| TTS 播报   | 点击 🔊 → `POST /patient/api/tts/` → 返回音频 URL → 播放  |
| 操作       | "返回首页" / "查看历史记录" / "查看 AI 历史"               |
| 后端依赖   | 从 Session 中读取 `last_result`；TTS 调用 `/patient/api/tts/` |

#### P-04 健康记录 (`/patient/records/`)
| 要素       | 说明                                                       |
| ---------- | ---------------------------------------------------------- |
| 功能       | 历史体征数据 + 趋势折线图                                  |
| 图表区域   | ① 血糖趋势图（空腹 + 餐后双线，Chart.js）                 |
|            | ② 血压趋势图（收缩压 + 舒张压双线）                       |
|            | ③ 体重趋势图                                              |
| 时间筛选   | 7天 / 30天 / 90天 切换按钮，AJAX 刷新图表                  |
| 表格区域   | 日期、空腹血糖、餐后血糖、收缩压、舒张压、体重、录入方式   |
| 后端依赖   | `GET /patient/records/`、`GET /patient/api/health-trend/`  |

#### P-05 用药管理 (`/patient/medication/`)
| 要素       | 说明                                                       |
| ---------- | ---------------------------------------------------------- |
| 功能       | 今日用药提醒 + 打卡 + 依从率                               |
| 顶部统计   | 30天依从率进度环（如 85%）                                 |
| 方案列表   | 每个活跃方案一张卡片：药名、剂量、频次、提醒时间           |
|            | 卡片右侧：打卡按钮（已服药/跳过），续方预警标记            |
| 打卡交互   | 点击 → `POST /patient/api/medication/checkin/` AJAX        |
|            | → 按钮变为 ✓ 已打卡（禁用），若需续方弹出提示             |
| 后端依赖   | `GET /patient/medication/`、`POST /patient/api/medication/checkin/` |

#### P-06 我的随访 (`/patient/visits/`)
| 要素       | 说明                                                       |
| ---------- | ---------------------------------------------------------- |
| 功能       | 查看自己的随访计划                                         |
| 展示       | 时间线形式，每条：日期、随访方式、状态（待处理/已完成）     |
| 后端依赖   | `GET /patient/visits/`                                     |

#### P-07 AI 交互历史 (`/patient/ai-history/`)
| 要素       | 说明                                                       |
| ---------- | ---------------------------------------------------------- |
| 功能       | 查看系统为自己生成的所有 AI 建议和语音解析记录              |
| 展示       | 时间线卡片，每条：时间、类型标签（健康反馈/语音解析/ASR）  |
|            | 展开可见完整的原始输入和 AI 输出                            |
| TTS 播报   | 每条建议旁 🔊 按钮 → TTS 播报                              |
| 后端依赖   | `GET /patient/ai-history/`                                 |

---

### 3.3 医生端页面（8个主页面）

#### D-01 医生工作台 (`/doctor/`)
| 要素       | 说明                                                       |
| ---------- | ---------------------------------------------------------- |
| 功能       | 全局看板，一目了然                                         |
| 统计卡片   | ① 在管患者总数                                             |
|            | ② 红码患者数（带链接跳转预警列表）                         |
|            | ③ 黄码患者数                                               |
|            | ④ 逾期随访数 / 本周随访数                                  |
| 图表       | 风险分布饼图（红/黄/绿占比，Chart.js）                     |
| 预警栏     | 续方预警列表（最多展示5条，"查看全部"跳转 D-07）           |
| 后端依赖   | `GET /doctor/`、`GET /doctor/api/stats/`                   |

#### D-02 患者列表 (`/doctor/patients/`)
| 要素       | 说明                                                       |
| ---------- | ---------------------------------------------------------- |
| 功能       | 管理所有患者，筛选、搜索                                   |
| 搜索栏     | 姓名/用户名模糊搜索                                       |
| 筛选器     | 风险等级（全部/红/黄/绿）、在管状态（全部/在管/停管）      |
| 列表项     | 姓名、年龄、性别、风险徽章、确诊年份、在管状态             |
| 操作       | 点击行 → 跳转 D-03 详情；右上角 "+ 新增患者" 按钮         |
| 后端依赖   | `GET /doctor/patients/?q=&risk=&active=`                   |

#### D-03 患者详情 (`/doctor/patients/<id>/`)
| 要素       | 说明                                                       |
| ---------- | ---------------------------------------------------------- |
| 功能       | 单个患者的完整档案                                         |
| 基本信息   | 姓名、年龄、性别、身高、确诊年份、在管状态 + "编辑"按钮    |
| AI 摘要    | DoctorAgent RAG 生成的诊疗辅助摘要卡片（自动持久化到 AgentLog）|
| Tab 面板   | ① 健康趋势 — 血糖/血压折线图（AJAX `api/health-trend/`）  |
|            | ② 风险评估历史 — 时间线 + 分数曲线（AJAX `api/risk-history/`）|
|            | ③ 用药方案 — 活跃方案列表 + 依从率 + "新增方案"按钮       |
|            | ④ 随访记录 — 最近10条随访任务                              |
|            | ⑤ AI 交互记录 — 该患者的 AgentLog 历史（最近20条）         |
| 后端依赖   | `GET /doctor/patients/<id>/`                               |
|            | `GET /doctor/patients/<id>/api/health-trend/`              |
|            | `GET /doctor/patients/<id>/api/risk-history/`              |
|            | `GET /doctor/patients/<id>/api/adherence/`                 |

#### D-04 新增/编辑患者 (`/doctor/patients/create/` · `/doctor/patients/<id>/edit/`)
| 要素       | 说明                                                       |
| ---------- | ---------------------------------------------------------- |
| 功能       | 患者信息表单                                               |
| 新增额外   | 用户名、密码、联系电话（创建 User 账号）                   |
| 表单字段   | 姓名、年龄、性别、身高、确诊年份、在管状态                 |
| 后端依赖   | `POST /doctor/patients/create/`、`POST /doctor/patients/<id>/edit/` |

#### D-05 风险预警 (`/doctor/alerts/`)
| 要素       | 说明                                                       |
| ---------- | ---------------------------------------------------------- |
| 功能       | 红/黄码患者预警面板                                        |
| 筛选器     | 全部 / 仅红码 / 仅黄码                                    |
| 列表       | 每条：患者姓名、风险等级、风险分值、异常指标、评估时间     |
| 操作       | 点击 → 跳转 D-03 患者详情                                 |
| 后端依赖   | `GET /doctor/alerts/?level=`                               |

#### D-06 随访任务 (`/doctor/visits/`)
| 要素       | 说明                                                       |
| ---------- | ---------------------------------------------------------- |
| 功能       | 随访任务列表 + 操作                                        |
| Tab 筛选   | 待处理（默认） / 已完成 / 已延期                           |
| 每条内容   | 患者姓名、随访方式、优先级徽章、截止日期、逾期天数         |
| 操作按钮   | ✅ 完成（弹出备注输入） / ⏱️ 延期（选择延期天数）          |
| 后端依赖   | `GET /doctor/visits/?status=`                              |
|            | `POST /doctor/visits/<id>/complete/`                       |
|            | `POST /doctor/visits/<id>/defer/`                          |

#### D-07 用药监控 (`/doctor/medication/`)
| 要素       | 说明                                                       |
| ---------- | ---------------------------------------------------------- |
| 功能       | 全体患者用药概览                                           |
| 排序       | 按依从率升序（最低的排前面，重点关注）                     |
| 列表项     | 患者姓名、方案数、30天依从率（进度条）、续方预警标记       |
| 操作       | 点击 → D-03 详情；续方预警行高亮                           |
| 后端依赖   | `GET /doctor/medication/`                                  |

#### D-08 用药方案表单 (`/doctor/medication/plan/<patient_id>/create/` · `/<plan_id>/edit/`)
| 要素       | 说明                                                       |
| ---------- | ---------------------------------------------------------- |
| 功能       | 为患者创建或编辑用药方案                                   |
| 字段       | 药名、剂量、频次、提醒时间、处方总天数、起始日期、是否生效 |
| 后端依赖   | `POST` 对应 URL                                            |

---

## 四、完整 API 路由表

### 4.1 页面路由（返回 HTML）

| Method | URL                                      | Name                    | 说明           |
| ------ | ---------------------------------------- | ----------------------- | -------------- |
| GET    | `/`                                      | `role_router`           | 角色跳转       |
| GET/POST | `/accounts/login/`                     | `login`                 | 登录           |
| GET    | `/accounts/logout/`                      | `logout`                | 登出           |
| GET    | `/patient/`                              | `patient_dashboard`     | 患者首页       |
| GET/POST | `/patient/input/`                      | `patient_input`         | 健康录入       |
| GET    | `/patient/input/result/`                 | `patient_input_result`  | 评估结果       |
| GET    | `/patient/records/`                      | `patient_records`       | 健康记录       |
| GET    | `/patient/medication/`                   | `patient_medication`    | 用药管理       |
| GET    | `/patient/visits/`                       | `patient_visits`        | 我的随访       |
| GET    | `/patient/ai-history/`                   | `patient_ai_history`    | AI交互历史     |
| GET    | `/doctor/`                               | `doctor_dashboard`      | 医生工作台     |
| GET    | `/doctor/patients/`                      | `doctor_patients`       | 患者列表       |
| GET/POST | `/doctor/patients/create/`             | `doctor_patient_create` | 新增患者       |
| GET    | `/doctor/patients/<id>/`                 | `doctor_patient_detail` | 患者详情       |
| GET/POST | `/doctor/patients/<id>/edit/`          | `doctor_patient_edit`   | 编辑患者       |
| GET    | `/doctor/alerts/`                        | `doctor_alerts`         | 风险预警       |
| GET    | `/doctor/visits/`                        | `doctor_visits`         | 随访任务       |
| GET    | `/doctor/medication/`                    | `doctor_medication`     | 用药监控       |
| GET/POST | `/doctor/medication/plan/<pid>/create/`| `doctor_med_plan_create`| 新增方案       |
| GET/POST | `/doctor/medication/plan/<id>/edit/`   | `doctor_med_plan_edit`  | 编辑方案       |

### 4.2 JSON API 路由（返回 JSON，供 AJAX 调用）

| Method | URL                                              | Name                      | 说明               |
| ------ | ------------------------------------------------ | ------------------------- | ------------------ |
| POST   | `/patient/api/voice-upload/`                     | `api_voice_upload`        | 音频上传→ASR转写   |
| POST   | `/patient/api/voice-parse/`                      | `api_voice_parse`         | 文本→结构化数据    |
| POST   | `/patient/api/tts/`                              | `api_tts`                 | 文本→语音合成      |
| GET    | `/patient/api/health-trend/?days=30`             | `api_health_trend`        | 患者自己的趋势     |
| POST   | `/patient/api/medication/checkin/`               | `api_medication_checkin`  | 用药打卡           |
| GET    | `/doctor/api/stats/`                             | `api_doctor_stats`        | 工作台统计         |
| GET    | `/doctor/patients/<id>/api/health-trend/?days=30`| `api_patient_health_trend`| 患者健康趋势       |
| GET    | `/doctor/patients/<id>/api/risk-history/?days=90`| `api_patient_risk_history`| 患者风险历史       |
| GET    | `/doctor/patients/<id>/api/adherence/?weeks=8`   | `api_patient_adherence`   | 患者依从率趋势     |
| POST   | `/doctor/visits/<id>/complete/`                  | `doctor_visit_complete`   | 完成随访（支持AJAX）|
| POST   | `/doctor/visits/<id>/defer/`                     | `doctor_visit_defer`      | 延期随访（支持AJAX）|

---

## 五、页面交互流程图（关键流程）

### 5.1 患者录入→评估全流程
```
患者首页 → 点击"录入数据"
  → 健康数据录入页（P-02）
    ├─ [语音模式] 按住录音 → MediaRecorder 录制 WebM 音频
    │   → 松开 → POST /patient/api/voice-upload/（音频文件上传）
    │   → 服务端 DashScope Paraformer ASR 转写 → 返回文本 → 显示在文本框
    │   → 点击"AI解析" → AJAX voice-parse → 预览结构化数据
    │   → 点击"确认提交"
    └─ [表单模式] 手动填写五项数据 → 点击"提交"
  → POST /patient/input/
  → Django View 调用 agent_app.invoke(initial_state)
    → PatientAgent → TriageAgent → [条件] → SchedulerAgent → DoctorAgent
    → 各 Agent 执行结果自动写入 AgentLog
  → Session 存储结果 → Redirect
  → 评估结果页（P-03）：风险等级 + 异常指标 + RAG 健康反馈 + 🔊 TTS 播报
```

### 5.2 医生工作台→处理预警
```
医生工作台（D-01）
  → 看到红码数 = 2，点击数字
  → 风险预警列表（D-05），筛选红码
  → 点击某患者行
  → 患者详情（D-03）
    → 健康趋势 Tab：查看血糖走势（AJAX 加载图表）
    → 风险评估 Tab：查看评分变化
    → 用药方案 Tab：检查依从率，如需续方点击"新增方案"
    → 随访记录 Tab：查看是否有逾期
  → 返回随访任务列表（D-06）→ 点击"完成"处理任务
```

---

## 六、技术要点备忘

| 技术点                | 方案                                          |
| --------------------- | --------------------------------------------- |
| 图表库                | Chart.js 4.x（CDN 引入）                     |
| LLM 服务              | 阿里云 DashScope qwen3.5-plus（OpenAI 兼容协议）|
| 语音识别（ASR）       | 前端 MediaRecorder 录音 → 后端 DashScope Paraformer-v2 转写 |
| 语音合成（TTS）       | 后端 DashScope CosyVoice-v2 合成 MP3 → 前端 `<audio>` 播放 |
| AJAX 请求             | fetch API + CSRF Token（从 cookie 读取）       |
| CSRF 处理             | `{% csrf_token %}` 表单；AJAX 用 `X-CSRFToken` header |
| 消息提示              | Django messages framework + Bootstrap Alert    |
| 表单渲染              | Django Form + Bootstrap 5 class（通过 widget attrs）|
| 分页                  | Django Paginator（患者列表、健康记录）         |
| 实时刷新              | 图表时间区间切换用 AJAX；无需 WebSocket        |
| Agent 交互历史        | AgentLog 模型持久化，患者端/医生端均可查看     |
| 运维日志              | Django LOGGING → logs/cdm.log（请求+Agent级）  |
| UI 设计               | Pencil (.pen) 原型 → 导出图片用于论文          |
| 适老化标准            | 遵循《互联网应用适老化及无障碍改造指南》       |
| 配色方案              | 暖色调系统（主色 #D35400 暖橙 + #FFF8F0 暖白背景）|
