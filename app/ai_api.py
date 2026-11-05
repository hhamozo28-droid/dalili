"""
التوصيل بذكاء اصطناعي خارجي — Google Gemini
يُستخدم عند توفر API Key في ملف .env

إذا لم يكن هناك API Key، يعود إلى المولد المدمج (ai_generator.py)
"""
import os
import requests
import json
import re

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
GEMINI_MODEL = "gemini-3.8-flash"


def _call_gemini(prompt: str, temperature: float = 0.7, max_tokens: int = 8000) -> str:
    """استدعاء Gemini API مع إعادة محاولة لـ 503"""
    import time
    headers = {
        "Authorization": f"Bearer {GEMINI_API_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "model": GEMINI_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    for attempt in range(5):
        try:
            response = requests.post(GEMINI_URL, headers=headers, json=data, timeout=120)
            if response.status_code == 503:
                if attempt < 4:
                    time.sleep(3 * (attempt + 1))
                    continue
                raise Exception(f"Gemini API 503 — النموذج تحت ضغط طلب عالٍ")
            if response.status_code != 200:
                raise Exception(f"Gemini API error: {response.status_code} — {response.text[:300]}")
            result = response.json()
            if isinstance(result, list):
                raise Exception(f"Gemini API returned list: {result[:200]}")
            if "choices" in result:
                return result["choices"][0]["message"]["content"].strip()
            elif "candidates" in result:
                parts = result["candidates"][0].get("content", {}).get("parts", [])
                return parts[0].get("text", "").strip() if parts else ""
            raise Exception(f"Gemini API unexpected response: {str(result)[:200]}")
        except requests.exceptions.ReadTimeout:
            if attempt < 4:
                time.sleep(3 * (attempt + 1))
                continue
            raise Exception("Gemini API timeout")
    raise Exception("Gemini API exhausted retries")


def _extract_title(text: str) -> str:
    """استخراج العنوان من النص"""
    text = text.strip().split("\n")[0].strip()
    text = text.replace("**", "").replace("#", "").strip()
    if len(text) > 60:
        text = text[:57] + "..."
    return text


# ===== توليد الدليل الكامل (المنهجية الموحدة) =====

_GUIDE_METHODOLOGY = """أنت أستاذ متخصص في التكوين المهني الجزائري، ولديك خبرة طويلة في إعداد أدلة المتربصين.

أنتِج دليل متربص متكامل وفق المنهجية الموحدة التالية بالضبط:

## الهيكل العام:

### 1. المقدمة
<h2>المقدمة</h2>
<p>مقدمة تشرح أهمية الموضوع في مجال {spec} وتعرض أهداف الوحدة التدريبية.</p>

### 2. ثمانية فصول
لكل فصل:
- عنوان الفصل (الفصل الأول، الفصل الثاني، ...)
- محتوى الفصل (شرح مفاهيمي)
- 4 أوراق تدريب (ورقة تدريب 01 إلى 04)
- 2 حالات تطبيقية (حالة تطبيقية 01 إلى 02)

### 3. بطاقات المهارات المهنية
5-6 بطاقات مهارية

### 4. حلول أوراق التدريب والحالات

## تركيب كل ورقة تدريب (بالضبط):
<div class="worksheet">
<h3>ورقة تدريب XX — عنوان</h3>
<p><b>الفصل:</b> الفصل الأول | <b>العمل:</b> فردي أو ثنائي | <b>الوسائل:</b> ذكر الوسائل</p>
<p><b>الوضعية:</b> وصف الوضعية المهنية الافتراضية</p>
<p><b>المطلوب:</b> وصف المهام المطلوبة</p>
<p><b>منهج الإنجاز:</b> خطوات الإنجاز المهنية</p>
<p><b>فحص الأداء:</b> نقاط الفحص والتقييم</p>
<p><b>مساحة العمل والتبرير:</b></p>
<p class="work-space">.....................................................................</p>
<p><b>تقييم ذاتي:</b> معايير التقييم الذاتي</p>
</div>

## تركيب كل حالة تطبيقية (بالضبط):
<div class="case">
<h3>حالة تطبيقية XX — عنوان</h3>
<p><b>وضعية مهنية افتراضية:</b> وصف الوضعية</p>
<p><b>العمل المطلوب:</b> وصف المهام</p>
<p><b>المسار المهني:</b> المسار والصلاحيات</p>
<p><b>الدليل المطلوب:</b> الأدلة المطلوبة</p>
<p><b>تسجيل الخطوات والنتيجة:</b></p>
<p class="work-space">.....................................................................</p>
<p><b>التحقق:</b> كيفية التحقق والمتابعة</p>
</div>

## تركيب كل بطاقة مهارية (بالضبط):
<div class="skill-card">
<h3>بطاقة مهارية XX — عنوان</h3>
<p><b>السياق:</b> وصف السياق</p>
<p><b>المدخلات والوسائل:</b> ذكر المدخلات والوسائل</p>
<p><b>خطوات الإنجاز:</b> وصف الخطوات</p>
<p><b>معايير الإتقان:</b> ذكر المعايير</p>
<p><b>أدلة الممارسة:</b> الأدلة المطلوبة</p>
<p><b>تقدير الأداء:</b> مستويات التقدير</p>
<p><b>الملاحظات:</b></p>
<p class="work-space">.....................................................................</p>
</div>

## تركيب الحلول:
<h2>حلول أوراق التدريب والحالات</h2>
لكل فصل: <h3>حلول الفصل X</h3> ثم حلول الأوراق والحالات

## متطلبات المحتوى:
- اللغة: العربية الفصحى الواضحة والمبسطة
- العمق: مناسب لمستوى متربص في التكوين المهني
- المحتوى: مرتبط بـ «{subject}» في مجال «{spec}»
- التنسيق: HTML فقط، استخدم العناصر المحددة أعلاه بالضبط
- لا تستخدم Markdown، فقط HTML
- لا تضيف أي نص خارج الهيكل المحدد

أرجع محتوى HTML الكامل للدليل فقط، بدون أي نص خارجي."""


def generate_guide_full(spec: str, subject: str):
    """
    توليد دليل متربص كامل وفق المنهجية الموحدة.
    يُرجع (العنوان, المحتوى HTML الكامل)
    """
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY غير مضبوط")

    # توليد العنوان
    title_text = _call_gemini(
        f'اختر عنواناً لدليل متربص حول "{subject}" ضمن تخصص "{spec}" في التكوين المهني. '
        'بين 5 و12 كلمة، عربي واضح. أرجع العنوان فقط.',
        temperature=0.5
    )
    title = _extract_title(title_text)

    # توليد المحتوى الكامل
    prompt = _GUIDE_METHODOLOGY.format(spec=spec, subject=subject)
    content = _call_gemini(prompt, temperature=0.7, max_tokens=8000)

    return title, content


# ===== توليد الدرس (مختصر — بدون المنهجية الموحدة) =====

def generate_lesson_simple(spec: str, subject: str):
    """توليد درس مختصر (ليس دليلاً كاملاً)"""
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY غير مضبوط")

    title_text = _call_gemini(
        f'اختر عنواناً لدرس تكوين مهني حول "{subject}" ضمن تخصص "{spec}". '
        'بين 5 و12 كلمة، عربي واضح. أرجع العنوان فقط.',
        temperature=0.5
    )
    title = _extract_title(title_text)

    content = _call_gemini(
        f"""أنت أستاذ في التكوين المهني. أنتِج درساً تعليمياً مختصراً حول "{subject}" ضمن تخصص "{spec}".

الهيكل:
<h3>الأهداف</h3>
<ul><li>هدف 1</li><li>هدف 2</li><li>هدف 3</li></ul>
<h3>المفاهيم الأساسية</h3>
<ul><li>مفهوم 1</li><li>مفهوم 2</li><li>مفهوم 3</li></ul>
<h3>التطبيقات العملية</h3>
<ul><li>تطبيق 1</li><li>تطبيق 2</li></ul>
<h3>خلاصة</h3>
<p>ملخص النقاط</p>

HTML فقط، لا Markdown.""",
        temperature=0.7, max_tokens=2000
    )

    return title, content


# ===== استخراج التخصص والمواد =====

def extract_specialization_and_subjects(text: str):
    """استخراج التخصص والمواد من نص برنامج التكوين المهني"""
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
    json_match = re.search(r'\{.*\}', result, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    return {"specialization": "غير معروف", "subjects": []}


def is_available() -> bool:
    """هل API Key مضبوط؟"""
    return bool(GEMINI_API_KEY)
