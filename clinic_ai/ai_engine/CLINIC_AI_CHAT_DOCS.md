# ClinicAIChat Technical Documentation

## Overview
The `ClinicAIChat` class serves as the core engine for the "Noor" AI medical assistant. It integrates **LangChain**, **OpenAI GPT-4o-mini**, and a **RAG (Retrieval-Augmented Generation)** architecture to provide authenticated, context-aware responses to user queries. The system handles appointment bookings, doctor availability checks, and general clinic inquiries using a set of defined tools.

## Architecture & Dependencies
The implementation relies on the following key libraries:
- **LangChain**: For agent orchestration (`AgentExecutor`, `create_openai_functions_agent`).
- **LangChain OpenAI**: For the LLM interface (`ChatOpenAI`).
- **Django**: For configuration (`settings`) and user authentication context.
- **Vector Store**: A custom `ClinicVectorStore` for context retrieval.

## Class: `ClinicAIChat`

### Initialization (`__init__`)
Initializes the AI engine with the following components:
1.  **LLM**: Uses `gpt-4o-mini` with `temperature=0` for deterministic outputs.
    -   *Timeout*: Set to 120 seconds to handle complex tool executions.
2.  **Vector Store**: Instance of `ClinicVectorStore` for RAG operations.
3.  **Tools**: A comprehensive list of functions available to the agent:
    -   `get_doctor_availability`: Checks doctor schedules.
    -   `get_clinic_general_info`: Retrieves static clinic data.
    -   `book_appointment`: Handles logic for booking.
    -   `list_user_appointments`: Fetches user's history.
    -   `list_clinics`: Enumerates available clinics.
    -   `generate_excel_report`, `generate_pdf_report`: Report generation.
    -   `list_all_doctors`: Directory of all physicians.
4.  **Agent Executor**: Sets up the agent runtime via `_setup_agent`.

### Method: `_setup_agent`
Configures the internal logic and persona of the agent.

#### System Prompt Strategy
The system prompt defines the persona "Noor" with strict operational protocols:
-   **Persona**: Professional, empathetic, proactive.
-   **Principles**:
    -   *Empathy*: Starts responses with health wishes if pain/anxiety is detected.
    -   *Accuracy*: Strictly adheres to tool outputs; strictly forbids hallucinating doctors or dates.
    -   *Date/Time Logic*: Handles Arabic time periods (Morning, Afternoon, Evening) and asserts strict date matching with `get_doctor_availability` outputs.
-   **Tool Usage Rules**: enforces verification of inputs (e.g., finding a valid date from the availability list) before calling `book_appointment`.

#### Agent Logic
-   **Prompt Construction**: Combines the system prompt, user status, retrieved context, chat history, and the current user input into a `ChatPromptTemplate`.
-   **Creation**: Uses `create_openai_functions_agent` to bind the LLM with the defined tools.
-   **Executor**: Returns an `AgentExecutor` with `verbose=True` and `max_iterations=10` to prevent infinite loops.

### Method: `ask`
The primary public interface for processing user queries.

**Signature**:
```python
def ask(self, query: str, user=None, chat_history=None) -> str
```

**Workflow**:
1.  **History Handling**: Initializes empty list if `chat_history` is None.
2.  **RAG Context Retrieval**:
    -   Uses `self.vector_store.get_retriever()` to find relevant documents.
    -   Aggregates document content into a `context` string.
3.  **Authentication Guard**: Checks `user.is_authenticated`. Returns a standard error message if not logged in.
4.  **Context Injection**:
    -   Constructs `user_status` indicating the username.
    -   Injects **Current Date & Time** (in Arabic format) to ensure the model understands relative time references (e.g., "appointment for tomorrow").
5.  **Execution**:
    -   Invokes the `agent_executor` with the input, history, context, and status.
    -   Returns the `output` string from the agent's response.

## Singleton Implementation

The module implements the Singleton pattern to ensure only one instance of `ClinicAIChat` is initialized during the application lifecycle, conserving resources (LLM connections, Vector Store initialization).

```python
_ai_chat_instance = None

def get_ai_chat():
    global _ai_chat_instance
    if _ai_chat_instance is None:
        _ai_chat_instance = ClinicAIChat()
    return _ai_chat_instance
```
