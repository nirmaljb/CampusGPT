from dotenv import load_dotenv
load_dotenv()

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from langgraph.graph import MessagesState, StateGraph, START, END

class State(MessagesState):
    messages: list[str]

model = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    max_retries=2
)

model_with_search = model.bind_tools([{"google_search": {}}])
embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")

vector_db = QdrantVectorStore.from_existing_collection(
    url="http://localhost:6333",
    collection_name="PONDICHERRY_UNIVERSITY_INFO",
    embedding=embeddings
)

def process_query(state: MessagesState):    
    search_result = vector_db.similarity_search(query=state['messages'][-1])
    context = "\n\n".join([f"{result.page_content}\n" for result in search_result])

    print(state)

    SYSTEM_PROMPT = f"""
        You're an expert consultant for Pondicherry University management and students.

        **USER CONVERSATION HISTORY:**
        {state['messages']}
        
        **Instructions:**
        1. First, analyze the INTERNAL DATABASE CONTEXT below
        2. Use Google Search to find current information and verify/supplement the internal data
        3. Cross-check information from both sources
        4. Merge and present comprehensive, accurate information
        5. Use tables where appropriate for clarity
        6. Ensure output is clean and highly readable

        **INTERNAL DATABASE CONTEXT:**
        {context}

        ---
        Now answer the user's query using both the internal context and web search results.
    """

    query = [
        ("system",SYSTEM_PROMPT),
        ("human", state['messages'][-1]),
    ]

    llm_response = model_with_search.invoke(query)
    return { "messages": llm_response.content }

builder = StateGraph(State)

builder.add_node("process_query", process_query)
builder.add_edge(START, "process_query")
builder.add_edge("process_query", END)

agent = builder.compile()

while(True):
    user_input = input()
    response = agent.invoke({"messages": [user_input]})

    print(response)
