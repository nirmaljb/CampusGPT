import camelot
import pandas as pd
import json

def process_nirf_pdf(pdf_path):
    # 1. Extract tables using Lattice mode (detects grid lines)
    print(f"Processing {pdf_path}...")
    tables = camelot.read_pdf(pdf_path, pages='all', flavor='lattice')
    
    extracted_data = []
    
    # Define the standard Faculty Header
    faculty_columns = [
        "Srno", "Name", "Age", "Designation", "Gender", 
        "Qualification", "Experience", "Working?", "Joining Date", 
        "Leaving Date", "Association"
    ]

    for i, table in enumerate(tables):
        df = table.df
        
        # --- LOGIC TO "READ" ROW CONTENT STARTS HERE ---
        
        # Clean up newlines in data cells to make checking easier
        df = df.replace(r'\n', ' ', regex=True)
        
        # 1. Convert the first few rows to a string to "read" what's inside
        # We grab the first 5 rows to check for keywords like "Professor"
        sample_text = df.head(5).to_string().lower()
        
        # 2. DETECT FACULTY TABLE
        # We check if "professor" or "ph.d" appears in the data, 
        # AND if the table has roughly 11 columns (matches faculty structure)
        is_faculty_data = ("professor" in sample_text or "ph.d" in sample_text)
        is_correct_width = (df.shape[1] == 11)
        
        section_title = f"Table {i}"
        
        if is_faculty_data and is_correct_width:
            # 3. FIX HEADLESS TABLES
            # Check if the first row is actual data (e.g. "19", "Lalitha") 
            # instead of a header.
            
            # If the first cell is a number (like "19" or "1"), it's likely data, not a header.
            first_cell = str(df.iloc[0, 0]).strip()
            
            if first_cell.isdigit():
                # This table is missing headers! (Like Table 21 in your file)
                # We simply assign our standard list as the column headers.
                df.columns = faculty_columns
                section_title = f"Faculty Details (Continuation - Table {i})"
            
            # If the first cell says "Srno", the header is already inside the data rows.
            elif "srno" in first_cell.lower():
                # Set the first row as header and drop it from data
                df.columns = df.iloc[0]
                df = df[1:]
                section_title = "Faculty Details"
                
        # --- END OF LOGIC ---
        
        # Handle other specific tables (Placement, Intake)
        elif "sanctioned" in sample_text:
            section_title = "Sanctioned Approved Intake"
        elif "student strength" in sample_text:
            section_title = "Total Actual Student Strength"
        elif "placement" in sample_text:
            section_title = f"Placement Data (Table {i})"
        
        # Convert to Dictionary (records format)
        # We use 'records' to get a list of dicts: [{'col1': 'val1'}, {'col1': 'val2'}]
        table_data = df.to_dict(orient='records')
        
        extracted_data.append({
            "title": section_title,
            "table_id": i,
            "data": table_data
        })

    return extracted_data

# Run the extraction
content = process_nirf_pdf("./data/pondiuni_nirf.pdf")

# Save
output_file = "./data/pondiuni_camlot_final.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(content, f, indent=4, ensure_ascii=False)

print(f"Extraction complete. Saved to {output_file}")