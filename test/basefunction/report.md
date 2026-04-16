# CDM System 基础功能测试报告

> 生成时间：2026-04-16 20:50:05
> 测试环境：Python 3.11.5, win32

## 测试概况

| 指标 | 数值 |
|------|------|
| 总用例数 | 10 |
| 通过 | 10 |
| 失败 | 0 |
| 跳过 | 0 |
| **通过率** | **100.0%** |

## 详细结果

| 编号 | 测试项 | 结果 | 耗时(ms) | 说明 |
|------|--------|------|----------|------|
| T-01 | Django 启动 + .env 加载 | PASS | 387 | LLM_MODEL=qwen3.5-plus, ASR=dashscope/paraformer-v2, TTS=dashscope/cosyvoice-v3-flash |
| T-02 | 数据库迁移 & ORM | PASS | 494 | User/Patient/HealthRecord CRUD 正常, migrate 成功 |
| T-03 | LLM API (Qwen) | PASS | 25137 | model=qwen3.5-plus, response=空腹血糖是指至少禁食 8 小时后测得的血液中葡萄糖浓度。... |
| T-04 | LLM 语音文本解析 | PASS | 29332 | input='今天早上空腹血糖7.8，血压有点高，上面的140下面的90，...', parsed={"fasting_glucose": 7.8, "postmeal_glucose": null, "systolic_bp": 140, |
| T-05 | 风险评估算法 | PASS | 1 | green=1.0/green, red=3.0/red, triggers_red=4 |
| T-06 | RAG 知识库初始化 & 检索 | PASS | 1009 | 知识库 16 段落, 检索到 3 条, top1=低血糖的识别与处理：低血糖是指血糖低于3.9 mmol/L，常见症状包括心慌、手... |
| T-07 | TTS (DashScope CosyVoice) | PASS | 5495 | provider=dashscope, path=media\tts_cache\d048d7707a00.mp3, size=56933B, latency=5494ms |
| T-08 | TTS 备选 (Edge TTS) | PASS | 2008 | voice=zh-CN-XiaoxiaoNeural, path=media\tts_cache\5611f1f3313c.mp3, size=20880B |
| T-09 | RAG + LLM 健康反馈 | PASS | 78829 | feedback=您好呀，叔叔/阿姨！看到您今天的健康数据了，咱们一起来瞧瞧，别着急，这个“黄色”风险等级就是提醒咱们要多留点心，但并不是说情况很危险，咱们慢慢调整就好。  首先... |
| T-10 | Seed 数据脚本 | PASS | 5429 | doctors=1, patients=5, health_records=75 |

## 测试项说明

| 编号 | 说明 |
|------|------|
| T-01 | 验证 Django 框架启动、.env 文件加载、API Key 配置读取 |
| T-02 | 验证数据库迁移、User/Patient/HealthRecord 模型 CRUD |
| T-03 | 验证 DashScope Qwen LLM API 调用（OpenAI 兼容协议） |
| T-04 | 验证 LLM 解析口语化健康数据为结构化 JSON |
| T-05 | 验证加权风险评分算法（绿/黄/红三级分类） |
| T-06 | 验证 ChromaDB 知识库初始化 + 语义检索 |
| T-07 | 验证 DashScope CosyVoice TTS 语音合成 |
| T-08 | 验证 Edge TTS 免费备选方案 |
| T-09 | 验证 RAG（检索增强生成）健康反馈完整链路 |
| T-10 | 验证 Seed 数据填充脚本（管理命令 python manage.py seed） |

## 结论

所有基础功能测试均通过，系统核心链路（LLM/TTS/RAG/风险评估/数据库）运行正常。
