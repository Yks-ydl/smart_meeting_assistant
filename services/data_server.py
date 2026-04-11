"""
数据服务：提供 VCSum 数据集的访问接口
端口：8006
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "Code"))

from data_loader import load_vcsum_data, format_transcript, get_participants

app = FastAPI(title="M7 - VCSum Data Service", version="1.0.0")


class DataServiceState:
    def __init__(self):
        self.short_data_path = Path(
            r"f:\课程\Semester B\CS6493 Natural Language Processing\NLP Project\VCSum\vcsum_data\short_train.txt"
        )
        self.long_data_path = Path(
            r"f:\课程\Semester B\CS6493 Natural Language Processing\NLP Project\VCSum\vcsum_data\long_train.txt"
        )
        self.test_meetings: List[Dict] = []
        self.overall_summaries: Dict[str, str] = {}
        self.current_index = 0
        self.is_loaded = False

    def load_data(self):
        if self.is_loaded:
            return
        try:
            self.test_meetings = load_vcsum_data(str(self.short_data_path))
            long_data = load_vcsum_data(str(self.long_data_path))
            for item in long_data:
                self.overall_summaries[item.get("id", "")] = item.get("summary", "")
            self.is_loaded = True
            print(f"[DataService] ✅ 加载 {len(self.test_meetings)} 条分段数据")
            print(f"[DataService] ✅ 加载 {len(self.overall_summaries)} 条整体摘要")
        except Exception as e:
            print(f"[DataService] ❌ 加载数据失败: {e}")

    def get_current_meeting(self) -> Optional[Dict]:
        if not self.test_meetings:
            return None
        if self.current_index >= len(self.test_meetings):
            self.current_index = 0
        return self.test_meetings[self.current_index]

    def advance_index(self):
        self.current_index += 1
        if self.current_index >= len(self.test_meetings):
            self.current_index = 0

    def parse_to_subtitles(self, meeting_data: Dict) -> List[Dict]:
        subtitles = []
        context = meeting_data.get("context", [])
        speakers = meeting_data.get("speaker", [])

        for para_idx, (paragraph, speaker_id) in enumerate(zip(context, speakers)):
            for sentence_idx, sentence in enumerate(paragraph):
                if sentence.strip():
                    subtitles.append(
                        {
                            "id": f"subtitle-{para_idx}-{sentence_idx}",
                            "speaker": f"Speaker {speaker_id}",
                            "text": sentence,
                            "timestamp": datetime.now().isoformat(),
                            "language": "zh-CN",
                            "meeting_id": meeting_data.get("id", ""),
                            "agenda": meeting_data.get("agenda", ""),
                        }
                    )
        return subtitles


state = DataServiceState()


class LoadRequest(BaseModel):
    short_data_path: Optional[str] = None
    long_data_path: Optional[str] = None


@app.on_event("startup")
async def startup():
    state.load_data()


@app.get("/api/v1/data/status")
async def get_status():
    return {
        "status": "ok",
        "is_loaded": state.is_loaded,
        "total_meetings": len(state.test_meetings),
        "current_index": state.current_index,
    }


@app.post("/api/v1/data/load")
async def load_data(req: LoadRequest = LoadRequest()):
    if req.short_data_path:
        state.short_data_path = Path(req.short_data_path)
    if req.long_data_path:
        state.long_data_path = Path(req.long_data_path)
    state.is_loaded = False
    state.load_data()
    return {"status": "ok", "total_meetings": len(state.test_meetings)}


@app.get("/api/v1/data/current")
async def get_current_meeting():
    meeting = state.get_current_meeting()
    if not meeting:
        raise HTTPException(status_code=404, detail="无可用会议数据")
    return {
        "meeting_id": meeting.get("id"),
        "agenda": meeting.get("agenda", ""),
        "subtitle_count": len(state.parse_to_subtitles(meeting)),
        "speakers": list(set(meeting.get("speaker", []))),
    }


@app.get("/api/v1/data/stream")
async def stream_subtitles():
    meeting = state.get_current_meeting()
    if not meeting:
        raise HTTPException(status_code=404, detail="无可用会议数据")

    subtitles = state.parse_to_subtitles(meeting)

    async def generate():
        for i, sub in enumerate(subtitles):
            sub["timestamp"] = datetime.now().isoformat()
            message = json.dumps({"type": "subtitle", "data": sub}, ensure_ascii=False)
            yield f"data: {message}\n\n"
            await asyncio.sleep(2.5)
        yield f"data: {json.dumps({'type': 'stream_complete', 'total': len(subtitles)})}\n\n"
        state.advance_index()

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/api/v1/data/summary/{meeting_id}")
async def get_summary(meeting_id: str):
    segment_id = meeting_id
    full_meeting_id = meeting_id.split("_")[0] if "_" in meeting_id else meeting_id

    for m in state.test_meetings:
        if m.get("id") == segment_id:
            segment_summary = m.get("segment_summary", "")
            overall_summary = state.overall_summaries.get(full_meeting_id, "")
            participants = get_participants(m)
            return {
                "segment_id": segment_id,
                "meeting_id": full_meeting_id,
                "agenda": m.get("agenda", ""),
                "segment_summary": segment_summary,
                "overall_summary": overall_summary,
                "participants": participants,
                "transcript": format_transcript(m),
            }

    raise HTTPException(status_code=404, detail="会议不存在")


@app.get("/api/v1/data/list")
async def list_meetings():
    return {
        "total": len(state.test_meetings),
        "meetings": [
            {
                "id": m.get("id"),
                "agenda": (
                    m.get("agenda", "")[:50] + "..."
                    if len(m.get("agenda", "")) > 50
                    else m.get("agenda", "")
                ),
            }
            for m in state.test_meetings[:20]
        ],
    }


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8006)
