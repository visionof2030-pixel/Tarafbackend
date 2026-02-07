import os
import random
import hashlib
import secrets
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

import jwt
import google.generativeai as genai
from fastapi import FastAPI, HTTPException, Header, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn

# =====================================================
# ENV
# =====================================================
JWT_SECRET = os.getenv("JWT_SECRET", "CHANGE_ME_SECRET")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "FahadJassar14061436")

GEMINI_KEYS = [
    os.getenv("GEMINI_API_KEY_1"),
    os.getenv("GEMINI_API_KEY_2"),
    os.getenv("GEMINI_API_KEY_3"),
    os.getenv("GEMINI_API_KEY_4"),
    os.getenv("GEMINI_API_KEY_5"),
    os.getenv("GEMINI_API_KEY_6"),
    os.getenv("GEMINI_API_KEY_7"),
]
GEMINI_KEYS = [k for k in GEMINI_KEYS if k]

if not GEMINI_KEYS:
    raise RuntimeError("No Gemini API Keys found")

# =====================================================
# APP
# =====================================================
app = FastAPI(title="Nassr AI Backend - تقارير تعليمية")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================
# MODELS
# =====================================================
class AskRequest(BaseModel):
    prompt: str
    reportData: Optional[Dict] = None

class ActivateRequest(BaseModel):
    code: str

class ReportGenerateRequest(BaseModel):
    reportType: str
    subject: Optional[str] = ""
    lesson: Optional[str] = ""
    grade: Optional[str] = ""
    target: Optional[str] = ""
    place: Optional[str] = ""
    count: Optional[str] = ""

class SaveTeacherRequest(BaseModel):
    education: Optional[str] = ""
    school: Optional[str] = ""
    grade: Optional[str] = ""
    subject: Optional[str] = ""
    target: Optional[str] = ""
    place: Optional[str] = ""
    lesson: Optional[str] = ""
    teacher: Optional[str] = ""
    principal: Optional[str] = ""
    teacherType: Optional[str] = "المعلم"
    principalType: Optional[str] = "المدير"
    term: Optional[str] = ""
    count: Optional[str] = ""
    manualTitle: Optional[str] = ""
    manualHijriDate: Optional[str] = ""
    manualGregorianDate: Optional[str] = ""
    tools: Optional[List[str]] = []
    goal: Optional[str] = ""
    summary: Optional[str] = ""
    steps: Optional[str] = ""
    strategies: Optional[str] = ""
    strengths: Optional[str] = ""
    improve: Optional[str] = ""
    recomm: Optional[str] = ""

class SupportRequest(BaseModel):
    name: str
    phone: str
    issue: str

# =====================================================
# STORAGE (مؤقت - in memory)
# =====================================================
# code_hash -> expires_at
VALID_CODES = {}

# تخزين بيانات المستخدمين (في الواقع يمكن استخدام قاعدة بيانات)
USER_DATA = {}

# =====================================================
# أنواع التقارير (تم نقلها من الفرونت إند)
# =====================================================
LINGUISTIC_ENRICHMENT = [
    "بما يعزز من فاعلية العملية التعليمية ويرتقي بمستوى الممارسات الصفية",
    "بما ينسجم مع توجهات التعليم الحديثة ونواتج التعلم المستهدفة",
    "بأسلوب مهني يعكس التخطيط الجيد والتنفيذ التربوي الفعال",
    "وفق معايير تربوية تسهم في تحسين جودة التعليم داخل الصف",
    "وبما يدعم بناء بيئة تعلم محفزة ومشجعة على المشاركة",
]

REPORTS_BY_CATEGORY = {
    "التقارير التعليمية الصفية": [
        "تقرير أنشطة صفية",
        "تقرير توزيع وقت الحصة",
        "تقرير درس تم تنفيذه",
        "تقرير تعليم تعاوني بين الطلاب",
        "تقرير المشاركات بين الطلاب",
        "تقرير توزيع المنهج",
        "تقرير الفصول المقلوبة",
        "تقرير تنفيذ درس تطبيقي",
        "تقرير تفعيل الفصول الافتراضية",
        "تقرير التعليم المدمج",
        "تقرير التعليم عن بعد",
        "تقرير استخدام أنظمة إدارة التعلم",
        "تقرير إدارة الوقت في الصف",
        "تقرير تنظيم البيئة الصفية",
        "تقرير إدارة الموارد التعليمية",
        "تقرير إدارة السلوك الصفي",
        "تقرير الأنشطة التفاعلية",
        "تقرير العروض العملية",
        "تقرير التعلم التعاوني",
        "تقرير التعلم الذاتي الموجه",
        "تقرير الألعاب التعليمية الرقمية",
        "تقرير التعلم بالأقران",
        "تقرير استراتيجيات التدريس المستخدمة",
        "تقرير تنويع أساليب الشرح",
        "تقرير مراعاة الفروق الفردية",
        "تقرير تفعيل مهارات التفكير",
        "تقرير دمج مهارات القرن الحادي والعشرين",
        "تقرير توظيف الوسائل التعليمية",
        "تقرير التهيئة الذهنية للدرس",
        "تقرير ختام الدرس والتقويم الختامي",
        "تقرير ربط الدرس بالحياة"
    ],
    "التقارير العلاجية والدعم الفردي": [
        "تقرير خطة علاجية",
        "تقرير سجل الخطط العلاجية",
        "تقرير رعاية الطلاب المتأخرين دراسيًا",
        "تقرير دراسة حالة",
        "تقرير معرفة الميول والاتجاهات",
        "تقرير التحليل الاحتياجات التدريبية",
        "تقرير دعم الطلاب ذوي الإعاقة",
        "تقرير خطة دعم فردية",
        "تقرير متابعة التحسن الأكاديمي",
        "تقرير تشخيص صعوبات التعلم",
        "تقرير برامج التقوية",
        "تقرير الإرشاد الأكاديمي الفردي",
        "تقرير متابعة الخطط العلاجية",
        "تقرير دعم الموهبة منخفضة التحصيل"
    ],
    "التقارير التحفيزية والسلوكية": [
        "تقرير تحفيز الطلاب",
        "تقرير تعزيز السلوك الإيجابي",
        "تقرير نظام الحوافز والمكافآت",
        "تقرير برنامج الدعم النفسي",
        "تقرير تحسين نتائج العلوم في الاختبارات الوطنية (نافس)",
        "تقرير تحسين نتائج الرياضيات في الاختبارات الوطنية (نافس)",
        "تقرير تحسين نتائج اللغة العربية في الاختبارات الوطنية (نافس)",
        "تقرير الانضباط المدرسي",
        "تقرير معالجة السلوكيات السلبية",
        "تقرير تعزيز الدافعية للتعلم",
        "تقرير بناء الاتجاهات الإيجابية",
        "تقرير متابعة السلوك الفردي",
        "تقرير برامج تعديل السلوك",
        "تقرير تعزيز القيم والاتجاهات"
    ],
    "تقارير الأنشطة غير الصفية": [
        "تقرير نشاط إثرائي",
        "تقرير رعاية الموهوبين",
        "تقرير المبادرات والابتكار",
        "تقرير تفعيل المنصات التعليمية",
        "تقرير حصة النشاط",
        "تقرير تفعيل حصص النشاط",
        "تقرير تنفيذ إذاعة مدرسية",
        "تقرير الزيارات الميدانية",
        "تقرير مبادرة تطوعية",
        "تقرير الاحتفال باليوم الوطني",
        "تقرير المعلم الصغير",
        "تقرير الأندية الطلابية",
        "تقرير المسابقات التعليمية",
        "تقرير الأنشطة الثقافية",
        "تقرير الأنشطة العلمية",
        "تقرير الأنشطة الرياضية",
        "تقرير الأنشطة الفنية",
        "تقرير المعارض المدرسية",
        "تقرير الأيام العالمية",
        "تقرير البرامج الموسمية"
    ],
    "تقارير التواصل مع أولياء الأمور والمجتمع": [
        "تقرير التواصل مع ولي الأمر",
        "تقرير إشعار ولي الأمر عن مستوى ابنه",
        "تقرير سجل التواصل مع أولياء الأمور",
        "تقرير حضور اجتماع أولياء الأمور",
        "تقرير الشراكات المهنية",
        "تقرير مجتمعات التعلم",
        "تقرير المجتمعات المهنية",
        "تقرير اللقاءات التربوية",
        "تقرير المبادرات المجتمعية",
        "تقرير التواصل الإلكتروني مع أولياء الأمور",
        "تقرير الزيارات المنزلية",
        "تقرير استطلاع رضا أولياء الأمور",
        "تقرير التعاون مع الجهات الخارجية",
        "تقرير العمل التطوعي المجتمعي"
    ],
    "التقارير التخطيطية والتنظيمية": [
        "تقرير خطة أسبوعية",
        "تقرير تفعيل الخطة الأسبوعية",
        "تقرير تخطيط المشاريع التعليمية",
        "تقرير تخطيط الرحلات التعليمية",
        "تقرير إدارة الاجتماعات",
        "تقرير المناوبة والفسحة",
        "تقرير الإشراف اليومي",
        "تقرير إدارة الأزمات",
        "تقرير الخطة الفصلية",
        "تقرير الخطة السنوية",
        "تقرير تنظيم الجداول الدراسية",
        "تقرير تنظيم المهام الإدارية",
        "تقرير توزيع الأدوار",
        "تقرير إدارة الوقت المدرسي",
        "تقرير متابعة تنفيذ الخطط"
    ],
    "تقارير التقييم والمتابعة": [
        "تقرير كشف المتابعة",
        "تقرير تصنيف الطلاب",
        "تقرير تنفيذ اختبار تحسن",
        "تقرير سجل الدرجات الإلكتروني",
        "تقرير تحليل النتائج",
        "تقرير مقارنة السلاسل الزمنية",
        "تقرير قياس الأثر التعليمي",
        "تقرير مؤشرات الأداء التعليمي",
        "تقرير تقييم المخرجات التعليمية",
        "تقرير تقييم المشاريع الطلابية",
        "تقرير تقييم الأداء العملي",
        "تقرير تقييم المحافظ الإلكترونية",
        "تقرير التقييم الإلكتروني",
        "تقرير تحليل نتائج الاختبارات التشخيصية",
        "تقرير تحليل الاختبارات التحصيلية",
        "تقرير متابعة مستوى الإتقان",
        "تقرير فجوات التعلم",
        "تقرير تقدم الطلاب",
        "تقرير تحليل بنود الاختبار",
        "تقرير متابعة نواتج التعلم"
    ],
    "تقارير التدريب والتطوير المهني": [
        "تقرير حضور دورات وورش تدريبية",
        "تقرير الورش التدريبية التي قدمتها",
        "تقرير التدريب على الاختبارات المعيارية",
        "تقرير التدريب على المناهج الحديثة",
        "تقرير نقل أثر التدريب",
        "تقرير متابعة الدورات العالمية",
        "تقرير التطوير المهني المستمر",
        "تقرير المشاركة في المؤتمرات التعليمية",
        "تقرير حضور الندوات العلمية",
        "تقرير المشاركة في البحث التربوي",
        "تقرير التعلم الذاتي المهني",
        "تقرير مجتمعات التعلم المهنية",
        "تقرير القراءة التربوية المتخصصة",
        "تقرير تبادل الخبرات",
        "تقرير بناء المسار المهني"
    ],
    "تقareير توظيف التكنولوجيا": [
        "تقرير المحتوى الرقمي المنتج",
        "تقرير إنتاج المحتوى الرقمي",
        "تقرير استخدام أنظمة إدارة التعلم",
        "تقرير التقييم الإلكتروني",
        "تقرير الواقع المعزز في التعليم",
        "تقرير الألعاب التعليمية الرقمية",
        "تقرير توظيف الذكاء الاصطناعي",
        "تقرير التعلم المتنقل",
        "تقرير الصفوف الافتراضية",
        "تقرير أدوات التعلم التفاعلي",
        "تقرير الأمن الرقمي",
        "تقرير الثقافة الرقمية",
        "تقرير التحول الرقمي",
        "تقرير استخدام التطبيقات التعليمية"
    ],
    "تقارير البحث والتطوير المناهجي": [
        "تقرير تصميم الوحدات التعليمية",
        "تقرير إعداد المواد التعليمية",
        "تقرير تطوير المناهج الإثرائية",
        "تقرير إعداد بنك الأسئلة",
        "تقرير تصميم الأنشطة اللاصفية",
        "تقرير تحليل محتوى المنهج",
        "تقرير مواءمة المنهج مع نواتج التعلم",
        "تقرير تطوير أدوات التقويم",
        "تقرير البحث الإجرائي"
    ],
    "تقارير الجودة واللجان": [
        "تقرير عضوية لجنة التميز والجودة",
        "تقرير عضوية لجنة التدقيق",
        "تقرير إدارة الموارد التعليمية",
        "تقرير تحسين الجودة",
        "تقرير متابعة مؤشرات الأداء",
        "تقرير التقييم الذاتي",
        "تقرير الاعتماد المدرسي",
        "تقرير الخطط التحسينية"
    ],
    "تقارير الأمن والسلامة": [
        "تقرير إجراءات السلامة في الصف",
        "تقرير الرعاية الصحية في المدرسة",
        "تقرير جرد المختبرات وغرف المصادر",
        "تقرير خطط الإخلاء",
        "تقرير السلامة المدرسية",
        "تقرير إدارة المخاطر",
        "تقرير الإسعافات الأولية",
        "تقرير جاهزية المباني"
    ]
}

# =====================================================
# النصوص الافتراضية للتقارير
# =====================================================
DEFAULT_REPORT_TEXTS = {
    "goal": [
        "تنمية المهارات الأساسية في المادة وتحقيق الأهداف التعليمية المحددة",
        "تحسين مستوى التحصيل الدراسي للطلاب وتعزيز دافعيتهم للتعلم",
        "تطبيق استراتيجيات تعليمية متنوعة لتحسين جودة العملية التعليمية"
    ],
    "summary": [
        "تقرير يوثق الأنشطة التعليمية المنفذة ونتائجها وفق المعايير التربوية",
        "وثيقة تربوية تسجل الجهود المبذولة لتحقيق أهداف الدرس والمنهج",
        "تقرير مهني يعكس الممارسات التعليمية الفعالة والتطوير المستمر"
    ],
    "steps": [
        "بدأت الحصة بالتهيئة المناسبة ثم الانتقال إلى شرح المفهوم الرئيسي",
        "تم تقسيم الطلاب إلى مجموعات تعاونية لممارسة الأنشطة العملية",
        "شمل التنفيذ العروض التقديمية والتطبيقات العملية والتقويم المستمر"
    ],
    "strategies": [
        "استخدام التعلم التعاوني والتعلم القائم على المشاريع",
        "توظيف استراتيجيات التفكير الناقد والتعلم النشط",
        "دمج التقنية في التعليم واستخدام الوسائل المتعددة"
    ],
    "strengths": [
        "تفاعل الطلاب الإيجابي ومشاركتهم الفعالة في الأنشطة",
        "تنوع الوسائل التعليمية المستخدمة وملاءمتها لأهداف الدرس",
        "إدارة الصف الفعالة وتنظيم الوقت بشكل مناسب"
    ],
    "improve": [
        "التركيز على الطلاب الضعاف وتقديم دعم إضافي لهم",
        "زيادة استخدام التقنية التفاعلية في الشرح والتطبيق",
        "تنويع أساليب التقويم لقياس جميع المهارات"
    ],
    "recomm": [
        "توفير مزيد من التدريب على استراتيجيات التعلم النشط",
        "تعزيز الشراكة مع أولياء الأمور لمتابعة التحصيل الدراسي",
        "تطوير بنك الأنشطة الإثرائية لدعم المتفوقين"
    ]
}

# =====================================================
# أدوات ووسائل تعليمية
# =====================================================
EDUCATIONAL_TOOLS = [
    "سبورة",
    "سبورة ذكية",
    "جهاز عرض",
    "أوراق عمل",
    "حاسب",
    "عرض تقديمي",
    "بطاقات تعليمية",
    "صور توضيحية",
    "كتاب",
    "أدوات رياضية"
]

# =====================================================
# إدارات التعليم (من الفرونت إند)
# =====================================================
EDUCATION_ADMINISTRATIONS = [
    "الإدارة العامة للتعليم بمنطقة مكة المكرمة",
    "الإدارة العامة للتعليم بمنطقة الرياض",
    "الإدارة العامة للتعليم بمنطقة المدينة المنورة",
    "الإدارة العامة للتعليم بالمنطقة الشرقية",
    "الإدارة العامة للتعليم بمنطقة القصيم",
    "الإدارة العامة للتعليم بمنطقة عسير",
    "الإدارة العامة للتعليم بمنطقة تبوك",
    "الإدارة العامة للتعليم بمنطقة حائل",
    "الإدارة العامة للتعليم بمنطقة الحدود الشمالية",
    "الإدارة العامة للتعليم بمنطقة جازان",
    "الإدارة العامة للتعليم بمنطقة نجران",
    "الإدارة العامة للتعليم بمنطقة الباحة",
    "الإدارة العامة للتعليم بمنطقة الجوف",
    "الإدارة العامة للتعليم بمحافظة الأحساء",
    "الإدارة العامة للتعليم بمحافظة الطائف",
    "الإدارة العامة للتعليم بمحافظة جدة"
]

# =====================================================
# HELPERS
# =====================================================
def pick_gemini_model():
    key = random.choice(GEMINI_KEYS)
    genai.configure(api_key=key)
    return genai.GenerativeModel("models/gemini-2.5-flash-lite")

def generate_short_code():
    return secrets.token_hex(3).upper()

def hash_code(code: str):
    return hashlib.sha256(code.encode()).hexdigest()

def create_jwt(expires_at: datetime):
    payload = {
        "type": "activation",
        "exp": expires_at
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def verify_jwt(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="TOKEN_EXPIRED")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="INVALID_TOKEN")

async def get_current_user(x_token: str = Header(..., alias="X-Token")):
    payload = verify_jwt(x_token)
    return payload

# =====================================================
# DURATIONS
# =====================================================
DURATIONS = {
    "5m": timedelta(minutes=5),
    "30m": timedelta(minutes=30),
    "1h": timedelta(hours=1),
    "3h": timedelta(hours=3),
    "1d": timedelta(days=1),
    "3d": timedelta(days=3),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
    "90d": timedelta(days=90),
    "150d": timedelta(days=150),
}

# =====================================================
# البرومت المتخصص للتقارير التعليمية
# =====================================================
def generate_educational_prompt(report_type: str, subject: str = "", lesson: str = "", 
                               grade: str = "", target: str = "", place: str = "", count: str = "") -> str:
    return f"""أنت خبير تربوي تعليمي محترف تمتلك خبرة ميدانية واسعة في التعليم العام.  
اعتمد منظورًا تربويًا مهنيًا احترافيًا يركّز على تحسين جودة التعليم، ودعم المعلم، وتعزيز بيئة التعلّم، وخدمة القيادة المدرسية.  

التقرير المطلوب: "{report_type}"
{subject if subject else ''}
{lesson if lesson else ''}
{grade if grade else ''}
{target if target else ''}
{place if place else ''}
{count if count else ''}

**توجيهات مهنية:**
- كن موضوعيًا ومتزنًا وبنّاءً  
- قدّم الملاحظات بصيغة تطويرية غير نقدية  
- راعِ واقع الميدان التعليمي وسياق المدرسة  
- اربط بين المعلم والطالب والمنهج والبيئة الصفية والقيادة المدرسية  
- ركّز على جودة التعليم وأثر الممارسات على تعلم الطلاب  
- التزم بلغة عربية فصيحة سليمة وخالية من الأخطاء  

**شروط المحتوى:**اكتب محتوى كل حقل بصيغة تقريرية مهنية وكأنه صادر عن المعلم.
لا تكتب أبداً عنوان الحقل داخل المحتوى ولا تعِد صياغته بصيغة مباشرة (مثل: الهدف التربوي هو، النبذة المختصرة).
⚠️ شرط إلزامي: 
- يجب أن يحتوي كل حقل على ما لا يقل عن 25 كلمة ولا يزيد عن 30 كلمة.
- أي حقل أقل من ذلك يُعد غير مقبول.
ابدأ بالمضمون مباشرة دون تمهيد أو عبارات إنشائية.
يمكن الاستفادة من معنى العنوان أو أحد مفاهيمه بشكل غير مباشر فقط عند الحاجة وبما يخدم الفكرة دون تكرار أو حشو.
احرص على وجود ترابط منطقي بين الأهداف، النبذة المختصرة، الاستراتيجيات، إجراءات التنفيذ، نقاط القوة، نقاط التحسين، والتوصيات.
اربط المحتوى بالمادة الدراسية وعنوان الدرس إن وُجد، وكذلك بمكان التنفيذ، بأسلوب مهني متوازن يجمع بين الإشارة المباشرة وغير المباشرة دون تكلف.
اجعل الهدف النهائي للمحتوى تحسين الممارسة التعليمية ودعم التطوير المهني المستدام.
راعِ الوضوح والترابط، واجعل كل جملة تضيف قيمة تعليمية فعلية.

الحقول المطلوبة:
1. الهدف التربوي
2. نبذة مختصرة  
3. إجراءات التنفيذ
4. الاستراتيجيات
5. نقاط القوة
6. نقاط التحسين
7. التوصيات

يرجى تقديم الإجابة باللغة العربية الفصحى، وتنظيمها بحيث يكون كل حقل في سطر منفصل يبدأ برقمه فقط دون ذكر العنوان."""

# =====================================================
# دالة الإثراء الذكي
# =====================================================
def enrich_and_enforce(text: str, min_words=25, max_words=35, report_type: str = "") -> str:
    """
    إثراء النص وتطبيق الحد الأدنى والأقصى للكلمات بشكل ذكي
    """
    words = text.split()
    
    if len(words) == 0:
        return text
    
    # تحليل السياق من نوع التقرير
    context_keywords = {
        "تقرير علاجي": ["العلاج", "الدعم", "تحسين", "تقدم"],
        "تقرير سلوكي": ["السلوك", "تحفيز", "تعزيز", "مكافأة"],
        "تقرير تقييمي": ["تقييم", "قياس", "نتائج", "مؤشرات"],
        "تقرير نشاط": ["نشاط", "مشاركة", "تفاعل", "تطبيق"],
    }
    
    # تحديد الكلمات الإثرائية المناسبة للسياق
    enrichment_phrases = []
    for keyword, phrases in context_keywords.items():
        if keyword in report_type:
            enrichment_phrases.extend(phrases)
    
    # إذا لم نجد سياق محدد، نستخدم الإثراء العام
    if not enrichment_phrases:
        enrichment_phrases = LINGUISTIC_ENRICHMENT
    
    # إثراء النص إذا كان قصيراً
    if len(words) < min_words:
        # احتساب عدد الكلمات المطلوبة
        words_needed = min_words - len(words)
        
        # إضافة عبارات إثرائية ذكية
        if len(words) < 15:  # إذا كان النص قصير جداً
            # إضافة عبارات تربوية محسنة
            enhancements = [
                "بما يعزز من جودة الممارسة التعليمية وينسجم مع أهداف المنهج",
                "وذلك لتحقيق نواتج التعلم المستهدفة ورفع مستوى التحصيل الدراسي",
                "بما يدعم التطوير المهني المستدام ويعزز فاعلية العملية التعليمية",
                "ويسهم في بناء بيئة تعلمية محفزة تدعم الإبداع والتميز",
                "وذلك تماشياً مع رؤية التعليم الحديثة واستراتيجياته التطويرية",
                "بما يرتقي بالممارسات الصفية ويعزز الشراكة المجتمعية الفاعلة",
            ]
            
            for enhancement in enhancements[:min(2, words_needed//10)]:
                if len(words) < min_words:
                    text += " " + enhancement
                    words = text.split()
        
        # إذا مازال النقص موجوداً
        while len(words) < min_words:
            # اختيار عبارة إثرائية مناسبة
            phrase = random.choice(enrichment_phrases)
            
            # التأكد من أن الإضافة تتناسب مع سياق النص
            if not any(word in text for word in phrase.split()[:3]):
                text += " " + phrase
                words = text.split()
    
    # تقليم النص إذا تجاوز الحد الأقصى
    if len(words) > max_words:
        # المحاولة لتقليم النص بشكل ذكي
        sentences = text.split('،')
        if len(sentences) > 1:
            trimmed_text = ""
            current_words = 0
            for sentence in sentences:
                sentence_words = sentence.split()
                if current_words + len(sentence_words) <= max_words - 5:  # ترك مساحة للختام
                    if trimmed_text:
                        trimmed_text += "، " + sentence
                    else:
                        trimmed_text = sentence
                    current_words += len(sentence_words)
                else:
                    break
            
            if current_words >= min_words:
                text = trimmed_text + "، مما يسهم في تحقيق الأهداف التربوية المنشودة."
                words = text.split()
        
        # إذا مازال الطول زائداً، قص الكلمات الزائدة
        if len(words) > max_words:
            text = " ".join(words[:max_words])
    
    # تحسين جودة النص النهائي
    text = text.replace("  ", " ").strip()
    
    # إضافة نقطة نهائية إذا لم تكن موجودة
    if text and text[-1] not in [".", "!", "؟"]:
        text += "."
    
    return text

# =====================================================
# ROUTES
# =====================================================

@app.get("/")
def health():
    return {
        "status": "healthy",
        "time": datetime.utcnow().isoformat(),
        "service": "ناصر - أداة إصدار التقارير التعليمية"
    }

# -----------------------------------------------------
# توليد كود (مشرف)
# -----------------------------------------------------
@app.get("/generate-code")
def generate_code(key: str, duration: str):
    if key != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden")

    if duration not in DURATIONS:
        raise HTTPException(status_code=400, detail="Invalid duration")

    code = generate_short_code()
    code_hash = hash_code(code)

    expires_at = datetime.utcnow() + DURATIONS[duration]
    VALID_CODES[code_hash] = expires_at

    return {
        "activation_code": code,
        "duration": duration,
        "expires_at": expires_at.isoformat() + "Z"
    }

# -----------------------------------------------------
# تفعيل كود
# -----------------------------------------------------
@app.post("/activate")
def activate(data: ActivateRequest):
    code = data.code.strip()
    if not code:
        raise HTTPException(status_code=400, detail="CODE_REQUIRED")

    code_hash = hash_code(code)
    expires_at = VALID_CODES.get(code_hash)

    if not expires_at:
        raise HTTPException(status_code=403, detail="INVALID_CODE")

    if expires_at < datetime.utcnow():
        VALID_CODES.pop(code_hash, None)
        raise HTTPException(status_code=403, detail="CODE_EXPIRED")

    token = create_jwt(expires_at)

    return {
        "token": token,
        "expires_at": expires_at.isoformat() + "Z"
    }

# -----------------------------------------------------
# تحقق من التوكن
# -----------------------------------------------------
@app.get("/verify")
def verify(user = Depends(get_current_user)):
    return {"status": "ok", "expires_at": user.get("exp")}

# -----------------------------------------------------
# الحصول على أنواع التقارير
# -----------------------------------------------------
@app.get("/reports/categories")
def get_report_categories():
    return {
        "categories": list(REPORTS_BY_CATEGORY.keys()),
        "reports_by_category": REPORTS_BY_CATEGORY,
        "all_reports": [report for category in REPORTS_BY_CATEGORY.values() for report in category]
    }

# -----------------------------------------------------
# البحث في التقارير
# -----------------------------------------------------
@app.get("/reports/search")
def search_reports(query: str):
    if not query or len(query.strip()) < 2:
        return {"results": []}
    
    search_term = query.strip().lower()
    results = []
    
    for category, reports in REPORTS_BY_CATEGORY.items():
        for report in reports:
            if search_term in report.lower():
                results.append({
                    "name": report,
                    "category": category
                })
    
    return {"results": results}

# -----------------------------------------------------
# الحصول على إدارات التعليم
# -----------------------------------------------------
@app.get("/education/administrations")
def get_education_administrations():
    return {
        "administrations": EDUCATION_ADMINISTRATIONS
    }

# -----------------------------------------------------
# الحصول على الأدوات التعليمية
# -----------------------------------------------------
@app.get("/education/tools")
def get_educational_tools():
    return {
        "tools": EDUCATIONAL_TOOLS
    }

# -----------------------------------------------------
# الذكاء الاصطناعي العام
# -----------------------------------------------------
@app.post("/generate")
def generate_ai_content(data: AskRequest, user = Depends(get_current_user)):
    try:
        model = pick_gemini_model()
        response = model.generate_content(data.prompt)
        return {"answer": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -----------------------------------------------------
# تحليل استجابة الذكاء الاصطناعي
# -----------------------------------------------------
def parse_ai_response(response_text: str, report_type: str = "") -> Dict[str, str]:
    """تحليل النص الذي يرجع من الذكاء الاصطناعي إلى حقول مع إثراء ذكي"""
    
    lines = response_text.split('\n')
    parsed = {
        "goal": "",
        "summary": "",
        "steps": "",
        "strategies": "",
        "strengths": "",
        "improve": "",
        "recomm": ""
    }
    
    current_field = None
    field_content = []
    
    for line in lines:
        line = line.strip()
        
        # البحث عن بداية حقل جديد
        if line.startswith('1.') or line.startswith('١.'):
            if current_field and field_content:
                parsed[current_field] = ' '.join(field_content).strip()
            current_field = "goal"
            field_content = [line[2:].strip()]
            
        elif line.startswith('2.') or line.startswith('٢.'):
            if current_field and field_content:
                parsed[current_field] = ' '.join(field_content).strip()
            current_field = "summary"
            field_content = [line[2:].strip()]
            
        elif line.startswith('3.') or line.startswith('٣.'):
            if current_field and field_content:
                parsed[current_field] = ' '.join(field_content).strip()
            current_field = "steps"
            field_content = [line[2:].strip()]
            
        elif line.startswith('4.') or line.startswith('٤.'):
            if current_field and field_content:
                parsed[current_field] = ' '.join(field_content).strip()
            current_field = "strategies"
            field_content = [line[2:].strip()]
            
        elif line.startswith('5.') or line.startswith('٥.'):
            if current_field and field_content:
                parsed[current_field] = ' '.join(field_content).strip()
            current_field = "strengths"
            field_content = [line[2:].strip()]
            
        elif line.startswith('6.') or line.startswith('٦.'):
            if current_field and field_content:
                parsed[current_field] = ' '.join(field_content).strip()
            current_field = "improve"
            field_content = [line[2:].strip()]
            
        elif line.startswith('7.') or line.startswith('٧.'):
            if current_field and field_content:
                parsed[current_field] = ' '.join(field_content).strip()
            current_field = "recomm"
            field_content = [line[2:].strip()]
            
        elif current_field and line and not line.startswith(('1','2','3','4','5','6','7','١','٢','٣','٤','٥','٦','٧')):
            field_content.append(line)
    
    # الحقل الأخير
    if current_field and field_content:
        parsed[current_field] = ' '.join(field_content).strip()
    
    # تطبيق الإثراء الذكي على كل حقل
    for key in parsed:
        if parsed[key]:  # إذا كان النص غير فارغ
            parsed[key] = enrich_and_enforce(parsed[key], 25, 30, report_type)
    
    # إذا فشل التحليل، نستخدم النصوص الافتراضية مع الإثراء
    if not any(parsed.values()):
        for key in parsed:
            if key in DEFAULT_REPORT_TEXTS:
                parsed[key] = enrich_and_enforce(
                    random.choice(DEFAULT_REPORT_TEXTS[key]), 
                    25, 35, 
                    report_type
                )
    
    return parsed

# -----------------------------------------------------
# توليد تقرير تعليمي متكامل
# -----------------------------------------------------
@app.post("/generate/report")
def generate_educational_report(data: ReportGenerateRequest, user = Depends(get_current_user)):
    if not data.reportType:
        raise HTTPException(status_code=400, detail="نوع التقرير مطلوب")
    
    try:
        # إنشاء البرومت المتخصص
        prompt = generate_educational_prompt(
            report_type=data.reportType,
            subject=data.subject,
            lesson=data.lesson,
            grade=data.grade,
            target=data.target,
            place=data.place,
            count=data.count
        )
        
        # استخدام الذكاء الاصطناعي
        model = pick_gemini_model()
        response = model.generate_content(prompt)
        
        # تحليل الاستجابة مع الإثراء الذكي
        ai_text = response.text
        parsed_fields = parse_ai_response(ai_text, data.reportType)
        
        return {
            "success": True,
            "report_type": data.reportType,
            "parsed_fields": parsed_fields,
            "raw_response": ai_text
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في توليد التقرير: {str(e)}")

# -----------------------------------------------------
# تحويل التاريخ الهجري إلى ميلادي
# -----------------------------------------------------
@app.get("/convert/hijri-to-gregorian")
async def convert_hijri_date(hijri_date: str):
    """تحويل التاريخ الهجري إلى ميلادي باستخدام API حقيقي"""
    try:
        # تحويل الأرقام العربية إلى إنجليزية
        arabic_to_english = {
            '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4',
            '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9'
        }
        
        clean_date = hijri_date
        for arabic, english in arabic_to_english.items():
            clean_date = clean_date.replace(arabic, english)
        
        date_parts = clean_date.split('/')
        if len(date_parts) != 3:
            raise ValueError("صيغة التاريخ غير صحيحة. استخدم: YYYY/MM/DD")
        
        year, month, day = date_parts
        
        # استخدام API متخصص لتحويل التاريخ
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(f'https://api.aladhan.com/v1/hToG?date={day}-{month}-{year}') as response:
                if response.status == 200:
                    data = await response.json()
                    if data['code'] == 200:
                        gregorian = data['data']['gregorian']
                        gregorian_date = f"{gregorian['day']}/{gregorian['month']['number']}/{gregorian['year']}"
                        
                        # تحويل الأرقام الإنجليزية إلى عربية للعرض
                        english_to_arabic = {v: k for k, v in arabic_to_english.items()}
                        arabic_gregorian = gregorian_date
                        for english, arabic in english_to_arabic.items():
                            arabic_gregorian = arabic_gregorian.replace(english, arabic)
                        
                        return {
                            "hijri_date": hijri_date,
                            "gregorian_date": arabic_gregorian,
                            "english_gregorian": gregorian_date
                        }
        
        return {
            "hijri_date": hijri_date,
            "gregorian_date": hijri_date,
            "note": "تعذر التحويل، تم استخدام التاريخ المدخل"
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"خطأ في تحويل التاريخ: {str(e)}")

# -----------------------------------------------------
# الحصول على التاريخ الحالي (هجري وميلادي)
# -----------------------------------------------------
@app.get("/dates/current")
async def get_current_dates():
    """الحصول على التاريخ الحالي هجري وميلادي"""
    try:
        import aiohttp
        from datetime import datetime
        
        today = datetime.now()
        day = today.day
        month = today.month
        year = today.year
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f'https://api.aladhan.com/v1/gToH?date={day}-{month}-{year}') as response:
                if response.status == 200:
                    data = await response.json()
                    if data['code'] == 200:
                        hijri = data['data']['hijri']
                        
                        # تحويل الأرقام الإنجليزية إلى عربية
                        english_to_arabic = {
                            '0': '٠', '1': '١', '2': '٢', '3': '٣', '4': '٤',
                            '5': '٥', '6': '٦', '7': '٧', '8': '٨', '9': '٩'
                        }
                        
                        hijri_day = str(hijri['day'])
                        hijri_month = str(hijri['month']['number'])
                        hijri_year = str(hijri['year'])
                        
                        for english, arabic in english_to_arabic.items():
                            hijri_day = hijri_day.replace(english, arabic)
                            hijri_month = hijri_month.replace(english, arabic)
                            hijri_year = hijri_year.replace(english, arabic)
                        
                        hijri_date = f"{hijri_year}/{hijri_month}/{hijri_day}"
                        gregorian_date = f"{day}/{month}/{year}"
                        
                        # تحويل التاريخ الميلادي إلى عربي
                        gregorian_arabic = gregorian_date
                        for english, arabic in english_to_arabic.items():
                            gregorian_arabic = gregorian_arabic.replace(english, arabic)
                        
                        return {
                            "hijri_date": hijri_date,
                            "gregorian_date": gregorian_arabic,
                            "english_hijri": f"{hijri['year']}/{hijri['month']['number']}/{hijri['day']}",
                            "english_gregorian": gregorian_date
                        }
        
        return {
            "hijri_date": "١٤٤٦/٠٦/٠١",
            "gregorian_date": "2024/12/01",
            "note": "تعذر الحصول على التواريخ الحقيقية"
        }
        
    except Exception as e:
        return {
            "hijri_date": "١٤٤٦/٠٦/٠١",
            "gregorian_date": "2024/12/01",
            "error": str(e)
        }

# -----------------------------------------------------
# حفظ بيانات المعلم
# -----------------------------------------------------
@app.post("/teacher/save")
def save_teacher_data(data: SaveTeacherRequest, user = Depends(get_current_user)):
    """حفظ بيانات المعلم على الخادم"""
    try:
        user_id = user.get("sub", "anonymous")
        
        if user_id not in USER_DATA:
            USER_DATA[user_id] = {}
        
        USER_DATA[user_id]["teacher_data"] = data.dict()
        USER_DATA[user_id]["last_saved"] = datetime.utcnow().isoformat()
        
        return {
            "success": True,
            "message": "تم حفظ بيانات المعلم بنجاح",
            "last_saved": USER_DATA[user_id]["last_saved"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في حفظ البيانات: {str(e)}")

# -----------------------------------------------------
# تحميل بيانات المعلم المحفوظة
# -----------------------------------------------------
@app.get("/teacher/load")
def load_teacher_data(user = Depends(get_current_user)):
    """تحميل بيانات المعلم المحفوظة"""
    try:
        user_id = user.get("sub", "anonymous")
        
        if user_id in USER_DATA and "teacher_data" in USER_DATA[user_id]:
            return {
                "success": True,
                "data": USER_DATA[user_id]["teacher_data"],
                "last_saved": USER_DATA[user_id].get("last_saved")
            }
        else:
            return {
                "success": False,
                "message": "لا توجد بيانات محفوظة",
                "data": {}
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في تحميل البيانات: {str(e)}")

# -----------------------------------------------------
# إرسال طلب دعم فني
# -----------------------------------------------------
@app.post("/support/send")
async def send_support_request(data: SupportRequest, background_tasks: BackgroundTasks):
    """إرسال طلب الدعم الفني"""
    try:
        # يمكن هنا إرسال الإيميل أو حفظ الطلب في قاعدة بيانات
        support_data = {
            "name": data.name,
            "phone": data.phone,
            "issue": data.issue,
            "timestamp": datetime.utcnow().isoformat(),
            "ip": "127.0.0.1"  # في الواقع سيتم الحصول على IP المستخدم
        }
        
        # حفظ الطلب مؤقتاً (يمكن استخدام قاعدة بيانات)
        if "support_requests" not in USER_DATA:
            USER_DATA["support_requests"] = []
        
        USER_DATA["support_requests"].append(support_data)
        
        # إعداد رابط الواتساب
        whatsapp_message = f"طلب دعم فني - أداة إصدار التقارير\n\nالاسم: {data.name}\nرقم التواصل: {data.phone}\n\nتفاصيل المشكلة:\n{data.issue}\n\n---\nتم الإرسال في: {support_data['timestamp']}"
        whatsapp_url = f"https://wa.me/966597077245?text={whatsapp_message}"
        
        # إعداد رابط الإيميل
        email_subject = "طلب دعم فني - أداة إصدار التقارير"
        email_body = f"الاسم: {data.name}\nرقم التواصل: {data.phone}\n\nتفاصيل المشكلة:\n{data.issue}\n\n---\nتم الإرسال في: {support_data['timestamp']}"
        email_url = f"mailto:iFahadenglish@gmail.com?subject={email_subject}&body={email_body}"
        
        return {
            "success": True,
            "message": "تم إرسال طلب الدعم بنجاح",
            "whatsapp_url": whatsapp_url,
            "email_url": email_url,
            "support_data": support_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في إرسال طلب الدعم: {str(e)}")

# -----------------------------------------------------
# توليد نسخة PDF من التقرير (محاكاة)
# -----------------------------------------------------
@app.post("/generate/pdf")
async def generate_pdf_report(data: Dict[str, Any], user = Depends(get_current_user)):
    """توليد نسخة PDF من التقرير"""
    try:
        # في الواقع يمكن استخدام مكتبة مثل ReportLab أو WeasyPrint
        # هنا نرجع بيانات التقرير فقط
        
        report_data = {
            "report_type": data.get("report_type", "تقرير"),
            "education": data.get("education", ""),
            "school": data.get("school", ""),
            "teacher": data.get("teacher", ""),
            "grade": data.get("grade", ""),
            "subject": data.get("subject", ""),
            "lesson": data.get("lesson", ""),
            "goal": data.get("goal", ""),
            "summary": data.get("summary", ""),
            "steps": data.get("steps", ""),
            "strategies": data.get("strategies", ""),
            "strengths": data.get("strengths", ""),
            "improve": data.get("improve", ""),
            "recomm": data.get("recomm", ""),
            "tools": data.get("tools", []),
            "hijri_date": data.get("hijri_date", ""),
            "gregorian_date": data.get("gregorian_date", ""),
            "generated_at": datetime.utcnow().isoformat()
        }
        
        # محاكاة اسم الملف
        report_name = data.get("report_type", "تقرير").replace("/", "-").replace("\\", "-")
        file_name = f"{report_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        return {
            "success": True,
            "message": "تم إنشاء التقرير بنجاح",
            "file_name": file_name,
            "report_data": report_data,
            "download_url": f"/reports/download/{file_name}",  # محاكاة رابط التحميل
            "preview_url": f"/reports/preview/{file_name}"    # محاكاة رابط المعاينة
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في إنشاء PDF: {str(e)}")

# -----------------------------------------------------
# استشارة تربوية (إضافية)
# -----------------------------------------------------
@app.post("/consult/educational")
def educational_consultation(data: AskRequest, user = Depends(get_current_user)):
    """استشارة تربوية مع خبير تعليمي"""
    consult_prompt = f"""أنت مستشار تربوي محترف مع خبرة 20 سنة في المجال التعليمي.
الاستشارة المطلوبة: {data.prompt}

قدم إجابة:
1. تحليل الموقف
2. الحلول المقترحة (3 حلول على الأقل)
3. خطوات التنفيذ
4. مؤشرات النجاح
5. نصائح احترافية

اجعل الإجابة عملية وقابلة للتطبيق في البيئة التعليمية السعودية."""
    
    try:
        model = pick_gemini_model()
        response = model.generate_content(consult_prompt)
        return {
            "consultation": response.text,
            "advisor": "خبير تربوي - نظام ناصر التعليمي"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -----------------------------------------------------
# الحصول على معلومات النظام
# -----------------------------------------------------
@app.get("/system/info")
def get_system_info():
    """الحصول على معلومات النظام والنسخ"""
    return {
        "system_name": "ناصر - نظام إصدار التقارير التعليمية",
        "version": "2.6.0",
        "api_version": "1.0",
        "developer": "فهد الخالدي",
        "support_email": "iFahadenglish@gmail.com",
        "support_phone": "+966597077245",
        "features": [
            "توليد التقارير التعليمية الذكية",
            "تحويل التاريخ الهجري/الميلادي",
            "حفظ بيانات المعلم",
            "الدعم الفني المتكامل",
            "تصدير إلى PDF",
            "مشاركة عبر واتساب"
        ],
        "last_updated": "2026-02-07"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)