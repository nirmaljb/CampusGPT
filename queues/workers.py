from dotenv import load_dotenv
load_dotenv()

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_qdrant import QdrantVectorStore

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash-lite",
    max_retries=2
)

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
        You're a smart AI chatbot put at touch device at the entrance of Pondicherry University. Visitors can use their speak as well as write to this device.
        DON'T WRITE "Based on the context/information provided". ANSWER CONFIDENTLY.
        Your task is to understand the query of the user and answer in the most natural human sounding as possible. 
        Remember, your output would be converted to speech, so respond as if a human is talking to another human.
        If you're unaware of the information you can politely say that to the user or do a google search tool calling.
        WRITE COMPLETE ENGLISH SENTENCES WITH CORRECT GRAMMAR AND POLITE TONE.
        DON'T MAKE ANY MISTAKE
        Context: {context}
    """

    messages = [
        ("system",SYSTEM_PROMPT),
        ("human", query),
    ]

    llm_response = llm.invoke(messages)
    return llm_response.content
