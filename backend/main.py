from fastapi import FastAPI
from pydantic import BaseModel
from agent_graph import agent

app = FastAPI()

class ChatRequest(BaseModel):
    messages: str

@app.post("/chat")
async def run_chat(req: ChatRequest):
    # Provide input to graph and invoke
    input_data = {"question": req.messages}
    result = agent.invoke(input_data, config = {"configurable": {"thread_id": "1"}})
    return {"output": result}