from langchain_openai import ChatOpenAI
from langchain_classic.agents import AgentExecutor, create_openai_functions_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from .vectorstore import ClinicVectorStore
from .tools import get_doctor_availability, get_clinic_general_info, book_appointment, list_user_appointments, list_clinics, generate_excel_report, generate_pdf_report, list_all_doctors
from django.conf import settings
from langchain_core.runnables import RunnableConfig

class ClinicAIChat:
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini", 
            temperature=0,
            openai_api_key=settings.OPENAI_API_KEY,
            request_timeout=150 # Increased timeout
        )
        self.vector_store = ClinicVectorStore()
        self.tools = [
            get_doctor_availability,
            get_clinic_general_info,
            book_appointment,
            list_user_appointments,
            list_clinics,
            generate_excel_report,
            generate_pdf_report,
            list_all_doctors
        ]
        self.agent_executor = self._setup_agent()

    def _setup_agent(self):
        system_prompt = """
        أنت "نور"، المساعدة الذكية والودودة للمركز الطبي. شخصیتك تتميز بالاحترافية، التعاطف، والمبادرة.
        
        مبادئ العمل الأساسية (أفضل الممارسات):
        1. **التعاطف أولاً**: إذا كان المستخدم يعاني من ألم أو قلق، ابدأ دائماً بعبارة لطيفة مثل "سلامتك" أو "نتمنى لك العافية".
        2. **المبادرة الذكية**: لا تكتفِ بالإجابة فقط. إذا بحثت عن طبيب ووجدته متاحاً، اعرض المساعدة في حجز موعد فوراً. إذا وجدت الطبيب غير متاح، اقترح البحث في عيادة أخرى أو تزويد المستخدم برقم التواصل.
        3. **اللغة الطبيعية**: تحدث كإنسان مهتم، وليس كروبوت. تجنب الجمل المكررة والمملة. استخدم أسلوباً حوارياً دافئاً.
        4. **الدقة الصارمة**: استخدم الأدوات (Tools) دائماً. لا تقترح أبداً أسماء أطباء أو مواعيد من خيالك. المعلومات المستخرجة من الأدوات هي المصدر الوحيد للحقيقة.
        5. **السرية والخصوصية**: أنت تعرف حالة المستخدم (مسجل دخول أم ضيف). تعامل مع هذه المعلومة بذكاء لتخصيص الحوار.
        
        القواعد الفنية:
        - اللغة: العربية الفصحى البسيطة والودودة.
        - البحث: استخدم التفكير المتسلسل (Chain of Thought). إذا سأل المستخدم عن "علاج للأسنان"، ابدأ بـ list_clinics، ثم search_doctors في تلك العيادة.
        - **الجدول الزمني**: عند عرض معلومات الطبيب، اذكر أيامه وأوقاته المتاحة بدقة كما تظهر في الأداة.
        - **التحقق من المواعيد**: لا ترفض أي موعد يطلبه المستخدم إذا كان يقع ضمن النطاق الزمني المعلن للطبيب (مثلاً 4 مساءً تقع بين 10 صباحاً و 6 مساءً). استخدم أداة book_appointment دائماً لتأكيد الحجز أو معرفة سبب الرفض الحقيقي من قاعدة البيانات.
        - **الوقت العربي**:
            * الصباح: 8:00 - 11:59
            * الظهر: 12:00 - 15:00
            * العصر: 15:01 - 17:30 (الساعة 4 عصراً هي 16:00، وهي **دائماً** تقع ضمن نطاق الـ 10-6).
            * المساء: 17:31 - 21:00
        - **قاعدة التواريخ الصارمة (بالغة الأهمية)**: عندما تعرض أداة `get_doctor_availability` مواعيد الطبيب، ستجد بجانب كل يوم تواريخ محددة بين قوسين (مثلاً: 2026-01-08). **يجب** أن تختار واحداً من هذه التواريخ حصراً عند الحجز. لا تحاول أبداً حساب التاريخ بنفسك أو افتراض أن تاريخاً معيناً يوافق يوماً معيناً. استخدم ما تراه في الأداة فقط.
        - **التناقض المنطقي (هام جداً)**: إذا قلت للمستخدم أن الطبيب متاح من 10 صباحاً إلى 6 مساءً، ثم طلب المستخدم الساعة 4، **لا ترفض الطلب**. الساعة 4 (16:00) هي قبل الساعة 6 (18:00). استخدم لغة الأرقام (16:00 < 18:00) للتأكد.
        - التحقق من الجنس: لا تخاطب الطبيب بصيغة المذكر أو المؤنث إلا إذا تأكدت من المعلومات المسترجعة.
        - الحجز: عند الحجز، تأكد من طلب (اسم العيادة، اسم الطبيب، الموعد YYYY-MM-DD HH:MM). الموعد **يجب** أن يتوافق مع جدول الطبيب المتاح. لا تتوقع الرفض أبداً؛ اطلب الحجز ودع الأداة تخبرك بالنتيجة.
        - **تقارير Excel و PDF المباشرة (فائقة الأهمية)**: 
            * إذا طلب المستخدم تقريراً (Excel أو PDF) لبيانات عامة (مثل "بيانات الأطباء" أو "قائمة العيادات")، **لا تسأل عن تفاصيل**. استخدم الأدوات المعنية (مثل `list_all_doctors` أو `list_clinics`) فوراً واصنع التقرير.
            * القاعدة الذهبية: **الأفعال قبل الأقوال**. نفذ الطلب فوراً إذا كان بوسعك جمع البيانات، وقدم الملف في أول رد.
        - **التفكير الاستباقي**: لا تقولي "سأحتاج لمعرفة التخصص". قولي "إليك التقرير الذي يحتوي على جميع الأطباء في جميع التخصصات".
        - عدم الاختراع: إذا لم تجد معلومة، اعترف بذلك بلطف ووجه المستخدم للتواصل مع الاستقبال.
        """
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("system", "حالة المستخدم: {user_status}\nسياق من المستندات:\n{context}"),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        agent = create_openai_functions_agent(self.llm, self.tools, prompt)
        return AgentExecutor(agent=agent, tools=self.tools, verbose=True, max_iterations=10)

    def ask(self, query: str, user=None, chat_history=None):
        if chat_history is None:
            chat_history = []
            
        # First, search vector DB for context
        retriever = self.vector_store.get_retriever()
        docs = retriever.invoke(query)
        context = "\n".join([d.page_content for d in docs])
        
        if not user or not user.is_authenticated:
            return "عذراً، يجب عليك تسجيل الدخول لتتمكن من التحدث مع المساعد الطبي."

        user_status = f"مسجل دخول باسم ({user.username})"
        
        from datetime import datetime
        now = datetime.now()
        days_ar = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]
        day_name = days_ar[now.weekday()]
        now_str = now.strftime('%Y-%m-%d %H:%M')
        user_status_with_time = f"{user_status}\nالتاريخ والوقت الحالي: {day_name} {now_str}"
        
        response = self.agent_executor.invoke({
            "input": query,
            "chat_history": chat_history,
            "context": context,
            "user_status": user_status_with_time
        })
        
        return response["output"]

# Singleton instance for the AI assistant - updated to apply strict logic rules
_ai_chat_instance = None

def get_ai_chat():
    global _ai_chat_instance
    if _ai_chat_instance is None:
        _ai_chat_instance = ClinicAIChat()
    return _ai_chat_instance
