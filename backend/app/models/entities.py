import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base


def now() -> datetime:
    return datetime.now(timezone.utc)


class ManualStatus(str, enum.Enum):
    uploaded="uploaded"; extracting="extracting"; chunking="chunking"; embedding="embedding"; indexed="indexed"; failed="failed"


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(160))
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)



class Manual(Base):
    __tablename__ = "manuals"
    __table_args__ = (UniqueConstraint("uploaded_by_user_id", "file_hash", name="uq_user_manual_hash"),)
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    uploaded_by_user_id: Mapped[str|None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    filename: Mapped[str] = mapped_column(String(255)); equipment_name: Mapped[str] = mapped_column(String(255), default="")
    manufacturer: Mapped[str] = mapped_column(String(255), default=""); model_number: Mapped[str] = mapped_column(String(120), default="")
    version: Mapped[str] = mapped_column(String(80), default=""); file_path: Mapped[str] = mapped_column(String(500)); file_hash: Mapped[str] = mapped_column(String(64), index=True)
    page_count: Mapped[int] = mapped_column(Integer, default=0); chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(30), default=ManualStatus.uploaded.value); error_message: Mapped[str|None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now); updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    logs = relationship("IngestionLog", cascade="all, delete-orphan")


class Conversation(Base):
    __tablename__="conversations"
    id: Mapped[str]=mapped_column(String,primary_key=True,default=lambda:str(uuid.uuid4())); title: Mapped[str]=mapped_column(String(255),default="New conversation")
    user_id: Mapped[str|None]=mapped_column(ForeignKey("users.id",ondelete="CASCADE"),nullable=True,index=True)
    selected_manual_id: Mapped[str|None]=mapped_column(ForeignKey("manuals.id",ondelete="SET NULL"),nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now); updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,onupdate=now)
    messages=relationship("Message",cascade="all, delete-orphan",order_by="Message.created_at")
    queries=relationship("Query",cascade="all, delete-orphan")


class Message(Base):
    __tablename__="messages"
    id: Mapped[str]=mapped_column(String,primary_key=True,default=lambda:str(uuid.uuid4())); conversation_id: Mapped[str]=mapped_column(ForeignKey("conversations.id",ondelete="CASCADE"))
    role: Mapped[str]=mapped_column(String(20)); content: Mapped[str]=mapped_column(Text); confidence_score: Mapped[float|None]=mapped_column(Float,nullable=True); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
    citations=relationship("Citation",cascade="all, delete-orphan")


class Query(Base):
    __tablename__="queries"
    id: Mapped[str]=mapped_column(String,primary_key=True,default=lambda:str(uuid.uuid4())); conversation_id: Mapped[str]=mapped_column(ForeignKey("conversations.id",ondelete="CASCADE"))
    original_query: Mapped[str]=mapped_column(Text); rewritten_query: Mapped[str]=mapped_column(Text); detected_error_code: Mapped[str|None]=mapped_column(String(50),nullable=True); detected_equipment: Mapped[str|None]=mapped_column(String(255),nullable=True)
    retrieval_attempts: Mapped[int]=mapped_column(Integer,default=1); response_time_ms: Mapped[int]=mapped_column(Integer,default=0); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)


class Citation(Base):
    __tablename__="citations"
    id: Mapped[str]=mapped_column(String,primary_key=True,default=lambda:str(uuid.uuid4())); message_id: Mapped[str]=mapped_column(ForeignKey("messages.id",ondelete="CASCADE")); manual_id: Mapped[str]=mapped_column(ForeignKey("manuals.id",ondelete="CASCADE"))
    chunk_id: Mapped[str]=mapped_column(String); page_number: Mapped[int]=mapped_column(Integer); section_title: Mapped[str]=mapped_column(String(255)); excerpt: Mapped[str]=mapped_column(Text); retrieval_score: Mapped[float]=mapped_column(Float); reranker_score: Mapped[float]=mapped_column(Float,default=0)


class IngestionLog(Base):
    __tablename__="ingestion_logs"
    id: Mapped[str]=mapped_column(String,primary_key=True,default=lambda:str(uuid.uuid4())); manual_id: Mapped[str]=mapped_column(ForeignKey("manuals.id",ondelete="CASCADE")); stage: Mapped[str]=mapped_column(String(50)); status: Mapped[str]=mapped_column(String(30)); message: Mapped[str]=mapped_column(Text); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
