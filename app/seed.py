"""
بيانات تجريبية لمشروع dalili
بما أن الأساتذة يُدخلون التخصص والمادة عند التوليد،
يتم إنشاء رموز دخول أولية فقط.
"""
import secrets
from .database import SessionLocal
from .models import Passcode, init_db


def seed():
    """إضافة رموز دخول تجريبية"""
    init_db()
    db = SessionLocal()

    # مسح الرموز القديمة (إذا تكرر التشغيل)
    db.query(Passcode).delete()
    db.commit()

    # إنشاء 3 رموز دخول أولية
    for _ in range(3):
        db.add(Passcode(code=secrets.token_urlsafe(6)))

    db.commit()
    db.close()
    print("✅ 3 رموز دخول تجريبية تم إنشاؤها!")


if __name__ == "__main__":
    seed()
