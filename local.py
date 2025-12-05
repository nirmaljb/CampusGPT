from dotenv import load_dotenv
load_dotenv()

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain.tools import tool


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

def process_query(query: str):
    search_result = vector_db.similarity_search(query=query)
    context = "\n\n".join([f"Page content: {result.page_content}\n" for result in search_result])
    
    print(context)

    SYSTEM_PROMPT = f"""
        You're an expert chatbot specialised to help top management at pondicherry university.
        You will be given a query and based on it you're supposed to look through the database as well as search the web.
        You're going to collect the information and merge it together in a clean format.
        Context: {context}
    """

    messages = [
        ("system",SYSTEM_PROMPT),
        ("human", query),
    ]

    llm_response = model_with_search.invoke(messages)
    return llm_response.content

@tool("web_search", description="Searches the web for information, specifically regarding Pondicherry University")
def search(query: str) -> str:
    """
    Search the web for information regarding Pondicherry Univeristy.
    
    :param query: Search query to look up for
    :type query: str
    :return: The result from the web search
    :rtype: str
    """

    response = model_with_search.invoke(query)
    return str(response.content)
