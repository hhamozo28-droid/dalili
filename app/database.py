"""
اتصال بقاعدة البيانات
يدعم PostgreSQL (لـ Vercel) و SQLite (للتطوير المحلي)
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "")

if DATABASE_URL:
    # PostgreSQL — للنشر على Vercel (Neon, Supabase, ...)
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=5, max_overflow=10)
else:
    # SQLite — للتطوير المحلي
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DB_PATH = os.path.join(BASE_DIR, "data", "dalili.db")
    engine = create_engine(
        f"sqlite:///{DB_PATH}",
        connect_args={"check_same_thread": False},
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def run_migrations():
    """إضافة columns جديدة للجداول الموجودة"""
    from sqlalchemy import inspect, text
    inspector = inspect(engine)

    # إضافة is_master لجدول passcodes
    try:
        cols = [c["name"] for c in inspector.get_columns("passcodes")]
        if "is_master" not in cols:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE passcodes ADD COLUMN is_master BOOLEAN DEFAULT FALSE"))
                conn.commit()
    except Exception:
        pass
