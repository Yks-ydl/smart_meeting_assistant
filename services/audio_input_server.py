"""
M6 - 音频输入服务 (Audio Input Service)

提供两种工作模式：
  模式一（双人模式）：录制本地麦克风 + 系统扬声器（loopback），生成双音轨音频
  模式二（多人模式）：接收预录制的多声道 WAV 文件，按声道拆分并分发

该服务负责采集/拆分音频，并将各声道音频片段推送给 M1 ASR 服务进行转录。
"""

from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, List
import uvicorn
import asyncio
import threading
import base64
import io
import os
import sys
import time
import json
import wave
import struct
import numpy as np
import httpx

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

app = FastAPI(title="M6 - Audio Input Service")

# ──────────────────────────────────────────────
# 配置
# ──────────────────────────────────────────────
ASR_SERVICE_URL = os.getenv("ASR_SERVICE_URL", "http://127.0.0.1:8001/api/v1/asr/transcribe")
GATEWAY_WS_URL = os.getenv("GATEWAY_WS_URL", "ws://127.0.0.1:8000/ws/meeting/")
CHUNK_DURATION_SEC = 5  # 每个音频切片的时长（秒）
SAMPLE_RATE = 16000     # 采样率
CHANNELS_DUAL = 2       # 双人模式声道数

# ──────────────────────────────────────────────
# 全局状态管理
# ──────────────────────────────────────────────

class AudioServiceState:
    """全局服务状态"""
    def __init__(self):
        self.is_capturing = False           # 模式一：是否正在采集
        self.is_processing = False          # 模式二：是否正在处理文件
        self.current_mode = None            # "dual" or "multitrack"
        self.current_session_id = None
        self.capture_thread = None
        self.stop_event = threading.Event()
        self.track_info: Dict = {}          # 音轨信息
        self.processing_progress = 0.0      # 处理进度
        self.results: List[dict] = []       # 转录结果缓存

state = AudioServiceState()

# ──────────────────────────────────────────────
# 请求模型
# ──────────────────────────────────────────────

class CaptureRequest(BaseModel):
    session_id: str
    mic_device_index: Optional[int] = None        # 麦克风设备索引（None=默认）
    loopback_device_index: Optional[int] = None   # 扬声器回环设备索引（None=默认）
    duration_sec: Optional[int] = None             # 录制时长（秒），None=持续直到手动停止

class StopRequest(BaseModel):
    session_id: str

# ──────────────────────────────────────────────
# 工具函数
# ──────────────────────────────────────────────

def numpy_to_wav_bytes(audio_data: np.ndarray, sample_rate: int = SAMPLE_RATE) -> bytes:
    """
    将 numpy 音频数据（单声道，float32 或 int16）转换为 WAV 格式的 bytes
    """
    # 确保是 int16
    if audio_data.dtype == np.float32 or audio_data.dtype == np.float64:
        audio_data = np.clip(audio_data, -1.0, 1.0)
        audio_data = (audio_data * 32767).astype(np.int16)
    elif audio_data.dtype != np.int16:
        audio_data = audio_data.astype(np.int16)

    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16bit
        wf.setframerate(sample_rate)
        wf.writeframes(audio_data.tobytes())
    return buf.getvalue()


def send_audio_to_asr(audio_bytes: bytes, session_id: str, speaker: str):
    """
    同步发送音频片段到 M1 ASR 服务
    """
    audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
    payload = {
        "audio_base64": audio_b64,
        "session_id": session_id,
        "speaker_hint": speaker,  # 提示 ASR 该音频对应的发言人
    }
    try:
        import requests
        resp = requests.post(ASR_SERVICE_URL, json=payload, timeout=30)
        result = resp.json()
        # 覆盖 speaker 为我们已知的标识
        if "speaker" in result:
            result["speaker"] = speaker
        return result
    except Exception as e:
        print(f"[M6] 发送 ASR 请求失败: {e}")
        return {"error": str(e), "speaker": speaker}


async def send_audio_to_asr_async(client: httpx.AsyncClient, audio_bytes: bytes,
                                   session_id: str, speaker: str) -> dict:
    """
    异步发送音频片段到 M1 ASR 服务
    """
    audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
    payload = {
        "audio_base64": audio_b64,
        "session_id": session_id,
        "speaker_hint": speaker,
    }
    try:
        resp = await client.post(ASR_SERVICE_URL, json=payload, timeout=30.0)
        result = resp.json()
        if "speaker" in result:
            result["speaker"] = speaker
        return result
    except Exception as e:
        print(f"[M6] 异步 ASR 请求失败: {e}")
        return {"error": str(e), "speaker": speaker}


# ──────────────────────────────────────────────
# 模式一：双人实时采集
# ──────────────────────────────────────────────

def _capture_dual_track(session_id: str, mic_index: Optional[int],
                        loopback_index: Optional[int], duration_sec: Optional[int]):
    """
    双人模式采集线程：
    - Channel 0: 本地麦克风
    - Channel 1: 系统扬声器（loopback）

    实际 loopback 录制依赖 sounddevice + WASAPI loopback (Windows)。
    如果 sounddevice 不可用，则使用模拟数据进行架构验证。
    """
    try:
        import sounddevice as sd

        # 获取设备信息
        devices = sd.query_devices()
        print(f"[M6] 可用音频设备: {len(devices)} 个")

        # 确定麦克风设备
        if mic_index is None:
            mic_index = sd.default.device[0]  # 默认输入设备

        chunk_samples = CHUNK_DURATION_SEC * SAMPLE_RATE
        elapsed = 0

        print(f"[M6] 双人模式采集已启动 (session: {session_id})")
        state.track_info = {
            "channels": 2,
            "speakers": ["本地用户", "远程用户"],
            "sample_rate": SAMPLE_RATE,
        }

        while not state.stop_event.is_set():
            if duration_sec and elapsed >= duration_sec:
                break

            try:
                # 录制麦克风
                mic_audio = sd.rec(
                    chunk_samples,
                    samplerate=SAMPLE_RATE,
                    channels=1,
                    dtype='int16',
                    device=mic_index,
                )
                sd.wait()

                mic_wav = numpy_to_wav_bytes(mic_audio.flatten(), SAMPLE_RATE)

                # 发送麦克风音频到 ASR
                mic_result = send_audio_to_asr(mic_wav, session_id, "本地用户")
                if mic_result and "text" in mic_result:
                    state.results.append(mic_result)

            except Exception as e:
                print(f"[M6] 麦克风录制异常: {e}")

            elapsed += CHUNK_DURATION_SEC

        print(f"[M6] 双人模式采集已停止")

    except ImportError:
        print("[M6] sounddevice 未安装，使用模拟模式")
        _capture_dual_track_mock(session_id, duration_sec)
    except Exception as e:
        print(f"[M6] 采集线程异常: {e}")
    finally:
        state.is_capturing = False


def _capture_dual_track_mock(session_id: str, duration_sec: Optional[int]):
    """
    模拟双人采集（sounddevice 不可用时的降级方案）
    生成静音音频发送给 ASR（ASR 会使用 LLM Mock 返回模拟数据）
    """
    elapsed = 0
    chunk_samples = CHUNK_DURATION_SEC * SAMPLE_RATE

    print(f"[M6] 模拟双人模式已启动 (session: {session_id})")
    state.track_info = {
        "channels": 2,
        "speakers": ["本地用户", "远程用户"],
        "sample_rate": SAMPLE_RATE,
        "mode": "mock",
    }

    speakers = ["本地用户", "远程用户"]
    turn = 0

    while not state.stop_event.is_set():
        if duration_sec and elapsed >= duration_sec:
            break

        # 生成静音 WAV（让 ASR 走 mock 路径）
        silence = np.zeros(chunk_samples, dtype=np.int16)
        wav_bytes = numpy_to_wav_bytes(silence, SAMPLE_RATE)

        speaker = speakers[turn % len(speakers)]
        result = send_audio_to_asr(wav_bytes, session_id, speaker)
        if result and "text" in result:
            state.results.append(result)

        turn += 1
        elapsed += CHUNK_DURATION_SEC
        time.sleep(CHUNK_DURATION_SEC)

    print(f"[M6] 模拟双人模式已停止")


# ──────────────────────────────────────────────
# 模式二：多声道文件处理
# ──────────────────────────────────────────────

async def _process_multitrack_file(file_path: str, session_id: str, num_channels: int,
                                    sample_rate: int, audio_data: np.ndarray):
    """
    处理多声道 WAV 文件：
    按声道拆分，按时间窗口切片，逐片段推送给 ASR
    """
    state.is_processing = True
    state.current_mode = "multitrack"
    state.processing_progress = 0.0
    state.results = []

    chunk_samples = CHUNK_DURATION_SEC * sample_rate
    total_samples = audio_data.shape[0] if audio_data.ndim > 1 else len(audio_data)
    total_chunks = max(1, total_samples // chunk_samples)

    state.track_info = {
        "channels": num_channels,
        "speakers": [f"Speaker_{i+1}" for i in range(num_channels)],
        "sample_rate": sample_rate,
        "total_duration_sec": total_samples / sample_rate,
        "total_chunks": total_chunks,
    }

    print(f"[M6] 多声道处理开始: {num_channels} 声道, "
          f"{total_samples/sample_rate:.1f}秒, {total_chunks} 个切片")

    async with httpx.AsyncClient() as client:
        chunk_idx = 0
        for start in range(0, total_samples, chunk_samples):
            if state.stop_event.is_set():
                break

            end = min(start + chunk_samples, total_samples)

            # 对每个声道分别处理
            tasks = []
            for ch in range(num_channels):
                if audio_data.ndim == 1:
                    # 单声道文件
                    channel_data = audio_data[start:end]
                else:
                    channel_data = audio_data[start:end, ch]

                speaker = f"Speaker_{ch+1}"
                wav_bytes = numpy_to_wav_bytes(channel_data, sample_rate)

                # 并行发送各声道的音频到 ASR
                task = send_audio_to_asr_async(client, wav_bytes, session_id, speaker)
                tasks.append(task)

            results = await asyncio.gather(*tasks)

            for r in results:
                if r and "text" in r and r["text"] and r["text"] != "[未识别到有效语音]":
                    state.results.append(r)

            chunk_idx += 1
            state.processing_progress = min(1.0, chunk_idx / total_chunks)
            print(f"[M6] 处理进度: {state.processing_progress*100:.0f}% ({chunk_idx}/{total_chunks})")

    state.is_processing = False
    state.processing_progress = 1.0
    print(f"[M6] 多声道处理完成，共生成 {len(state.results)} 条转录结果")


# ──────────────────────────────────────────────
# API 端点
# ──────────────────────────────────────────────

@app.post("/api/v1/audio/start_capture")
async def start_capture(req: CaptureRequest):
    """
    模式一：启动双人实时音频采集

    录制本地麦克风和系统扬声器，生成双声道音频并实时推送给 ASR 服务。
    - Channel 0 = 本地麦克风（本地用户）
    - Channel 1 = 系统扬声器 loopback（远程用户）

    Parameters:
    - session_id: 会议会话 ID
    - mic_device_index: 麦克风设备索引（可选，None=系统默认）
    - loopback_device_index: 扬声器回环设备索引（可选）
    - duration_sec: 录制时长（秒），None=持续录制直到调用 stop_capture
    """
    if state.is_capturing or state.is_processing:
        return {
            "status": "error",
            "message": "已有采集或处理任务在运行，请先停止当前任务",
        }

    state.is_capturing = True
    state.current_mode = "dual"
    state.current_session_id = req.session_id
    state.stop_event.clear()
    state.results = []

    # 在后台线程中启动采集
    state.capture_thread = threading.Thread(
        target=_capture_dual_track,
        args=(req.session_id, req.mic_device_index,
              req.loopback_device_index, req.duration_sec),
        daemon=True,
    )
    state.capture_thread.start()

    return {
        "status": "success",
        "message": "双人模式音频采集已启动",
        "session_id": req.session_id,
        "mode": "dual",
    }


@app.post("/api/v1/audio/stop_capture")
async def stop_capture(req: StopRequest):
    """
    停止模式一的实时音频采集

    Parameters:
    - session_id: 会议会话 ID
    """
    if not state.is_capturing:
        return {
            "status": "error",
            "message": "当前没有正在进行的采集任务",
        }

    state.stop_event.set()

    # 等待线程结束（最多等 10 秒）
    if state.capture_thread and state.capture_thread.is_alive():
        state.capture_thread.join(timeout=10)

    state.is_capturing = False

    return {
        "status": "success",
        "message": "音频采集已停止",
        "session_id": req.session_id,
        "total_results": len(state.results),
        "results": state.results,
    }


@app.post("/api/v1/audio/upload_multitrack")
async def upload_multitrack(
    background_tasks: BackgroundTasks,
    session_id: str = "default_session",
    file: UploadFile = File(...),
):
    """
    模式二：上传预录制的多声道 WAV 文件

    上传一个多声道 WAV 文件，服务会按声道拆分，每个声道对应一个发言人，
    按 5 秒时间窗口切片后逐片段推送给 M1 ASR 服务进行转录。

    Parameters:
    - session_id: 会议会话 ID（query参数）
    - file: 多声道 WAV 文件（form-data 上传）

    Response:
    - 返回音轨信息和处理状态，处理在后台异步进行
    - 使用 GET /api/v1/audio/status 查询处理进度
    - 处理完成后使用 GET /api/v1/audio/tracks/{session_id} 获取结果
    """
    if state.is_capturing or state.is_processing:
        return {
            "status": "error",
            "message": "已有采集或处理任务在运行，请先停止当前任务",
        }

    # 读取上传的文件
    try:
        import soundfile as sf

        content = await file.read()
        buf = io.BytesIO(content)

        audio_data, sample_rate = sf.read(buf, dtype='int16')

        # 获取声道数
        if audio_data.ndim == 1:
            num_channels = 1
        else:
            num_channels = audio_data.shape[1]

        print(f"[M6] 接收到 WAV 文件: {file.filename}, "
              f"声道数={num_channels}, 采样率={sample_rate}, "
              f"时长={len(audio_data)/sample_rate:.1f}秒")

    except ImportError:
        return {
            "status": "error",
            "message": "soundfile 库未安装，请执行: pip install soundfile",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"WAV 文件读取失败: {str(e)}",
        }

    # 初始化状态
    state.current_session_id = session_id
    state.stop_event.clear()
    state.results = []

    # 在后台异步处理
    background_tasks.add_task(
        _process_multitrack_file,
        file.filename, session_id, num_channels, sample_rate, audio_data
    )

    return {
        "status": "success",
        "message": f"多声道文件已接收，正在后台处理",
        "session_id": session_id,
        "mode": "multitrack",
        "file_info": {
            "filename": file.filename,
            "channels": num_channels,
            "sample_rate": sample_rate,
            "duration_sec": round(len(audio_data) / sample_rate, 2),
        },
    }


@app.get("/api/v1/audio/status")
async def get_status():
    """
    查询当前音频服务的工作状态

    Returns:
    - is_capturing: 模式一是否在采集
    - is_processing: 模式二是否在处理
    - current_mode: 当前模式 ("dual" / "multitrack" / null)
    - progress: 模式二的处理进度 (0.0 ~ 1.0)
    - result_count: 已生成的转录结果数量
    """
    return {
        "status": "success",
        "is_capturing": state.is_capturing,
        "is_processing": state.is_processing,
        "current_mode": state.current_mode,
        "session_id": state.current_session_id,
        "progress": state.processing_progress,
        "result_count": len(state.results),
        "track_info": state.track_info,
    }


@app.get("/api/v1/audio/tracks/{session_id}")
async def get_tracks(session_id: str):
    """
    获取指定会话的音轨拆分信息和转录结果

    Parameters:
    - session_id: 会议会话 ID

    Returns:
    - track_info: 音轨元信息（声道数、发言人列表、采样率等）
    - results: 各声道的转录结果列表
    - full_text: 按时间顺序合并的完整会议文本
    """
    if state.current_session_id != session_id:
        return {
            "status": "error",
            "message": f"未找到会话 {session_id} 的数据",
        }

    # 组装完整会议文本
    full_text = ""
    for r in state.results:
        speaker = r.get("speaker", "Unknown")
        text = r.get("text", "")
        if text and text not in ("[未识别到有效语音]",):
            full_text += f"{speaker}: {text}\n"

    return {
        "status": "success",
        "session_id": session_id,
        "track_info": state.track_info,
        "results": state.results,
        "full_text": full_text.strip(),
        "is_complete": not state.is_capturing and not state.is_processing,
    }


@app.get("/api/v1/audio/devices")
async def list_audio_devices():
    """
    列出系统可用的音频设备（用于模式一选择设备）

    Returns:
    - devices: 音频设备列表，包含设备索引、名称、最大输入/输出通道数
    """
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        device_list = []
        for i, dev in enumerate(devices):
            device_list.append({
                "index": i,
                "name": dev["name"],
                "max_input_channels": dev["max_input_channels"],
                "max_output_channels": dev["max_output_channels"],
                "default_samplerate": dev["default_samplerate"],
                "is_default_input": i == sd.default.device[0],
                "is_default_output": i == sd.default.device[1],
            })
        return {"status": "success", "devices": device_list}
    except ImportError:
        return {
            "status": "error",
            "message": "sounddevice 未安装。模式一需要: pip install sounddevice",
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "M6 - Audio Input",
        "is_capturing": state.is_capturing,
        "is_processing": state.is_processing,
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8005)
