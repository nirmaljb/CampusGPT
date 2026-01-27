from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from enum import Enum


def get_utc_now():
    return datetime.now(timezone.utc)

class UserRole(str, Enum):
    USER = "user"
    SYSTEM = "system"

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str
    email: str = Field(unique=True, index=True)
    created_at: datetime = Field(default_factory=get_utc_now)

    conversations: List["Conversation"] = Relationship(back_populates="user")


class Conversation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    created_at: datetime = Field(default_factory=get_utc_now)
    updated_at: datetime = Field(default_factory=get_utc_now)
    user: Optional[User] = Relationship(back_populates="conversations")
    messages: List["Message"] = Relationship(back_populates="conversation")

class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    conversation_id: Optional[int] = Field(default=None, foreign_key="conversation.id")
    created_at: datetime = Field(default_factory=get_utc_now)
    content: str
    role: UserRole = Field(default=UserRole.SYSTEM)
    conversation: Optional[Conversation] = Relationship(back_populates="messages")