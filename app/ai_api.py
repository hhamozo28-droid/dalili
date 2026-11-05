"""
التوصيل بذكاء اصطناعي خارجي — Google Gemini
يُستخدم عند توفر API Key في ملف .env

إذا لم يكن هناك API Key، يعود إلى المولد المدمج (ai_generator.py)
"""
import os
import requests

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
GEMINI_MODEL = "gemini-1.5-flash"  # المجاني


def _build_prompt(spec: str, subject: str, kind: str) -> str:
    """بناء prompt متكامل للذكاء الاصطناعي — محتوى تعليمي احترافي"""
    kind_label = "دليل المتربص" if kind == "guide" else "درس التكوين المهني"
    prompt = f"""أنت أستاذ متخصص في التكوين المهني، ولديك خبرة طويلة في تدريب المتربصين.
أنتِج {kind_label} تعليمي احترافي ومتكامل حول: "{subject}" ضمن تخصص "{spec}".

الهيكل المطلوب:
1. <h3>مقدمة</h3> — مقدمة مختصرة توضح أهمية الموضوع في مجال {spec}
2. <h3>الأهداف</h3> — <ul> مع 3-4 أهداف تعليمية واضحة ومحددة
3. <h3>المفاهيم الأساسية</h3> — <ul> مع شرح 3-5 مفاهيم رئيسية مرتبطة بـ {subject}
4. <h3>التطبيقات العملية</h3> — <ul> مع أمثلة تطبيقية واقعية من الميدان
5. <h3>نصائح للمتربص</h3> — <ul> مع 4-5 نصائح عملية للسلامة والefficacité
6. <h3>خلاصة</h3> — <ul> ملخص النقاط الرئيسية
7. <h3>أسئلة تقويمية</h3> — <ol> مع 4-5 أسئلة لتقويم فهم المتربص

متطلبات المحتوى:
- اللغة: العربية الفصحى الواضحة والمبسطة، مناسبة للمستوى المهني
- العمق: مناسب لمستوى متربص في التكوين المهني
- الطول: محتوى متكامل (800-1500 كلمة تقريباً)
- التنسيق: HTML فقط (استخدم <h3> للعناوين، <ul> و<li> للنقاط، <ol> للأسئلة، <p> للفقرات)
- لا تستخدم Markdown، فقط HTML

مخرجات HTML فقط، بدون أي نص خارجي أو تعليقات.

---

محتوى {kind_label}:"""
    return prompt


def _build_title_prompt(spec: str, subject: str, kind: str) -> str:
    """بناء prompt لإنشاء عنوان"""
    kind_label = "دليل" if kind == "guide" else "درس"
    return f"""اختر عنواناً مناسباً لـ {kind_label} تعليمي حول "{subject}" ضمن تخصص "{spec}" في التكوين المهني.
العنوان يجب أن يكون:
- عربياً واضحاً وجذاباً
- بين 5 و12 كلمة
- يعكس محتوى المادة

أرجع العنوان فقط، بدون أي نص آخر."""


def _call_gemini(prompt: str, temperature: float = 0.7) -> str:
    """استدعاء Gemini API"""
    headers = {
        "Authorization": f"Bearer {GEMINI_API_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "model": GEMINI_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": 2000,
    }
    response = requests.post(GEMINI_URL, headers=headers, json=data, timeout=60)
    if response.status_code != 200:
        raise Exception(f"Gemini API error: {response.status_code} — {response.text[:300]}")
    result = response.json()
    return result["choices"][0]["message"]["content"].strip()


def _extract_title(text: str) -> str:
    """استخراج العنوان من النص"""
    text = text.strip().split("\n")[0].strip()
    text = text.replace("**", "").replace("#", "").strip()
    # اقتطاع إذا كان طويلاً جداً
    if len(text) > 60:
        text = text[:57] + "..."
    return text


def generate_with_gemini(spec: str, subject: str, kind: str = "guide"):
    """
    توليد محتوى دليل أو درس عبر Google Gemini.
    يُرجع (العنوان, المحتوى HTML)
    """
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY غير مضبوط في ملف .env")

    # توليد العنوان
    title_text = _call_gemini(_build_title_prompt(spec, subject, kind), temperature=0.5)
    title = _extract_title(title_text)

    # توليد المحتوى
    content = _call_gemini(_build_prompt(spec, subject, kind), temperature=0.7)

    return title, content


def extract_specialization_and_subjects(text: str):
    """
    استخراج التخصص والمواد من نص برنامج التكوين المهني
    يُرجع (specialization: str, subjects: list of dict)
    """
    prompt = f"""أنت مساعد متخصص في برامج التكوين المهني الجزائرية.

قم بتحليل النص المستخرج من برنامج تكوين مهني واستخراج:

1. اسم التخصص بالصيغة الكاملة (مثال: "ميكانيك إصلاح المركبات الخفيفة • 0709MME • شهادة الكفاءة المهنية")
2. جميع المواد مع رموزها وأسماءها:
   - MQ = Module Qualifiant (الوحدة المهنية التخصصية)
   - MC = Module Commun (الوحدة المشتركة)
   - قم بترجمة أسماء المواد إلى العربية إذا كانت بالفرنسية

أرجع النتيجة كصيغة JSON فقط (بدون أي نص آخر):

{{
    "specialization": "التخصص الكامل بالصيغة المذكورة",
    "subjects": [
        {{"code": "MQ1", "name": "الاسم بالعربية", "original_name": "nom original"}},
        {{"code": "MC1", "name": "الاسم بالعربية", "original_name": "nom original"}},
        ...
    ]
}}

إذا لم تجد التخصص، ضع "غير معروف".
إذا لم تجد المواد، ضع قائمة فارغة.

---
نص البرنامج:
{text[:8000]}"""

    result = _call_gemini(prompt, temperature=0.3)
    import json
    import re
    # استخراج JSON من النص
    json_match = re.search(r'\{.*\}', result, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    # نتيجة فارغة إذا فشل التحليل
    return {"specialization": "غير معروف", "subjects": []}


def is_available() -> bool:
    """هل API Key مضبوط؟"""
    return bool(GEMINI_API_KEY)


# ===== الاستخدام من خارج المشروع =====
# من Python:
#   from app.ai_api import generate_with_gemini, is_available
#   if is_available():
#       title, content = generate_with_gemini("الإلكتروني", "الأساسيات الإلكترونية", "guide")
