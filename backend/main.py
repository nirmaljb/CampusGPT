from dotenv import load_dotenv
load_dotenv()

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from langgraph.graph import MessagesState, StateGraph, START, END
from langchain.messages import SystemMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_ollama import ChatOllama
from langchain.tools import tool
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver


class State(MessagesState):
    messages: list[str]

model = ChatOllama(
    model="llama3.2"
)
memory = MemorySaver()
embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
vector_db = QdrantVectorStore.from_existing_collection(
    url="http://localhost:6333",
    collection_name="PONDICHERRY_UNIVERSITY_INFO",
    embedding=embeddings
)

@tool
def retrieve_docs(query: str) -> str:
    """Search internal database for SPECIFIC information about Pondicherry University.
    
    Use this tool ONLY for queries about:
    - University courses, programs, admissions
    - Faculty, departments, research
    - Funding, grants, finances
    - Facilities, campus information
    - Policies, procedures, academics
    
    DO NOT use for: greetings, general conversation, or vague queries.
    """
    search_result = vector_db.similarity_search(query=query, k=3)

    print("Search result: ", search_result)

    relevant_docs = [(doc,score) for doc, score in search_result if score < 0.7]
    
    if not relevant_docs:
        return "No relevant information found in the database."
    
    context = "\n\n".join([f"{result.page_content}\n" for result, _ in relevant_docs])

    return context

model_with_tools = model.bind_tools([retrieve_docs])


def should_continue(state: State):
    """Determine if we should continue to tools or end."""
    print("Continue State :", state)
    last_message = state['messages'][-1]
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"
    return END

def call_model(state: State):
    SYSTEM_PROMPT = """You're an expert consultant for Pondicherry University.
        **TOOL USAGE GUIDELINES:**
        - Use 'retrieve_docs' ONLY for specific questions about Pondicherry University (courses, admissions, faculty, funding, facilities, etc.)
        - DO NOT use tools for: greetings, casual conversation, general questions, or chitchat
        - For simple greetings like "hi", "hello", "how are you", respond naturally WITHOUT using tools

        **Your Role:**
        Answer questions about Pondicherry University using the retrieve_docs tool when needed.
    """
    print("Agent State: ", state)
    messages = [SystemMessage(SYSTEM_PROMPT)] + state['messages']
    response = model_with_tools.invoke(messages)

    return { "messages": response }

builder = StateGraph(State)
tools = ToolNode([retrieve_docs])

builder.add_node("agent_call", call_model)
builder.add_node("tools", tools)

builder.add_edge(START, "agent_call")
builder.add_conditional_edges("agent_call", should_continue, ["tools", END])
builder.add_edge("tools", "agent_call")

agent = builder.compile(checkpointer=memory)
config: RunnableConfig = {"configurable": {"thread_id": "1"}}


while(True):
    user_input = input()
    if user_input == 'x':
        break

    response = agent.invoke({"messages": [{"role": "user", "content": user_input}]}, config)

    print(response)
