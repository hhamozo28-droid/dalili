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

from .database import SessionLocal, run_migrations
from .models import Specialization, Subject, Guide, Lesson, Passcode, ExtractedProgram, init_db, get_db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

app = FastAPI(title="dalili — التكوين المهني")
app.add_middleware(SessionMiddleware, secret_key=os.environ.get("SECRET_KEY", "dalili-default-secret"))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")


@app.on_event("startup")
def startup():
    try:
        init_db()
        run_migrations()
        _seed_passcodes()
    except Exception as e:
        print(f"⚠️ Database warning: {e}")


def _seed_passcodes():
    """إنشاء رموز دخول أولية عند التشغيل"""
    db = SessionLocal()
    initial = os.environ.get("MASTER_PASSCODE", os.environ.get("INITIAL_PASSCODE", ""))
    # التحقق من وجود الرمز الرئيسي
    if initial:
        master = db.query(Passcode).filter(Passcode.code == initial.strip(), Passcode.is_master == True).first()
        if not master:
            db.add(Passcode(code=initial.strip(), is_master=True))
            db.commit()
            print(f"👑 رمز الدخول الرئيسي (دائم): {initial.strip()}")
    else:
        if db.query(Passcode).count() == 0:
            for _ in range(3):
                db.add(Passcode(code=secrets.token_urlsafe(6)))
            db.commit()
            print("🔑 رموز دخول أولية تم إنشاؤها")
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
    """تسجيل الدخول — الرمز الرئيسي دائم، الرموز العادية مرة واحدة"""
    code = code.strip()

    # التحقق من الرمز الرئيسي أولاً (دائم — لا يُستهلك)
    master_code = os.environ.get("MASTER_PASSCODE", os.environ.get("INITIAL_PASSCODE", ""))
    if code == master_code:
        master = db.query(Passcode).filter(Passcode.code == master_code, Passcode.is_master == True).first()
        if master:
            request.session["logged_in"] = True
            request.session["is_master"] = True
            return RedirectResponse("/dashboard", status_code=302)

    # الرمز العادي (مرة واحدة)
    pc = db.query(Passcode).filter(Passcode.code == code, Passcode.used == False, Passcode.is_master == False).first()
    if pc:
        pc.used = True
        pc.used_at = datetime.utcnow()
        db.commit()
        request.session["logged_in"] = True
        request.session["is_master"] = False
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
    """إنشاء رمز دخول جديد — فقط للرمز الرئيسي"""
    if not is_logged_in(request):
        return RedirectResponse("/login", status_code=302)
    if not request.session.get("is_master"):
        return RedirectResponse("/dashboard?err=notmaster", status_code=302)
    code = secrets.token_urlsafe(6)
    db.add(Passcode(code=code, is_master=False))
    db.commit()
    return RedirectResponse("/dashboard?newcode=" + code, status_code=302)


@app.get("/passcodes", response_class="HTML")
def list_passcodes(request: Request, db: Session = Depends(get_db)):
    """عرض رموز الدخول غير المستخدمة — فقط للرمز الرئيسي"""
    if not is_logged_in(request):
        return RedirectResponse("/login", status_code=302)
    if not request.session.get("is_master"):
        return RedirectResponse("/dashboard?err=notmaster", status_code=302)
    codes = db.query(Passcode).filter(Passcode.used == False, Passcode.is_master == False).order_by(Passcode.created_at.desc()).all()
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


# ===== توليد الدليل من ملف البرنامج (3 مراحل) =====

@app.post("/generate/upload-file")
async def generate_upload_file(request: Request, db: Session = Depends(get_db)):
    """رفع ملف برنامج التخصص — المرحلة 1"""
    if not is_logged_in(request):
        return RedirectResponse("/login", status_code=302)

    form = await request.form()
    upload = form.get("file")
    if not upload or not hasattr(upload, "read"):
        return RedirectResponse("/dashboard?err=nofile", status_code=302)

    filename = getattr(upload, "filename", "unknown")
    file_bytes = await upload.read()

    if len(file_bytes) > 10 * 1024 * 1024:  # 10MB max
        return RedirectResponse("/dashboard?err=toolarge", status_code=302)

    # تحليل الملف
    try:
        from .file_parser import parse_uploaded_file
        text = parse_uploaded_file(file_bytes, filename)
    except Exception as e:
        return RedirectResponse(f"/dashboard?err=parse:{str(e)[:50]}", status_code=302)

    # استخراج التخصص والمواد بالذكاء الاصطناعي
    try:
        from .ai_api import extract_specialization_and_subjects
        result = extract_specialization_and_subjects(text)
    except Exception as e:
        # محاولة الاستخراج بالـ regex ك fallback
        result = _extract_with_regex(text)

    if not result or not result.get("subjects"):
        return RedirectResponse("/dashboard?err=noextract", status_code=302)

    # حفظ نتيجة الاستخراج
    import json
    ep = ExtractedProgram(
        specialization=result.get("specialization", "غير معروف"),
        subjects_json=json.dumps(result.get("subjects", []), ensure_ascii=False),
        source_filename=filename,
        used=False,
    )
    db.add(ep)
    db.commit()
    db.refresh(ep)

    # تخزين معرف الاستخراج في الجلسة
    request.session["extracted_id"] = ep.id

    return RedirectResponse(f"/generate/confirm/{ep.id}", status_code=302)


def _extract_with_regex(text: str) -> dict:
    """استخراج التخصص والمواد بالـ regex (بدون ذكاء اصطناعي)"""
    import re
    subjects = []

    # البحث عن مواد MQ و MC
    for match in re.finditer(r'(MQ|MC)\s*[:\-–]\s*(.+)', text, re.IGNORECASE):
        code = match.group(1).upper()
        name = match.group(2).strip().split("\n")[0][:100]
        if name and len(name) > 2:
            subjects.append({
                "code": f"{code}1",
                "name": name,
                "original_name": name,
            })

    # البحث عن التخصص (أنماط شائعة)
    spec_match = re.search(r'([^\n]{0,50}?(?:MME|MMP|MMC|MMG|MMA|MMH|MMI|MMJ|MMK|MML|MMM)[^\n]{0,50})', text, re.IGNORECASE)
    specialization = spec_match.group(1).strip() if spec_match else "غير معروف"

    return {"specialization": specialization, "subjects": subjects}


@app.get("/generate/confirm/{ep_id}", response_class="HTML")
def generate_confirm_form(request: Request, ep_id: int, db: Session = Depends(get_db)):
    """المرحلة 1: صفحة تأكيد التخصص المستخرج"""
    if not is_logged_in(request):
        return RedirectResponse("/login", status_code=302)

    ep = db.query(ExtractedProgram).filter(ExtractedProgram.id == ep_id).first()
    if not ep:
        return templates.TemplateResponse(request, "error.html", {"message": "البرنامج غير موجود"}, status_code=404)

    import json
    subjects = json.loads(ep.subjects_json)

    return templates.TemplateResponse(request, "confirm_specialization.html", {
        "db": db, "ep": ep, "subjects": subjects, "active": "dashboard",
    })


@app.post("/generate/confirm/{ep_id}")
def generate_confirm(request: Request, ep_id: int):
    """المرحلة 1: تأكيد التخصص والتوجه لاختيار المادة"""
    if not is_logged_in(request):
        return RedirectResponse("/login", status_code=302)

    form = request.form if hasattr(request, "form") else {}
    action = form.get("action", "confirm")

    if action == "confirm":
        return RedirectResponse(f"/generate/subject/{ep_id}", status_code=302)
    elif action == "reupload":
        request.session.pop("extracted_id", None)
        return RedirectResponse("/dashboard", status_code=302)

    return RedirectResponse(f"/generate/confirm/{ep_id}", status_code=302)


@app.get("/generate/subject/{ep_id}", response_class="HTML")
def generate_subject_form(request: Request, ep_id: int, db: Session = Depends(get_db)):
    """المرحلة 2: اختيار المادة من القائمة"""
    if not is_logged_in(request):
        return RedirectResponse("/login", status_code=302)

    ep = db.query(ExtractedProgram).filter(ExtractedProgram.id == ep_id).first()
    if not ep:
        return templates.TemplateResponse(request, "error.html", {"message": "البرنامج غير موجود"}, status_code=404)

    import json
    subjects = json.loads(ep.subjects_json)

    return templates.TemplateResponse(request, "select_subject.html", {
        "db": db, "ep": ep, "subjects": subjects, "active": "dashboard",
    })


@app.post("/generate/subject/{ep_id}")
def generate_subject(request: Request, ep_id: int, db: Session = Depends(get_db)):
    """المرحلة 2: توليد الدليل بناءً على المادة المختارة"""
    if not is_logged_in(request):
        return RedirectResponse("/login", status_code=302)

    ep = db.query(ExtractedProgram).filter(ExtractedProgram.id == ep_id).first()
    if not ep:
        return templates.TemplateResponse(request, "error.html", {"message": "البرنامج غير موجود"}, status_code=404)

    import json
    subjects = json.loads(ep.subjects_json)
    subject_code = request.form.get("subject_code", "")
    subject_name = ""
    for s in subjects:
        if s["code"] == subject_code:
            subject_name = s["name"]
            break

    if not subject_name:
        return RedirectResponse(f"/generate/subject/{ep_id}?err=nosubject", status_code=302)

    # توليد الدليل بالذكاء الاصطناعي
    from .ai_generator import generate_guide
    spec_name = ep.specialization
    title, content = generate_guide(spec_name, subject_name)

    # إنشاء المادة إذا لم تكن موجودة
    subj_slug = subject_name.lower().replace(" ", "-")[:80]
    subject = db.query(Subject).filter(Subject.slug == subj_slug).first()
    if not subject:
        # إنشاء تخصص إذا لم يكن موجوداً
        spec_slug = spec_name.lower().replace(" ", "-")[:80]
        spec = db.query(Specialization).filter(Specialization.slug == spec_slug).first()
        if not spec:
            spec = Specialization(name=spec_name, slug=spec_slug, description="", icon="📘")
            db.add(spec)
            db.flush()
        subject = Subject(specialization_id=spec.id, name=subject_name, slug=subj_slug, description="", icon="📚")
        db.add(subject)
        db.flush()

    guide = Guide(subject_id=subject.id, title=title, content=content)
    db.add(guide)

    # حفظ البرنامج كمستخدم
    ep.used = True
    db.commit()

    return RedirectResponse(f"/view/guide/{guide.id}", status_code=302)
