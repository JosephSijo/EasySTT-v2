import threading
import uvicorn
import uuid
import logging
from typing import Dict, Any, List
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel

class StatusResponse(BaseModel):
    status: str
    is_recording: bool
    version: str = "2.0.0-agentic"

class TranscriptionEvent(BaseModel):
    id: str
    text: str
    confidence: float
    mode: str

class A2ABridge:
    """
    Agent-to-Agent Bridge for EasySTT.
    Exposes a REST API for other local agents to control and consume transcription.
    """
    
    def __init__(self, engine, config):
        self.engine = engine
        self.config = config
        self.port = config.get("a2a_port", 8090)
        self.enabled = config.get("a2a_enabled", True) # Default to enabled for Pro
        
        self.app = FastAPI(title="EasySTT A2A API")
        self._setup_routes()
        
        self._server_thread = None
        self.logger = logging.getLogger("A2ABridge")
        
        # In-memory history for agent queries
        self.history: List[TranscriptionEvent] = []

    def _setup_routes(self):
        @self.app.get("/", response_model=StatusResponse)
        async def get_status():
            return {
                "status": "online",
                "is_recording": self.engine.is_recording
            }

        @self.app.post("/recording/start")
        async def start_recording(background_tasks: BackgroundTasks):
            if not self.engine.is_recording:
                background_tasks.add_task(self.engine.start_recording)
                return {"message": "Recording started"}
            return {"message": "Already recording"}

        @self.app.post("/recording/stop")
        async def stop_recording(background_tasks: BackgroundTasks):
            if self.engine.is_recording:
                background_tasks.add_task(self.engine.stop_recording)
                return {"message": "Recording stopped"}
            return {"message": "Not recording"}

        @self.app.get("/transcriptions/latest")
        async def get_latest():
            if not self.history:
                return {"message": "No transcriptions yet"}
            return self.history[-1]

        @self.app.get("/transcriptions/history")
        async def get_history(limit: int = 10):
            return self.history[-limit:]

    def on_transcription_event(self, data: Dict[str, Any]):
        """Callback from STTEngine when a final result is ready."""
        if data.get("type") == "final":
            event = TranscriptionEvent(
                id=str(uuid.uuid4()),
                text=data.get("text", ""),
                confidence=data.get("confidence", 0.0),
                mode=data.get("mode", "local")
            )
            self.history.append(event)
            if len(self.history) > 100:
                self.history.pop(0)
            
            self.logger.info(f"[A2A] Cached event for agent discovery: {event.id}")

    def start(self):
        """Starts the A2A server in a background thread."""
        if not self.enabled:
            return

        if self._server_thread and self._server_thread.is_alive():
            return

        self._server_thread = threading.Thread(
            target=lambda: uvicorn.run(self.app, host="127.0.0.1", port=self.port, log_level="error"),
            daemon=True
        )
        self._server_thread.start()
        self.logger.info(f"[A2A] Bridge active on http://127.0.0.1:{self.port}")
