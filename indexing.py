from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.documents import Document
from langchain_qdrant import Qdrant
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
from dotenv import load_dotenv
import pandas as pd
import io

load_dotenv()

# 1. Load your clean Markdown content
with open("./data/pondiuni_clean_final.md", "r") as f:
    md_content = f.read()

headers_to_split_on = [
    ("##", "Section"),
]

markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
md_docs = markdown_splitter.split_text(md_content)

final_documents = []

for doc in md_docs:
    section_name = doc.metadata.get("Section", "")
    
    if "Faculty Details" in section_name:
        try:
            df = pd.read_csv(
                io.StringIO(doc.page_content), 
                sep="|", 
                skipinitialspace=True, 
                engine="python"
            ).dropna(axis=1, how='all')
            
            df.columns = df.columns.str.strip()
            
            for index, row in df.iterrows():
                if "-----" in str(row.iloc[0]): 
                    continue 
                
                def safe_strip(value, default='Unknown'):
                    return value.strip() if pd.notna(value) and value else default
                
                content_string = (
                    f"Faculty Record for {safe_strip(row['Name'])}: "
                    f"Designation: {safe_strip(row['Designation'])}, "
                    f"Age: {row['Age'] if pd.notna(row['Age']) else 0}, "
                    f"Gender: {safe_strip(row['Gender'])}, "
                    f"Qualification: {safe_strip(row['Qualification'])}, "
                    f"Experience: {row['Experience (Years)'] if pd.notna(row['Experience (Years)']) else 0} years, "
                    f"Department Association: {safe_strip(row['Association Type'])}. "
                    f"Joining Date: {safe_strip(row['Joining Date'])}. "
                    f"Currently working with institution?: {safe_strip(row['Currently Working'])}. "
                    f"Leaving Date: {safe_strip(row['Leaving Date'])}"
                )
                
                new_doc = Document(
                    page_content=content_string,
                    metadata={
                        "section": "Faculty Details",
                        "faculty_name": safe_strip(row['Name']),
                        "designation": safe_strip(row['Designation']),
                        "association": safe_strip(row['Association Type']),
                        "joining_date": safe_strip(row['Joining Date']),
                        "currently_working": safe_strip(row['Currently Working']),
                        "leaving_date": safe_strip(row['Leaving Date']),
                        "gender": safe_strip(row['Gender']),
                        "age": row['Age'] if pd.notna(row['Age']) else 0,
                        "qualification": safe_strip(row['Qualification']),
                        "experience": row['Experience (Years)'] if pd.notna(row['Experience (Years)']) else 0,
                    }
                )
                final_documents.append(new_doc)
                
        except Exception as e:
            print(f"Error parsing faculty table: {e}")

    else:
        doc.page_content = f"Section: {section_name}\n\n" + doc.page_content
        final_documents.append(doc)

print(f"Total Documents Created: {len(final_documents)}")
print(f"Example Faculty Doc: {final_documents[-1].page_content}")

embeddings = GoogleGenerativeAIEmbeddings(
    model="models/text-embedding-004",
    task_type="retrieval_document"
)

url = "http://localhost:6333"
collection_name = "PONDICHERRY_UNIVERSITY_INFO"

vector_store = QdrantVectorStore.from_documents(
    url=url,
    documents=final_documents,
    embedding=embeddings,
    collection_name=collection_name,
)