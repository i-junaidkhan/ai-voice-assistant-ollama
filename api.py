from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from main import VocalAssistant
import threading

app = FastAPI(title="Voice Assistant API", description="REST API for Ollama voice assistant")

# Initialize assistant once (no microphone for API mode)
assistant = VocalAssistant(mic_device_index=None)  # API mode – no voice I/O
assistant.microphone = None  # disable microphone for API

class QueryRequest(BaseModel):
    text: str
    use_history: bool = True

@app.post("/ask", response_model=dict)
async def ask(query: QueryRequest):
    try:
        reply = assistant.query_mistral(query.text, use_history=query.use_history)
        if reply is None:
            raise HTTPException(status_code=500, detail="Mistral did not respond")
        return {"response": reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "ok", "ollama": assistant.is_ollama_running()}