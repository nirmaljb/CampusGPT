from dotenv import load_dotenv
load_dotenv()

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_qdrant import QdrantVectorStore

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    max_retries=2
)

embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
vector_db = QdrantVectorStore.from_existing_collection(
    url="http://localhost:6333",
    collection_name="PONDICHERRY_UNIVERSITY_INFO",
    embedding=embeddings
)

def process_query(query: str):
    search_result = vector_db.similarity_search(query=query)
    context = "\n\n".join([f"Page content: {result.page_content}\n" for result in search_result])

    SYSTEM_PROMPT = f"""
        You're a helpful AI Assistant who answers user's queries based on the available context retrieved from the pdf file along with page contents and page number.
        You should only answer user's queries based on the context provided
        Context: {context}
    """

    messages = [
        ("system",SYSTEM_PROMPT),
        ("human", query),
    ]


    llm_response = llm.invoke(messages)
    return llm_response.content
