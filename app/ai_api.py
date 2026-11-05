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
    """بناء prompt مناسب للذكاء الاصطناعي"""
    kind_label = "دليل المتربص" if kind == "guide" else "درس التكوين المهني"
    prompt = f"""أنت مساعد تعليمي متخصص في التكوين المهني.
أنتِج محتوى تعليمي متكامل {kind_label} حول: "{subject}" ضمن تخصص "{spec}".

المطلوب:
- محتوى تعليمي منظم ومفيد للمتربص في التكوين المهني
- يحتوي على: مقدمة، أهداف، مفاهيم أساسية، تطبيقات عملية، نصائح، أسئلة تقويمية
- اللغة: العربية الفصحى الواضحة والمبسطة
- التنسيق: HTML (استخدم <h3> للعناوين الفرعية، <ul> و<li> للنقاط، <p> للفقرات)

مخرجات HTML فقط، بدون أي نص خارجي.

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


def is_available() -> bool:
    """هل API Key مضبوط؟"""
    return bool(GEMINI_API_KEY)


# ===== الاستخدام من خارج المشروع =====
# من Python:
#   from app.ai_api import generate_with_gemini, is_available
#   if is_available():
#       title, content = generate_with_gemini("الإلكتروني", "الأساسيات الإلكترونية", "guide")
