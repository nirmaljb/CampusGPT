from fastapi import FastAPI
# from backend.auth.router import router as auth_router
from chat.router import router as chat_router
# from backend.conversation.router import router as conversation_router

app = FastAPI()

# app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(chat_router, prefix="/chat", tags=["Chat"])
# app.include_router(conversation_router, prefix="/conversations", tags=["Conversations"])
