"""
语音交互服务模块。
ASR（语音识别）：支持 OpenAI Whisper API / 火山引擎（字节豆包）/ 通义听悟，通过 settings 切换。
TTS（语音合成）：支持 edge-tts（微软免费）/ 火山引擎 TTS / 通义语音合成，通过 settings 切换。
供应商切换仅需修改 settings.py 中的 ASR_PROVIDER / TTS_PROVIDER 配置项。
"""
import asyncio
import hashlib
import io
import logging
import time
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)

MEDIA_DIR = Path(settings.BASE_DIR) / "media" / "tts_cache"


# ═══════════════════════ ASR 语音识别 ═══════════════════════


def transcribe_audio(audio_bytes: bytes, filename: str = "audio.webm") -> dict:
    """
    将音频字节流转写为文本。
    返回 {"text": "...", "duration_ms": int, "provider": str}
    支持供应商：whisper_api / volcano / dashscope
    """
    provider = getattr(settings, "ASR_PROVIDER", "whisper_api")
    start = time.time()

    try:
        dispatch = {
            "whisper_api": _asr_whisper_api,
            "volcano": _asr_volcano,
            "dashscope": _asr_dashscope,
        }
        asr_fn = dispatch.get(provider, _asr_whisper_api)
        text = asr_fn(audio_bytes, filename)

        duration_ms = int((time.time() - start) * 1000)
        logger.info("ASR 完成 [%s]: %d ms, %d 字", provider, duration_ms, len(text))
        return {"text": text, "duration_ms": duration_ms, "provider": provider}

    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        logger.error("ASR 失败 [%s]: %s", provider, e)
        return {"text": "", "duration_ms": duration_ms, "provider": provider, "error": str(e)}


def _asr_whisper_api(audio_bytes: bytes, filename: str) -> str:
    """OpenAI Whisper API（兼容 OpenAI 协议的代理也可使用）。"""
    from openai import OpenAI

    client = OpenAI(
        api_key=getattr(settings, "LLM_API_KEY", ""),
        base_url=getattr(settings, "ASR_BASE_URL", None) or getattr(settings, "LLM_BASE_URL", None),
    )
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = filename

    response = client.audio.transcriptions.create(
        model=getattr(settings, "ASR_MODEL", "whisper-1"),
        file=audio_file,
        language="zh",
        response_format="text",
    )
    return response.strip() if isinstance(response, str) else response.text.strip()


def _asr_volcano(audio_bytes: bytes, filename: str) -> str:
    """
    火山引擎（字节豆包）语音识别。
    需要 settings 中配置 VOLCANO_APP_ID / VOLCANO_ACCESS_TOKEN。
    API 文档：https://www.volcengine.com/docs/6561/80818
    """
    import json
    import base64
    import urllib.request

    app_id = getattr(settings, "VOLCANO_APP_ID", "")
    token = getattr(settings, "VOLCANO_ACCESS_TOKEN", "")
    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

    payload = {
        "app": {"appid": app_id, "cluster": "volcengine_streaming_common"},
        "user": {"uid": "cdm_system"},
        "audio": {
            "format": "wav",
            "codec": "raw",
            "rate": 16000,
            "bits": 16,
            "channel": 1,
            "language": "zh-CN",
        },
        "request": {"nbest": 1, "workflow": "audio_in,resample,partition,vad,fe,decode"},
        "additions": {"with_speaker_info": "false"},
    }
    payload["audio"]["data"] = audio_b64

    url = "https://openspeech.bytedance.com/api/v1/asr"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer; {token}",
    }
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read().decode("utf-8"))

    if result.get("code") == 1000:
        return result.get("result", [{}])[0].get("text", "")
    raise RuntimeError(f"火山引擎 ASR 返回错误: code={result.get('code')}, message={result.get('message')}")


def _asr_dashscope(audio_bytes: bytes, filename: str) -> str:
    """
    通义听悟 / 阿里云 Paraformer 语音识别。
    需要 settings 中配置 DASHSCOPE_API_KEY（或 LLM_API_KEY）。
    通过 OpenAI 兼容协议调用，模型可选 paraformer-v2 / fun-asr / sensevoice-v1。
    """
    from openai import OpenAI

    api_key = getattr(settings, "DASHSCOPE_API_KEY", "") or getattr(settings, "LLM_API_KEY", "")
    client = OpenAI(
        api_key=api_key,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = filename

    response = client.audio.transcriptions.create(
        model=getattr(settings, "ASR_MODEL", "paraformer-v2"),
        file=audio_file,
        language="zh",
    )
    return response.text.strip() if hasattr(response, "text") else str(response).strip()


# ═══════════════════════ TTS 语音合成 ═══════════════════════


def synthesize_speech(text: str, voice: str = None) -> dict:
    """
    将文本合成为语音音频。
    返回 {"audio_path": str, "duration_ms": int, "provider": str}
    支持供应商：edge_tts / volcano / dashscope
    """
    if not voice:
        voice = getattr(settings, "TTS_VOICE", "zh-CN-XiaoxiaoNeural")
    provider = getattr(settings, "TTS_PROVIDER", "edge_tts")
    start = time.time()

    try:
        dispatch = {
            "edge_tts": _tts_edge,
            "volcano": _tts_volcano,
            "dashscope": _tts_dashscope,
        }
        tts_fn = dispatch.get(provider, _tts_edge)
        audio_path = tts_fn(text, voice)

        duration_ms = int((time.time() - start) * 1000)
        logger.info("TTS 完成 [%s]: %d ms, voice=%s", provider, duration_ms, voice)
        return {"audio_path": audio_path, "duration_ms": duration_ms, "provider": provider}

    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        logger.error("TTS 失败 [%s]: %s", provider, e)
        return {"audio_path": "", "duration_ms": duration_ms, "provider": provider, "error": str(e)}


def _get_cache_path(voice: str, text: str) -> Path:
    """根据 voice + text 生成缓存文件路径（MD5 去重）。"""
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    text_hash = hashlib.md5(f"{voice}:{text}".encode()).hexdigest()[:12]
    return MEDIA_DIR / f"{text_hash}.mp3"


def _tts_edge(text: str, voice: str) -> str:
    """edge-tts：微软 Edge 在线合成，免费、中文效果好、无需 API Key。"""
    import edge_tts

    output_file = _get_cache_path(voice, text)
    if output_file.exists():
        return str(output_file.relative_to(settings.BASE_DIR))

    communicate = edge_tts.Communicate(text, voice)

    loop = None
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        pass

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            pool.submit(_run_async_save, communicate, str(output_file)).result(timeout=30)
    else:
        asyncio.run(communicate.save(str(output_file)))

    return str(output_file.relative_to(settings.BASE_DIR))


def _run_async_save(communicate, output_path: str):
    """在新线程中运行异步 edge-tts 保存。"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(communicate.save(output_path))
    finally:
        loop.close()


def _tts_volcano(text: str, voice: str) -> str:
    """
    火山引擎 TTS（字节豆包语音合成）。
    需要 settings 中配置 VOLCANO_APP_ID / VOLCANO_ACCESS_TOKEN。
    voice 参数对应火山引擎的 voice_type，如 "zh_female_shuangkuaisisi_moon_bigtts"。
    """
    import json
    import base64
    import urllib.request

    output_file = _get_cache_path(voice, text)
    if output_file.exists():
        return str(output_file.relative_to(settings.BASE_DIR))

    app_id = getattr(settings, "VOLCANO_APP_ID", "")
    token = getattr(settings, "VOLCANO_ACCESS_TOKEN", "")

    payload = {
        "app": {"appid": app_id, "cluster": "volcano_tts"},
        "user": {"uid": "cdm_system"},
        "audio": {"voice_type": voice, "encoding": "mp3", "speed_ratio": 0.9},
        "request": {"text": text, "operation": "query"},
    }

    url = "https://openspeech.bytedance.com/api/v1/tts"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer; {token}",
    }
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read().decode("utf-8"))

    if result.get("code") == 3000:
        audio_b64 = result.get("data", "")
        output_file.write_bytes(base64.b64decode(audio_b64))
        return str(output_file.relative_to(settings.BASE_DIR))

    raise RuntimeError(f"火山引擎 TTS 返回错误: code={result.get('code')}, message={result.get('message')}")


def _tts_dashscope(text: str, voice: str) -> str:
    """
    通义语音合成（阿里云 DashScope CosyVoice）。
    需要 settings 中配置 DASHSCOPE_API_KEY（或 LLM_API_KEY）。
    模型通过 settings.TTS_MODEL 指定，默认 cosyvoice-v2。
    voice 参数对应 CosyVoice 音色 ID，如 "longxiaochun"（温和女声）。
    API 文档：https://help.aliyun.com/zh/model-studio/non-realtime-cosyvoice-api
    非流式模式：API 返回 JSON，其中 output.audio.url 为音频下载地址（24h 有效）。
    """
    import json
    import urllib.request

    output_file = _get_cache_path(voice, text)
    if output_file.exists():
        return str(output_file.relative_to(settings.BASE_DIR))

    api_key = getattr(settings, "DASHSCOPE_API_KEY", "") or getattr(settings, "LLM_API_KEY", "")
    tts_model = getattr(settings, "TTS_MODEL", "cosyvoice-v2")

    payload = {
        "model": tts_model,
        "input": {
            "text": text,
            "voice": voice,
            "format": "mp3",
            "sample_rate": 22050,
        },
    }

    url = "https://dashscope.aliyuncs.com/api/v1/services/audio/tts/SpeechSynthesizer"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read().decode("utf-8"))

    audio_url = result.get("output", {}).get("audio", {}).get("url")
    if not audio_url:
        raise RuntimeError(f"通义 TTS 未返回音频 URL: {result}")

    with urllib.request.urlopen(audio_url, timeout=30) as audio_resp:
        output_file.write_bytes(audio_resp.read())

    return str(output_file.relative_to(settings.BASE_DIR))


# ═══════════════════════ 供应商配置参考 ═══════════════════════

PROVIDER_CONFIGS = {
    "dashscope": {
        "LLM_MODEL": "qwen3.5-plus",
        "LLM_BASE_URL": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "ASR_PROVIDER": "dashscope",
        "ASR_MODEL": "paraformer-v2",
        "TTS_PROVIDER": "dashscope",
        "TTS_MODEL": "cosyvoice-v3-flash",
        "TTS_VOICE": "longxiaochun_v3",
        "desc": "通义千问全家桶（阿里云 DashScope），LLM/ASR/TTS 共用一个 DASHSCOPE_API_KEY",
    },
    "whisper_api": {
        "ASR_PROVIDER": "whisper_api",
        "ASR_MODEL": "whisper-1",
        "desc": "OpenAI Whisper API，需设置 LLM_API_KEY",
    },
    "volcano": {
        "ASR_PROVIDER": "volcano",
        "TTS_PROVIDER": "volcano",
        "TTS_VOICE": "zh_female_shuangkuaisisi_moon_bigtts",
        "desc": "火山引擎（字节豆包），需设置 VOLCANO_APP_ID + VOLCANO_ACCESS_TOKEN",
    },
    "edge_tts": {
        "TTS_PROVIDER": "edge_tts",
        "TTS_VOICE": "zh-CN-XiaoxiaoNeural",
        "desc": "微软 Edge TTS，免费，无需 API Key",
    },
}

RECOMMENDED_VOICES = {
    "dashscope": {
        "female_gentle": "longxiaochun_v3",
        "male_calm": "longshu_v3",
        "female_warm": "longanrou_v3",
    },
    "edge_tts": {
        "female_gentle": "zh-CN-XiaoxiaoNeural",
        "female_warm": "zh-CN-XiaohanNeural",
        "male_calm": "zh-CN-YunxiNeural",
        "male_elder": "zh-CN-YunjianNeural",
    },
    "volcano": {
        "female_warm": "zh_female_shuangkuaisisi_moon_bigtts",
        "male_calm": "zh_male_chunhou_moon_bigtts",
    },
}
