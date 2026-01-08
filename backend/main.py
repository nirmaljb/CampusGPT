import json
from uuid import uuid4
from typing import Optional, List, Dict, Any

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agent_graph import agent

app = FastAPI()

class ChatRequest(BaseModel):
    messages: str
    thread_id: Optional[str] = None


def format_sse(event: str, data: Dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def extract_sources(documents: List[Any]) -> List[Dict[str, Any]]:
    sources = []
    for idx, doc in enumerate(documents):
        meta = getattr(doc, "metadata", {}) or {}
        label = meta.get("section") or meta.get("faculty_name") or f"source-{idx+1}"
        sources.append({"id": idx + 1, "label": label, "metadata": meta})
    return sources

@app.post("/chat")
async def run_chat(req: ChatRequest):
    # Provide input to graph and invoke
    input_data = {"question": req.messages}
    result = agent.invoke(input_data, config = {"configurable": {"thread_id": "1"}})
    return {"output": result}


@app.post("/chat/stream")
async def run_chat_stream(req: ChatRequest):
    thread_id = req.thread_id or str(uuid4())
    input_data = {"question": req.messages}
    config = {"configurable": {"thread_id": thread_id}}

    async def event_generator():
        final_generation = ""
        final_sources: List[Dict[str, Any]] = []
        try:
            for output in agent.stream(input_data, config=config):
                for _, value in output.items():
                    documents = value.get("documents")
                    if documents:
                        final_sources = extract_sources(documents)

                    if "generation" in value:
                        final_generation = value["generation"]
                        yield format_sse("token", {"text": final_generation})

            yield format_sse(
                "done",
                {"text": final_generation, "sources": final_sources, "thread_id": thread_id},
            )
        except Exception as e:
            yield format_sse("error", {"error": str(e)})

    return StreamingResponse(event_generator(), media_type="text/event-stream")