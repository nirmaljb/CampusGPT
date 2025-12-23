from dotenv import load_dotenv
load_dotenv()

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from langgraph.graph import MessagesState, StateGraph, START, END
from langchain.messages import SystemMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver  
from langchain_core.runnables import RunnableConfig
from langchain_ollama import ChatOllama
from langchain.tools import tool
from langgraph.prebuilt import ToolNode

class State(MessagesState):
    messages: list[str]

model = ChatOllama(
    model="llama3.2"
)

# model_with_search = model.bind_tools([{"google_search": {}}]
embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")

vector_db = QdrantVectorStore.from_existing_collection(
    url="http://localhost:6333",
    collection_name="PONDICHERRY_UNIVERSITY_INFO",
    embedding=embeddings
)

@tool
def retrieve_docs(query: str) -> str:
    """Search and return information about Pondicherry University."""
    search_result = vector_db.similarity_search(query=query)
    context = "\n\n".join([f"{result.page_content}\n" for result in search_result])

    return context

model_with_tools = model.bind_tools([retrieve_docs])


def should_continue(state: State):
    """Determine if we should continue to tools or end."""
    last_message = state['messages'][-1]
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"
    return END

def call_model(state: State):    
    """Call the model to generate a response based on the current state. Given
    the question, it will decide to retrieve using the retriever tool, or simply respond to the user.
    """

    SYSTEM_PROMPT = f"""
        You're an expert consultant for Pondicherry University management and students.
        
        **Instructions:**
        1. Use the retrieved information to answer user queries when needed
        2. Ensure output is clean and highly readable
        ---
        Now answer the user's query using the retrieved context.
    """
    print(state)
    messages = [SystemMessage(SYSTEM_PROMPT)] + state['messages']
    print(messages)
    llm_response = model_with_tools.invoke(messages)
    
    return { "messages": [llm_response] }

builder = StateGraph(State)
tools = ToolNode([retrieve_docs])

builder.add_node("agent_call", call_model)
builder.add_node("tools", tools)

builder.add_edge(START, "agent_call")
builder.add_conditional_edges("agent_call", should_continue, ["tools", END])
builder.add_edge("tools", "agent_call")

agent = builder.compile()
config: RunnableConfig = {"configurable": {"thread_id": "1"}}


while(True):
    user_input = input()
    if user_input == 'x':
        break

    response = agent.invoke({"messages": [HumanMessage(user_input)]})

    print(response)
