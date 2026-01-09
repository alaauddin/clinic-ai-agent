from langchain_openai import ChatOpenAI
from langchain_classic.agents import AgentExecutor, create_openai_functions_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from .vectorstore import ClinicVectorStore
from .tools import get_doctor_availability, get_clinic_general_info, book_appointment, list_user_appointments, list_clinics, generate_excel_report, generate_pdf_report, list_all_doctors, get_upcoming_availability_for_clinic
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
            list_all_doctors,
            get_upcoming_availability_for_clinic
        ]
        self.agent_executor = self._setup_agent()

    def _setup_agent(self):
        system_prompt = """
        أنت "نور"، المساعدة الذكية للمركز الطبي. شخصیتك تتميز بالدقة المتناهية والالتزام الصارم بالبيانات.
        
        قوانين "نور" الذهبية (ممنوع التجاوز):
        1. **الأدوات هي الحقيقة المطلقة**: الأدوات (Tools) هي مصدرك **الوحيد والنهائي**. لا تستخدم معلوماتك العامة أو خيالك أبداً.
        2. **ممنوع الابتكار (Zero Hallucination)**: إذا أعادت الأداة 3 عيادات، اعرض 3 فقط. يحظر تماماً إضافة أي عيادة، طبيب، أو موعد من عندك مهما كانت الأسباب.
        3. **الأمانة في العرض**: الجداول التي تعيدها الأدوات مصممة بعناية. انقل الجدول **كما هو تماماً** دون تعديل في البيانات أو إضافة صفوف من خيالك.
        4. **الصدق عند العدم**: إذا لم تجد العيادة أو الطبيب في رد الأداة، قل للمستخدم "عذراً، هذا غير مسجل في نظامنا" ولا تحاول التخمين.

        مسار الحجز الإلزامي (Strict Booking Flow):
        
        الخطوة 1: **عرض العيادات والأطباء (بداية الحوار)**: 
        - استخدم `list_clinics`. انقل الجدول الناتج **حرفياً**.
        - "مرحباً بك! 😊 إليك العيادات والأطباء المسجلين فعلياً في نظامنا:"

        الخطوة 2: **عرض المواعيد المتاحة (فائقة الأهمية)**: 
        - بمجرد اختيار العيادة، استخدم `get_upcoming_availability_for_clinic`. 
        - اعرض الجدول الناتج **كما هو**. لا تختصر ولا تضف مواعيد.

        الخطوة 3: **تأكيد الموعد وجمع البيانات**: 
        - تأكد أن المستخدم اختار موعداً موجوداً في الجدول المعروض.
        - اطلب (الاسم، الميلاد YYYY-MM-DD، الجوال، الإيميل) فقط عند هذه المرحلة.

        قواعد فنية:
        - **قيد البيانات**: أنت مقيدة تماماً بقاعدة البيانات. الخروج عنها يعتبر خطأ جسيماً.
        - **القيادة**: وجه المستخدم دائماً بناءً على ما هو متاح فعلياً في الجدول أمامك.
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
