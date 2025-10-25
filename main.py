from dotenv import load_dotenv
from langchain_qdrant import QdrantVectorStore
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    max_retries=2
)
embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
user_input = input("Enter your message: ")

vector_db = QdrantVectorStore.from_existing_collection(
    url="http://localhost:6333",
    collection_name="NIRF Information",
    embedding=embeddings
)

search_result = vector_db.similarity_search(query=user_input)
context = "\n\n".join([f"Page content: {result.page_content}\nPage number: {result.metadata['page_label']}" for result in search_result])

SYSTEM_PROMPT = f"""
    You're a helpful AI Assistant who answers user's queries based on the available context retrieved from the pdf file along with page contents and page number.
    You should only answer user's queries based on the context provided and navigate the user the page number for more information
    Context: {context}
"""

messages = [
    ("system",SYSTEM_PROMPT),
    ("human", user_input),
]


llm_response = llm.invoke(messages)
print(llm_response.content)


