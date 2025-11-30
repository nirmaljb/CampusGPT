from langchain_text_splitters import MarkdownHeaderTextSplitter
import io
import pandas as pd
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
    print(section_name)
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
                print(content_string)
        except Exception as e:
            print(e)