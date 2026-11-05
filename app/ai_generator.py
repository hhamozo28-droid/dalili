"""
مولد المحتوى بالذكاء الاصطناعي لمشروع dalili
يولّد عنوان ومحتوى دليل/درس بناءً على التخصص والمادة

أولاً يحاول استخدام Google Gemini API (عند توفر GEMINI_API_KEY).
إذا لم يكن المفتاح متاحاً، يعود إلى المولد المدمج.
"""
import os
import random
from typing import Tuple


def _try_gemini(spec: str, subject: str, kind: str):
    """محاولة استخدام Gemini API الخارجي"""
    try:
        from .ai_api import generate_guide_full, generate_lesson_simple, is_available
        if is_available():
            if kind == "guide":
                return generate_guide_full(spec, subject)
            else:
                return generate_lesson_simple(spec, subject)
    except Exception:
        pass
    return None


def generate_guide(spec: str, subject: str) -> Tuple[str, str]:
    """توليد دليل المتربص — يستخدم Gemini عند توفر المفتاح، وإلا المولد المدمج"""
    result = _try_gemini(spec, subject, "guide")
    if result:
        return result
    return _generate_builtin_guide(spec, subject)


def generate_lesson(spec: str, subject: str) -> Tuple[str, str]:
    """توليد درس التكوين المهني — يستخدم Gemini عند توفر المفتاح، وإلا المولد المدمج"""
    result = _try_gemini(spec, subject, "lesson")
    if result:
        return result
    return _generate_builtin_lesson(spec, subject)


# ===== المولد المدمج (للاستخدام بدون API خارجي) =====

_INTROS = [
    "يهدف هذا الدليل/الدرس إلى تزويد المتربص بالمعرفة العملية حول {topic}.",
    "في هذا الجزء، نتعرّف على المفاهيم الأساسية المتعلقة بـ {topic}.",
    "يقدّم هذا المحتوى شرحاً مبسّطاً لـ {topic} بما يتناسب مع متطلبات التكوين المهني.",
    "سنستعرض في هذا الدروس أهم ما يخص {topic} من الناحية العملية.",
]

_SECTIONS = [
    ("الأهداف", "يتمحور هذا المحتوى حول الأهداف التالية:\n- فهم المفاهيم الأساسية لـ {topic}\n- القدرة على تطبيق المعارف في المواقف العملية\n- اكتساب المهارات المطلوبة في سوق العمل"),
    ("المفاهيم الأساسية", "يرتكز موضوع {topic} على عدة مفاهيم رئيسية:\n- <b>التعريف:</b> ما هو {topic} وما أهميته في مجال {spec}\n- <b>المكونات:</b> الأجزاء أو العناصر الأساسية المرتبطة به\n- <b>الوظائف:</b> الأدوار والوظائف التي يقوم بها في السياق المهني"),
    ("التطبيقات العملية", "يُستخدم {topic} في تطبيقات عملية متعددة:\n- تشخيص الأعطال الشائعة\n- تركيب وضبط الأجهزة\n- الصيانة الدورية\n- قراءة المخططات والرسومات الفنية"),
    ("نصائح للمتربص", "نصائح مهمة:\n- ✅ احرص على قراءة التعليمات بعناية قبل البدء\n- ✅ استخدم أدوات الوقاية الشخصية (السلامة)\n- ✅ نظّر جيداً في الحالات المشابهة\n- ✅ اطلب المساعدة من المدرب عند الحاجة"),
    ("خلاصة", "بعد هذا العرض، أصبح المتربص قادراً على:\n- التعرف على مكونات {topic}\n- تطبيق الإجراءات الأساسية\n- فهم دور {topic} في سياق {spec}"),
]

_QUESTIONS = [
    "ما تعريف {topic}؟",
    "ما أهم مكونات {topic}؟",
    "اذكر تطبيقين عمليين لـ {topic}.",
    "ما دور {topic} في مجال {spec}؟",
]


def _build_content(spec: str, subject: str) -> str:
    """بناء محتوى تعليمي منظم بناءً على التخصص والمادة"""
    topic = subject
    intro = random.choice(_INTROS).format(topic=topic)

    parts = [f"<p>{intro}</p>"]

    for heading, body in _SECTIONS:
        text = body.format(topic=topic, spec=spec)
        lines = text.split("\n")
        heading_html = f"<h3>{heading}</h3>"
        list_html = "<ul>" + "".join(f"<li>{l.strip()}</li>" for l in lines if l.strip()) + "</ul>"
        parts.append(f"{heading_html}{list_html}")

    questions_html = "<h3>أسئلة تقويمية</h3><ol>"
    for q in _QUESTIONS:
        questions_html += f"<li>{q.format(topic=topic, spec=spec)}</li>"
    questions_html += "</ol>"
    parts.append(questions_html)

    return "\n".join(parts)


def _build_title(spec: str, subject: str) -> str:
    """بناء عنوان مناسب للدرس/الدليل"""
    templates = [
        f"مدخل إلى {subject} — {spec}",
        f"أساسيات {subject} في مجال {spec}",
        f"التكوين المهني: {subject}",
        f"دليل المتربص في {subject}",
        f"{subject} — مفاهيم وتطبيقات",
    ]
    return random.choice(templates)


def _generate_builtin_guide(spec: str, subject: str) -> Tuple[str, str]:
    """توليد دليل المتربص بالمولد المدمج"""
    title = _build_title(spec, subject)
    content = _build_content(spec, subject)
    return title, content


def _generate_builtin_lesson(spec: str, subject: str) -> Tuple[str, str]:
    """توليد درس التكوين المهني بالمولد المدمج"""
    title = _build_title(spec, subject)
    content = _build_content(spec, subject)
    return title, content
