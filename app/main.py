"""
تطبيق dalili — تطبيق تعليمي للأساتذة (التكوين المهني)
الأساتذة يختارون: دليل أو درس، ويدخلون التخصص + المادة فقط،
والذكاء الاصطناعي يولد المحتوى كاملاً.
الدخول يتطلب رمز دخول مرة واحدة.
تقنية: FastAPI
"""
import secrets
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
import os

from .database import SessionLocal
from .models import Specialization, Subject, Guide, Lesson, Passcode, init_db, get_db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

app = FastAPI(title="dalili — التكوين المهني")
app.add_middleware(SessionMiddleware, secret_key=os.environ.get("SECRET_KEY", "dalili-default-secret"))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")


@app.on_event("startup")
def startup():
    init_db()
    _seed_passcodes()


def _seed_passcodes():
    """إنشاء رموز دخول أولية عند التشغيل"""
    db = SessionLocal()
    if db.query(Passcode).count() == 0:
        # إذا كان هناك INITIAL_PASSCODE مضبوط، استخدمه
        initial = os.environ.get("INITIAL_PASSCODE", "")
        if initial:
            db.add(Passcode(code=initial.strip()))
            print(f"🔑 رمز الدخول الأولي: {initial.strip()}")
        else:
            for _ in range(3):
                db.add(Passcode(code=secrets.token_urlsafe(6)))
        db.commit()
        print("🔑 رموز دخول أولية تم إنشاؤها — اطلبها من Vercel logs أو من صفحة /passcodes")
    db.close()


# ===== التحقق من الدخول =====
def require_login(request: Request):
    if not request.session.get("logged_in"):
        return None
    return request.session


def is_logged_in(request: Request):
    return bool(request.session.get("logged_in"))


# ===== الصفحات =====

@app.get("/", response_class="HTML")
def home(request: Request):
    if is_logged_in(request):
        return RedirectResponse("/dashboard", status_code=302)
    return RedirectResponse("/login", status_code=302)


@app.get("/login", response_class="HTML")
def login_form(request: Request):
    if is_logged_in(request):
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse(request, "login.html", {"active": "login"})


@app.post("/login", response_class="HTML")
def login(request: Request, code: str = Form(...), db: Session = Depends(get_db)):
    """تسجيل الدخول برمز دخول مرة واحدة"""
    pc = db.query(Passcode).filter(Passcode.code == code.strip(), Passcode.used == False).first()
    if pc:
        pc.used = True
        pc.used_at = datetime.utcnow()
        db.commit()
        request.session["logged_in"] = True
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse(request, "login.html", {
        "active": "login", "error": "رمز الدخول غير صحيح أو تم استخدامه بالفعل"
    })


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=302)


# ===== لوحة الأساتذة =====

@app.get("/dashboard", response_class="HTML")
def dashboard(request: Request, db: Session = Depends(get_db)):
    """لوحة الأساتذة — الرئيسية"""
    if not is_logged_in(request):
        return RedirectResponse("/login", status_code=302)
    guides = db.query(Guide).order_by(Guide.order.desc(), Guide.created_at.desc()).all()
    lessons = db.query(Lesson).order_by(Lesson.order.desc(), Lesson.created_at.desc()).all()
    return templates.TemplateResponse(request, "dashboard.html", {
        "db": db, "guides": guides, "lessons": lessons, "active": "dashboard",
    })


@app.post("/generate", response_class="HTML")
def generate(request: Request,
             kind: str = Form(...),           # "guide" أو "lesson"
             specialization: str = Form(...),
             subject_name: str = Form(...),
             db: Session = Depends(get_db)):
    """
    توليد دليل أو درس.
    الأستاذ يختار النوع ويدخل التخصص + المادة فقط.
    الذكاء الاصطناعي يولد المحتوى كاملاً.
    """
    if not is_logged_in(request):
        return RedirectResponse("/login", status_code=302)

    from .ai_generator import generate_guide, generate_lesson

    spec_name = specialization.strip()
    subj_name = subject_name.strip()
    if not spec_name or not subj_name:
        return RedirectResponse("/dashboard?err=missing", status_code=302)

    # العثور على التخصص أو إنشاء جديد
    slug = spec_name.lower().replace(" ", "-")
    spec = db.query(Specialization).filter(Specialization.slug == slug).first()
    if not spec:
        spec = Specialization(name=spec_name, slug=slug, description="", icon="📘",
                              order=len(db.query(Specialization).all()))
        db.add(spec)
        db.flush()

    # العثور على المادة أو إنشاء جديد
    subj_slug = subj_name.lower().replace(" ", "-")
    subject = db.query(Subject).filter(Subject.slug == subj_slug).first()
    if not subject:
        subject = Subject(specialization_id=spec.id, name=subj_name, slug=subj_slug,
                         description="", icon="📚", order=0)
        db.add(subject)
        db.flush()

    # توليد المحتوى حسب الاختيار
    if kind == "guide":
        title, content = generate_guide(spec.name, subject.name)
        guide = Guide(subject_id=subject.id, title=title, content=content,
                     order=len(db.query(Guide).filter(Guide.subject_id == subject.id).all()))
        db.add(guide)
    else:
        title, content = generate_lesson(spec.name, subject.name)
        lesson = Lesson(subject_id=subject.id, title=title, content=content,
                       order=len(db.query(Lesson).filter(Lesson.subject_id == subject.id).all()))
        db.add(lesson)
    db.commit()
    return RedirectResponse(f"/dashboard?ok=generated&type={kind}&title={title}", status_code=302)


@app.post("/passcode/new")
def new_passcode(request: Request, db: Session = Depends(get_db)):
    """إنشاء رمز دخول جديد (للأساتذة المسجلين)"""
    if not is_logged_in(request):
        return RedirectResponse("/login", status_code=302)
    code = secrets.token_urlsafe(6)
    db.add(Passcode(code=code))
    db.commit()
    return RedirectResponse("/dashboard?newcode=" + code, status_code=302)


@app.get("/passcodes", response_class="HTML")
def list_passcodes(request: Request, db: Session = Depends(get_db)):
    """عرض رموز الدخول غير المستخدمة"""
    if not is_logged_in(request):
        return RedirectResponse("/login", status_code=302)
    codes = db.query(Passcode).filter(Passcode.used == False).order_by(Passcode.created_at.desc()).all()
    return templates.TemplateResponse(request, "passcodes.html", {
        "db": db, "codes": codes, "active": "dashboard",
    })


# ===== عرض المحتوى =====

@app.get("/view/guide/{id}", response_class="HTML")
def view_guide(request: Request, id: int, db: Session = Depends(get_db)):
    if not is_logged_in(request):
        return RedirectResponse("/login", status_code=302)
    guide = db.query(Guide).filter(Guide.id == id).first()
    if not guide:
        return templates.TemplateResponse(request, "error.html", {"message": "الدليل غير موجود"}, status_code=404)
    return templates.TemplateResponse(request, "view_guide.html", {
        "db": db, "guide": guide, "subject": guide.subject, "spec": guide.subject.specialization,
        "active": "dashboard",
    })


@app.get("/view/lesson/{id}", response_class="HTML")
def view_lesson(request: Request, id: int, db: Session = Depends(get_db)):
    if not is_logged_in(request):
        return RedirectResponse("/login", status_code=302)
    lesson = db.query(Lesson).filter(Lesson.id == id).first()
    if not lesson:
        return templates.TemplateResponse(request, "error.html", {"message": "الدرس غير موجود"}, status_code=404)
    return templates.TemplateResponse(request, "view_lesson.html", {
        "db": db, "lesson": lesson, "subject": lesson.subject, "spec": lesson.subject.specialization,
        "active": "dashboard",
    })


@app.get("/api/specializations")
def api_specializations(db: Session = Depends(get_db)):
    specs = db.query(Specialization).order_by(Specialization.order).all()
    return [{"id": s.id, "name": s.name, "slug": s.slug, "description": s.description} for s in specs]


# ===== تعديل المحتوى =====

@app.get("/edit/guide/{id}", response_class="HTML")
def edit_guide_form(request: Request, id: int, db: Session = Depends(get_db)):
    if not is_logged_in(request):
        return RedirectResponse("/login", status_code=302)
    guide = db.query(Guide).filter(Guide.id == id).first()
    if not guide:
        return templates.TemplateResponse(request, "error.html", {"message": "الدليل غير موجود"}, status_code=404)
    return templates.TemplateResponse(request, "edit_content.html", {
        "db": db, "kind": "guide", "item": guide,
        "subject": guide.subject, "spec": guide.subject.specialization, "active": "dashboard",
    })


@app.post("/edit/guide/{id}", response_class="HTML")
def edit_guide(request: Request, id: int, db: Session = Depends(get_db),
               title: str = Form(...), content: str = Form("")):
    if not is_logged_in(request):
        return RedirectResponse("/login", status_code=302)
    guide = db.query(Guide).filter(Guide.id == id).first()
    if not guide:
        return templates.TemplateResponse(request, "error.html", {"message": "الدليل غير موجود"}, status_code=404)
    guide.title = title.strip() if title.strip() else guide.title
    guide.content = content
    db.commit()
    return RedirectResponse("/view/guide/" + str(id), status_code=302)


@app.get("/edit/lesson/{id}", response_class="HTML")
def edit_lesson_form(request: Request, id: int, db: Session = Depends(get_db)):
    if not is_logged_in(request):
        return RedirectResponse("/login", status_code=302)
    lesson = db.query(Lesson).filter(Lesson.id == id).first()
    if not lesson:
        return templates.TemplateResponse(request, "error.html", {"message": "الدرس غير موجود"}, status_code=404)
    return templates.TemplateResponse(request, "edit_content.html", {
        "db": db, "kind": "lesson", "item": lesson,
        "subject": lesson.subject, "spec": lesson.subject.specialization, "active": "dashboard",
    })


@app.post("/edit/lesson/{id}", response_class="HTML")
def edit_lesson(request: Request, id: int, db: Session = Depends(get_db),
                title: str = Form(...), content: str = Form("")):
    if not is_logged_in(request):
        return RedirectResponse("/login", status_code=302)
    lesson = db.query(Lesson).filter(Lesson.id == id).first()
    if not lesson:
        return templates.TemplateResponse(request, "error.html", {"message": "الدرس غير موجود"}, status_code=404)
    lesson.title = title.strip() if title.strip() else lesson.title
    lesson.content = content
    db.commit()
    return RedirectResponse("/view/lesson/" + str(id), status_code=302)


# ===== حذف المحتوى =====

@app.post("/delete/guide/{id}")
def delete_guide(request: Request, id: int, db: Session = Depends(get_db)):
    if not is_logged_in(request):
        return RedirectResponse("/login", status_code=302)
    guide = db.query(Guide).filter(Guide.id == id).first()
    if guide:
        db.delete(guide)
        db.commit()
    return RedirectResponse("/dashboard", status_code=302)


@app.post("/delete/lesson/{id}")
def delete_lesson(request: Request, id: int, db: Session = Depends(get_db)):
    if not is_logged_in(request):
        return RedirectResponse("/login", status_code=302)
    lesson = db.query(Lesson).filter(Lesson.id == id).first()
    if lesson:
        db.delete(lesson)
        db.commit()
    return RedirectResponse("/dashboard", status_code=302)


# ===== صفحة حذف =====

@app.get("/delete/{kind}/{id}", response_class="HTML")
def delete_confirm(request: Request, kind: str, id: int, db: Session = Depends(get_db)):
    if not is_logged_in(request):
        return RedirectResponse("/login", status_code=302)
    if kind == "guide":
        item = db.query(Guide).filter(Guide.id == id).first()
        label = "الدليل"
    else:
        item = db.query(Lesson).filter(Lesson.id == id).first()
        label = "الدرس"
    if not item:
        return templates.TemplateResponse(request, "error.html", {"message": f"{label} غير موجود"}, status_code=404)
    return templates.TemplateResponse(request, "delete_confirm.html", {
        "db": db, "kind": kind, "item": item, "label": label, "active": "dashboard",
    })
