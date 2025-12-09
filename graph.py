from dotenv import load_dotenv
load_dotenv()

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from langgraph.graph import MessagesState, StateGraph, START, END

class State(MessagesState):
    message: list[str]
    query: str

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

def query(state: State):
    """
    Search the database as well web and answer the user query regarding Pondicherry University
    
    :param state: State variable contains the context as well the present query.
    :type state: State
    """
    search_result = vector_db.similarity_search(query=state['query'])
    db_context = "\n\n".join([f"Page content: {result.page_content}\n" for result in search_result])

    SYSTEM_PROMPT = f"""
        You're an expert content specialist/consultant helping top management (HODs, Professors and even students) at Pondicherry University.
        YOU'RE FORCED TO DO A WEB SEARCH AND GATHER INFORMATION AS WELL GET THE INFORMATION FROM THE CONTEXT.
        Cross check the information, fill the data gaps and correct the information if needed, finally merge the information. DON'T MAKE ANY MISTAKE
        USER CONTEXT: {state['message']}
        INTERNAL DATABASE CONTEXT: {db_context}
    """

    messages = [
        ("system",SYSTEM_PROMPT),
        ("human", query),
    ]

    llm_response = model_with_search.invoke(messages)
    return llm_response.content

graph = StateGraph(State)

graph.add_node("processing_query", query)

graph.add_edge(START, "processing_query")
graph.add_edge("processing_key", END)


agent = graph.compile()



