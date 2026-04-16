# CDM System 基础功能测试方案

## 1. 测试目的

在 DashScope API Key 配置完成后，验证系统各基础模块能否正常工作，确保核心链路跑通。

## 2. 测试范围

| 编号 | 测试模块 | 测试内容 | 前置条件 |
|------|----------|----------|----------|
| T-01 | Django 启动 | 框架初始化、.env 加载、API Key 读取 | .env 中 DASHSCOPE_API_KEY 已填写 |
| T-02 | 数据库 ORM | migrate、User/Patient/HealthRecord CRUD | T-01 通过 |
| T-03 | LLM API | DashScope Qwen3.5 基础对话调用 | DASHSCOPE_API_KEY 有效 |
| T-04 | 语音文本解析 | LLM 解析口语化健康数据为结构化 JSON | T-03 通过 |
| T-05 | 风险评估 | 加权评分算法 + 绿/黄/红三级映射 | 纯本地计算，无外部依赖 |
| T-06 | RAG 知识库 | ChromaDB 初始化 + 语义检索 | knowledge_base/*.txt 存在 |
| T-07 | TTS (DashScope) | CosyVoice 语音合成，验证音频文件生成 | DASHSCOPE_API_KEY 有效 |
| T-08 | TTS (Edge) | Edge TTS 免费备选方案 | 网络连通 |
| T-09 | RAG + LLM | 完整的健康反馈生成链路 | T-03 + T-06 通过 |
| T-10 | Seed 脚本 | management command 数据填充 | T-02 通过 |

## 3. 测试环境

- OS: Windows 10/11
- Python: 3.10+
- Django: 5.2.13
- 数据库: SQLite3（开发模式）
- LLM: DashScope qwen3.5-plus
- ASR: DashScope paraformer-v2（本次不测试，需音频输入）
- TTS: DashScope cosyvoice-v2 + Edge TTS

## 4. 运行方式

```bash
cd cdm_system
python ../test/basefunction/run_tests.py
```

## 5. 输出文件

| 文件 | 说明 |
|------|------|
| `report.md` | 测试报告（Markdown 格式，含通过率、详细结果、结论） |
| `results.json` | 原始测试数据（JSON 格式，供程序读取） |

## 6. 通过标准

- 全部 10 项测试通过（T-01 ~ T-10）
- LLM API 响应延迟 < 10s
- TTS 生成的音频文件 > 100 bytes
- Seed 脚本生成数据量符合预期（≥5 患者，≥50 健康记录）
