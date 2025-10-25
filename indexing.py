from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from dotenv import load_dotenv

load_dotenv()


pdf_path = Path(__file__).parent / "pondi.pdf"
loader = PyPDFLoader(pdf_path)
docs = loader.load()

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=250,
    chunk_overlap=40,
)

embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
chunks = text_splitter.split_documents(documents=docs)

vector_store = QdrantVectorStore.from_documents(
    documents=chunks,
    url="http://localhost:6333",
    collection_name="NIRF Information",
    embedding=embeddings,
)

