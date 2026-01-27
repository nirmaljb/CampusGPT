from fastapi import APIRouter
from chat.schema import ChatRequest

router = APIRouter()

@router.post('/')
def chat(request: ChatRequest):
    return request



