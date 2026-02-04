# main.py
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import os
import itertools
import google.generativeai as genai
from database import init_db, get_connection
from create_key import create_key
from security import activation_required

try:
    init_db()
except Exception as e:
    print("DB INIT ERROR:", e)

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Req(BaseModel):
    prompt: str
    model: str | None = "gemini-2.5-flash-lite"
    reportData: dict | None = None

class GenerateKeyReq(BaseModel):
    expires_at: str | None = None
    usage_limit: int | None = None

class FillAIRequest(BaseModel):
    reportType: str
    subject: str | None = None
    lesson: str | None = None
    grade: str | None = None
    target: str | None = None
    place: str | None = None
    count: str | None = None
    category: str | None = None
    manualTitle: str | None = None

api_keys = [
    os.getenv("GEMINI_API_KEY_1"),
    os.getenv("GEMINI_API_KEY_2"),
    os.getenv("GEMINI_API_KEY_3"),
    os.getenv("GEMINI_API_KEY_4"),
    os.getenv("GEMINI_API_KEY_5"),
    os.getenv("GEMINI_API_KEY_6"),
    os.getenv("GEMINI_API_KEY_7"),
]
api_keys = [k for k in api_keys if k]

key_cycle = itertools.cycle(api_keys) if api_keys else None

def get_api_key():
    if not key_cycle:
        raise HTTPException(status_code=500, detail="No Gemini API key configured")
    return next(key_cycle)

def admin_auth(x_admin_token: str = Header(...)):
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

# جميع التقارير مصنفة - تم نقلها من Frontend
all_reports_by_category = {
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
    "تقارير توظيف التكنولوجيا": [
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
        "تقرير تحديث الخطط الدراسية",
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

# إنشاء قائمة بجميع التقارير
all_reports = []
for category, reports in all_reports_by_category.items():
    for report in reports:
        all_reports.append({"name": report, "category": category})

# البرومبت المهني - تم نقله من Frontend
PROFESSIONAL_PROMPT = """أنت خبير تربوي تعليمي محترف تمتلك خبرة ميدانية واسعة في التعليم العام.  
اعتمد منظورًا تربويًا مهنيًا احترافيًا يركّز على تحسين جودة التعليم، ودعم المعلم، وتعزيز بيئة التعلّم، وخدمة القيادة المدرسية.  

التقرير المطلوب: "{report_type}"
{subject_text}{lesson_text}{grade_text}{target_text}{place_text}{count_text}

**توجيهات مهنية:**
- كن موضوعيًا ومتزنًا وبنّاءً  
- قدّم الملاحظات بصيغة تطويرية غير نقدية  
- راعِ واقع الميدان التعليمي وسياق المدرسة  
- اربط بين المعلم والطالب والمنهج والبيئة الصفية والقيادة المدرسية  
- ركّز على جودة التعليم وأثر الممارسات على تعلم الطلاب  
- التزم بلغة عربية فصيحة سليمة وخالية من الأخطاء  

**شروط المحتوى:**
اكتب محتوى كل حقل بصيغة تقريرية مهنية وكأنه صادر عن المعلم.
لا تكتب أبداً عنوان الحقل داخل المحتوى ولا تعِد صياغته بصيغة مباشرة (مثل: الهدف التربوي هو، النبذة المختصرة).
يجب أن يحتوي كل حقل على ما يقارب 25 كلمة.
ابدأ بالمضمون مباشرة دون تمهيد أو عبارات إنشائية.
يمكن الاستفادة من معنى العنوان أو أحد مفاهيمه بشكل غير مباشر فقط عند الحاجة وبما يخدم الفكرة دون تكرار أو حشو.
احرص على وجود ترابط منطقي بين الأهداف، النبذة المختصرة، الاستراتيجيات، إجراءات التنفيذ، نقاط القوة، نقاط التحسين، والتوصيات.
اربط المحتوى بالمادة الدراسية وعنوان الدرس إن وُجد، وكذلك بمكان التنفيذ، بأسلوب مهني متوازن يجمع بين الإشارة المباشرة وغير المباشرة دون تكلف.
اجعل الهدف النهائي للمحتوى تحسين الممارسة التعليمية ودعم التطوير المهني المستدام.
راعِ الوضوح والترابط، واجعل كل جملة تضيف قيمة تعليمية فعلية.

**الحقول المطلوبة:**
1. الهدف التربوي
2. نبذة مختصرة  
3. إجراءات التنفيذ
4. الاستراتيجيات
5. نقاط القوة
6. نقاط التحسين
7. التوصيات

يرجى تقديم الإجابة باللغة العربية الفصحى، وتنظيمها بحيث يكون كل حقل في سطر منفصل يبدأ برقمه فقط دون ذكر العنوان."""

@app.get("/")
def root():
    return {"status": "running"}

@app.get("/health")
def health(_: None = Depends(activation_required)):
    return {"status": "ok"}

@app.get("/reports/categories")
def get_categories(_: None = Depends(activation_required)):
    """الحصول على جميع تصنيفات التقارير"""
    return {"categories": list(all_reports_by_category.keys())}

@app.get("/reports/all")
def get_all_reports(_: None = Depends(activation_required)):
    """الحصول على جميع التقارير"""
    return {"reports": all_reports}

@app.get("/reports/category/{category_name}")
def get_reports_by_category(category_name: str, _: None = Depends(activation_required)):
    """الحصول على التقارير حسب التصنيف"""
    if category_name not in all_reports_by_category:
        raise HTTPException(status_code=404, detail="التصنيف غير موجود")
    return {"category": category_name, "reports": all_reports_by_category[category_name]}

@app.get("/reports/search/{search_term}")
def search_reports(search_term: str, _: None = Depends(activation_required)):
    """بحث في التقارير"""
    search_term_lower = search_term.lower()
    results = []
    
    for report in all_reports:
        if search_term_lower in report["name"].lower():
            results.append(report)
    
    return {"results": results}

@app.post("/ask")
def ask(req: Req, _: None = Depends(activation_required)):
    """الدالة الأصلية للذكاء الاصطناعي"""
    try:
        genai.configure(api_key=get_api_key())
        model_name = req.model if req.model else "gemini-2.5-flash-lite"
        model = genai.GenerativeModel(f"models/{model_name}")
        response = model.generate_content(req.prompt)
        return {"answer": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في الذكاء الاصطناعي: {str(e)}")

@app.post("/fill-with-ai")
def fill_with_ai(req: FillAIRequest, _: None = Depends(activation_required)):
    """تعبئة التقرير باستخدام الذكاء الاصطناعي"""
    try:
        # التحقق من وجود نوع التقرير
        if not req.reportType or req.reportType == "تقرير":
            raise HTTPException(status_code=400, detail="الرجاء تحديد نوع التقرير")
        
        # بناء النص الإضافي
        additional_info = ""
        if req.subject:
            additional_info += f"المادة: {req.subject}\n"
        if req.lesson:
            additional_info += f"الدرس: {req.lesson}\n"
        if req.grade:
            additional_info += f"الصف: {req.grade}\n"
        if req.target:
            additional_info += f"المستهدفون: {req.target}\n"
        if req.place:
            additional_info += f"مكان التنفيذ: {req.place}\n"
        if req.count:
            additional_info += f"عدد الحضور: {req.count}\n"
        
        # بناء البرومبت الكامل
        full_prompt = PROFESSIONAL_PROMPT.format(
            report_type=req.reportType,
            subject_text=f"المادة: {req.subject}\n" if req.subject else "",
            lesson_text=f"الدرس: {req.lesson}\n" if req.lesson else "",
            grade_text=f"الصف: {req.grade}\n" if req.grade else "",
            target_text=f"المستهدفون: {req.target}\n" if req.target else "",
            place_text=f"مكان التنفيذ: {req.place}\n" if req.place else "",
            count_text=f"عدد الحضور: {req.count}" if req.count else ""
        )
        
        # استدعاء الذكاء الاصطناعي
        genai.configure(api_key=get_api_key())
        model = genai.GenerativeModel("models/gemini-2.5-flash-lite")
        response = model.generate_content(full_prompt)
        
        # تحليل الاستجابة
        ai_response = response.text
        parsed_fields = parse_ai_response_professional(ai_response)
        
        return {
            "success": True,
            "fields": parsed_fields,
            "raw_response": ai_response
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في تعبئة التقرير: {str(e)}")

def parse_ai_response_professional(response: str) -> dict:
    """تحليل استجابة الذكاء الاصطناعي المهنية"""
    lines = response.split('\n')
    parsed = {
        "goal": "",
        "summary": "",
        "steps": "",
        "strategies": "",
        "strengths": "",
        "improve": "",
        "recomm": ""
    }
    
    field_mapping = {
        '1': 'goal',
        '2': 'summary',
        '3': 'steps',
        '4': 'strategies',
        '5': 'strengths',
        '6': 'improve',
        '7': 'recomm'
    }
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # البحث عن نمط "رقم. محتوى"
        for i in range(1, 8):
            if line.startswith(f"{i}.") or line.startswith(f"{i}-"):
                content = line[2:].strip()
                # إزالة أي عناوين محتملة
                content = remove_field_titles(content)
                # ضمان عدد الكلمات
                content = ensure_word_count(content, 25)
                # إضافة لمسة مهنية
                content = add_professional_touch(content, field_mapping[str(i)])
                parsed[field_mapping[str(i)]] = content
                break
    
    # إذا لم يتم العثور على الحقول بالتنسيق المتوقع
    if not any(parsed.values()):
        parsed = fallback_professional_ai_parsing(response)
    
    return parsed

def remove_field_titles(content: str) -> str:
    """إزالة عناوين الحقول من النص"""
    field_titles = [
        'الهدف التربوي', 'الهدف',
        'نبذة مختصرة', 'نبذة',
        'إجراءات التنفيذ', 'إجراءات',
        'الاستراتيجيات', 'الاستراتيجيات',
        'نقاط القوة', 'نقاط',
        'نقاط التحسين', 'تحسين',
        'التوصيات', 'التوصيات',
        'هو:', 'تشمل:', 'يشمل:', 'يتضمن:', 'يتمثل في'
    ]
    
    cleaned = content
    for title in field_titles:
        pattern = f"^{title}[:\\.\\-]?\\s*"
        import re
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
    
    return cleaned.strip()

def ensure_word_count(content: str, target_words: int) -> str:
    """ضمان عدد الكلمات المطلوب"""
    words = content.split()
    if len(words) >= target_words - 5 and len(words) <= target_words + 5:
        return content
    
    if len(words) < target_words - 5:
        professional_phrases = [
            'مع التركيز على تحقيق أهداف التعلم وتنمية المهارات الأساسية',
            'بما يسهم في رفع مستوى التحصيل الدراسي وتحسين المخرجات التعليمية',
            'وذلك لتحقيق التكامل بين الجوانب المعرفية والمهارية والوجدانية',
            'مع مراعاة الفروق الفردية وتنويع أساليب التدريس لتناسب جميع الطلاب',
            'لضمان تحقيق رؤية التعليم وتطوير العملية التعليمية بصورة شاملة',
            'مع الاستفادة من أفضل الممارسات التربوية والتقنيات التعليمية الحديثة',
            'بما يعزز من دور المعلم كميسر للتعلم وموجه للطالب نحو التميز'
        ]
        
        extended = content
        while len(extended.split()) < target_words:
            import random
            extended += ' ' + random.choice(professional_phrases)
        
        extended_words = extended.split()
        if len(extended_words) > target_words + 5:
            return ' '.join(extended_words[:target_words])
        
        return extended
    
    # إذا كانت الكلمات أكثر من المطلوب
    return ' '.join(words[:target_words])

def add_professional_touch(content: str, field_id: str) -> str:
    """إضافة لمسة مهنية للمحتوى"""
    words = content.split()
    if len(words) >= 20:
        return content
    
    professional_additions = {
        'goal': ' بما يعزز من جودة التعليم ويدعم تحقيق رؤية المدرسة التعليمية',
        'summary': ' مع التركيز على الأثر الإيجابي في تحسين الممارسات التعليمية',
        'steps': ' ومراعاة الجوانب التربوية والنفسية للطلاب في جميع المراحل',
        'strategies': ' بما يناسب البيئة الصفية ويحقق أقصى استفادة تعليمية',
        'strengths': ' مما يسهم في تحقيق بيئة تعلم إيجابية ومنتجة',
        'improve': ' مع وضع خطط تطويرية قابلة للتنفيذ في الفصول القادمة',
        'recomm': ' بما يدعم التطوير المهني المستمر ويعزز جودة التعليم'
    }
    
    if field_id in professional_additions:
        return content + professional_additions[field_id]
    
    return content

def fallback_professional_ai_parsing(response: str) -> dict:
    """نهج بديل لتحليل الاستجابة المهنية"""
    import re
    sentences = re.split(r'[\.\n]', response)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
    
    # تصفية الجمل التي تحتوي على كلمات شائعة للحقول
    filtered = []
    for s in sentences:
        if not any(word in s.lower() for word in ['الحقل', 'المطلوب', 'يجب', 'يرجى', 'الرجاء']):
            filtered.append(s)
    
    fields = ['goal', 'summary', 'steps', 'strategies', 'strengths', 'improve', 'recomm']
    parsed = {field: "" for field in fields}
    
    for i, field in enumerate(fields):
        if i < len(filtered):
            content = filtered[i]
            content = remove_field_titles(content)
            content = ensure_word_count(content, 25)
            content = add_professional_touch(content, field)
            parsed[field] = content
    
    return parsed

@app.post("/admin/generate", dependencies=[Depends(admin_auth)])
def admin_generate(req: GenerateKeyReq):
    return {"code": create_key(req.expires_at, req.usage_limit)}

@app.get("/admin/codes", dependencies=[Depends(admin_auth)])
def admin_codes():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, code, is_active, usage_count FROM activation_codes")
    rows = cur.fetchall()
    conn.close()
    return [
        {"id": r[0], "code": r[1], "active": bool(r[2]), "usage": r[3]}
        for r in rows
    ]

@app.put("/admin/code/{code_id}/toggle", dependencies=[Depends(admin_auth)])
def admin_toggle(code_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE activation_codes SET is_active = CASE WHEN is_active=1 THEN 0 ELSE 1 END WHERE id=?",
        (code_id,)
    )
    conn.commit()
    conn.close()
    return {"status": "ok"}

@app.delete("/admin/code/{code_id}", dependencies=[Depends(admin_auth)])
def admin_delete(code_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM activation_codes WHERE id=?", (code_id,))
    conn.commit()
    conn.close()
    return {"status": "deleted"}

@app.get("/admin", response_class=HTMLResponse)
def admin_page():
    return "<h3>Admin Panel Ready</h3>"

@app.get("/tools/list")
def get_tools_list(_: None = Depends(activation_required)):
    """الحصول على قائمة الأدوات التعليمية"""
    tools = [
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
    return {"tools": tools}
