import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import jwt
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from pwdlib import PasswordHash
from sqlalchemy import create_engine, String, Integer, Float, Date, DateTime, ForeignKey, Text, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session, sessionmaker

BASE_DIR = Path(__file__).resolve().parent
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./harikashi.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
password_hash = PasswordHash.recommended()
SECRET = os.getenv("HARIKASHI_SECRET_KEY")
if not SECRET:
    SECRET = "development-only-secret-change-in-production"
app = FastAPI(title="HARIKASHI API", docs_url="/api/docs")
security = HTTPBearer(auto_error=False)

class Base(DeclarativeBase): pass
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
class Achievement(Base):
    __tablename__ = "achievements"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    date: Mapped[date] = mapped_column(Date)
    hours: Mapped[float] = mapped_column(Float)
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
class Note(Base):
    __tablename__ = "notes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    subject: Mapped[str] = mapped_column(String(80))
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(engine)
def get_db():
    with SessionLocal() as s:
        yield s
class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=40, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(pattern=r"^\d{6}$")
class AchievementIn(BaseModel):
    date: date
    hours: float = Field(ge=0, le=24)
    text: str = Field(min_length=1, max_length=5000)
class NoteIn(BaseModel):
    subject: str = Field(min_length=1, max_length=80)
    text: str = Field(min_length=1, max_length=5000)

def make_token(user):
    return jwt.encode({"sub": str(user.id), "exp": datetime.now(timezone.utc) + timedelta(days=7)}, SECRET, algorithm="HS256")
def get_user(creds: Optional[HTTPAuthorizationCredentials] = Depends(security), s: Session = Depends(get_db)):
    if not creds:
        raise HTTPException(401, "يرجى تسجيل الدخول.")
    try:
        uid = int(jwt.decode(creds.credentials, SECRET, algorithms=["HS256"])["sub"])
    except Exception:
        raise HTTPException(401, "انتهت الجلسة؛ سجّل الدخول مجددًا.")
    user = s.get(User, uid)
    if not user:
        raise HTTPException(401, "الحساب غير موجود.")
    return user

@app.get("/")
def home():
    return FileResponse(BASE_DIR / "index.html")
@app.get("/manifest.webmanifest")
def manifest():
    return FileResponse(BASE_DIR / "manifest.webmanifest", media_type="application/manifest+json")
@app.get("/sw.js")
def service_worker():
    return FileResponse(BASE_DIR / "sw.js", media_type="application/javascript")
@app.get("/icon.svg")
def icon():
    return FileResponse(BASE_DIR / "icon.svg", media_type="image/svg+xml")
@app.get("/health")
def health():
    return {"status": "ok"}
@app.post("/api/auth/register")
def register(body: Credentials, s: Session = Depends(get_db)):
    username = body.username.lower()
    if s.scalar(select(User).where(User.username == username)):
        raise HTTPException(409, "اسم المستخدم مستخدم بالفعل.")
    u = User(username=username, password_hash=password_hash.hash(body.password))
    s.add(u); s.commit(); s.refresh(u)
    return {"access_token": make_token(u), "token_type": "bearer"}
@app.post("/api/auth/login")
def login(body: Credentials, s: Session = Depends(get_db)):
    u = s.scalar(select(User).where(User.username == body.username.lower()))
    if not u or not password_hash.verify(body.password, u.password_hash):
        raise HTTPException(401, "اسم المستخدم أو رمز الدخول غير صحيح.")
    return {"access_token": make_token(u), "token_type": "bearer"}
@app.get("/api/data")
def data(u: User = Depends(get_user), s: Session = Depends(get_db)):
    aa = s.scalars(select(Achievement).where(Achievement.user_id == u.id).order_by(Achievement.date)).all()
    nn = s.scalars(select(Note).where(Note.user_id == u.id).order_by(Note.created_at)).all()
    return {"username": u.username,
            "achievements": [{"id": x.id, "date": x.date.isoformat(), "hours": x.hours, "text": x.text} for x in aa],
            "notes": [{"id": x.id, "subject": x.subject, "text": x.text, "created_at": x.created_at.isoformat()} for x in nn]}
@app.post("/api/achievements")
def add_achievement(body: AchievementIn, u: User = Depends(get_user), s: Session = Depends(get_db)):
    x = Achievement(user_id=u.id, date=body.date, hours=body.hours, text=body.text.strip())
    s.add(x); s.commit(); s.refresh(x)
    return {"id": x.id, "ok": True}
@app.delete("/api/achievements/{item_id}")
def delete_achievement(item_id: int, u: User = Depends(get_user), s: Session = Depends(get_db)):
    x = s.get(Achievement, item_id)
    if not x or x.user_id != u.id: raise HTTPException(404, "السجل غير موجود.")
    s.delete(x); s.commit()
    return {"ok": True}
@app.post("/api/notes")
def add_note(body: NoteIn, u: User = Depends(get_user), s: Session = Depends(get_db)):
    x = Note(user_id=u.id, subject=body.subject, text=body.text.strip())
    s.add(x); s.commit(); s.refresh(x)
    return {"id": x.id, "ok": True}
@app.delete("/api/notes/{item_id}")
def delete_note(item_id: int, u: User = Depends(get_user), s: Session = Depends(get_db)):
    x = s.get(Note, item_id)
    if not x or x.user_id != u.id: raise HTTPException(404, "الملاحظة غير موجودة.")
    s.delete(x); s.commit()
    return {"ok": True}
