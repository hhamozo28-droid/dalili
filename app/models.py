"""
نماذج البيانات (ORM) لمشروع dalili
الهيكل: تخصص → مادة → (أدلة + دروس)
رمز الدخول: Passcode (مرة واحدة)
"""
from datetime import datetime
from .database import Base, engine, SessionLocal
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship


class Specialization(Base):
    """تخصص في التكوين المهني (مثل: الإلكتروني، الميكانيكي، البناء...)"""
    __tablename__ = "specializations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(120), unique=True, nullable=False)
    description = Column(Text, default="")
    icon = Column(String(20), default="📘")
    order = Column(Integer, default=0)

    subjects = relationship("Subject", back_populates="specialization", cascade="all, delete-orphan")


class Subject(Base):
    """مادة ضمن تخصص (مثل: الرياضيات، الإلكترونيك...)"""
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    specialization_id = Column(Integer, ForeignKey("specializations.id"), nullable=False)
    name = Column(String(100), nullable=False)
    slug = Column(String(120), unique=True, nullable=False)
    description = Column(Text, default="")
    icon = Column(String(20), default="📚")
    order = Column(Integer, default=0)

    specialization = relationship("Specialization", back_populates="subjects")
    guides = relationship("Guide", back_populates="subject", cascade="all, delete-orphan")
    lessons = relationship("Lesson", back_populates="subject", cascade="all, delete-orphan")


class Guide(Base):
    """دليل المتربص — قسم 1"""
    __tablename__ = "guides"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text, default="")
    order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    subject = relationship("Subject", back_populates="guides")


class Lesson(Base):
    """درس التكوين المهني — قسم 2"""
    __tablename__ = "lessons"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text, default="")
    order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    subject = relationship("Subject", back_populates="lessons")


class Passcode(Base):
    """رمز دخول — يُستخدم مرة واحدة فقط"""
    __tablename__ = "passcodes"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False)
    used = Column(Boolean, default=False)
    used_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    """إنشاء الجداول في قاعدة البيانات"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """اتصال بالـ Database لكل request"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
