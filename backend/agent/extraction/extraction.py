"""
Faculty Details Extraction Script
Parses faculty data from markdown and stores in PostgreSQL

Database: nirf
Table: faculty_details
"""

import re
import uuid
from datetime import datetime
from typing import Optional
import psycopg2
from psycopg2.extras import execute_values


# PostgreSQL Configuration
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "nirf",
    "user": "postgres",      # Change this
    "password": "mypassword"   # Change this
}

# Path to markdown file
MARKDOWN_FILE_PATH = "../data/parsed_data/pondiuni_clean_final.md"


# SQL Statements
CREATE_TABLE_SQL = """
DROP TABLE IF EXISTS faculty_details CASCADE;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE faculty_details (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    srno                INTEGER NOT NULL,
    name                VARCHAR(255) NOT NULL,
    age                 INTEGER,
    designation         VARCHAR(100),
    gender              VARCHAR(10),
    qualification       VARCHAR(50),
    experience_years    DECIMAL(4,1),
    currently_working   BOOLEAN,
    joining_date        DATE,
    leaving_date        DATE,
    association_type    VARCHAR(50),
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_faculty_designation ON faculty_details(designation);
CREATE INDEX idx_faculty_gender ON faculty_details(gender);
CREATE INDEX idx_faculty_association_type ON faculty_details(association_type);
CREATE INDEX idx_faculty_currently_working ON faculty_details(currently_working);
"""

INSERT_SQL = """
INSERT INTO faculty_details (
    id, srno, name, age, designation, gender, qualification,
    experience_years, currently_working, joining_date, leaving_date, association_type
) VALUES %s
"""


def parse_date(date_str: str) -> Optional[datetime]:
    """Parse date from DD-MM-YYYY format."""
    if not date_str or date_str.strip() == "--" or date_str.strip() == "-":
        return None
    try:
        return datetime.strptime(date_str.strip(), "%d-%m-%Y").date()
    except ValueError:
        print(f"Warning: Could not parse date: {date_str}")
        return None


def parse_boolean(value: str) -> Optional[bool]:
    """Parse Yes/No to boolean."""
    if not value:
        return None
    value = value.strip().lower()
    if value == "yes":
        return True
    elif value == "no":
        return False
    return None


def parse_experience(value: str) -> Optional[float]:
    """Parse experience years, handling empty values."""
    if not value or value.strip() == "":
        return None
    try:
        return float(value.strip())
    except ValueError:
        print(f"Warning: Could not parse experience: {value}")
        return None


def parse_integer(value: str) -> Optional[int]:
    """Parse integer, handling empty values."""
    if not value or value.strip() == "":
        return None
    try:
        return int(value.strip())
    except ValueError:
        print(f"Warning: Could not parse integer: {value}")
        return None


def extract_faculty_from_markdown(file_path: str) -> list[dict]:
    """
    Extract faculty details from markdown table.
    Returns list of faculty dictionaries.
    """
    faculty_list = []
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Find the Faculty Details section
    faculty_section_match = re.search(
        r"## Faculty Details\n\|.*?\n\|[-:\s|]+\n((?:\|.*?\n)+)",
        content,
        re.DOTALL
    )
    
    if not faculty_section_match:
        print("Error: Could not find Faculty Details section in markdown")
        return faculty_list
    
    table_rows = faculty_section_match.group(1).strip().split("\n")
    
    for row in table_rows:
        if not row.strip() or not row.startswith("|"):
            continue
        
        # Split by | and clean up
        columns = [col.strip() for col in row.split("|")]
        # Remove empty first and last elements from split
        columns = [c for c in columns if c != ""]
        
        if len(columns) < 11:
            print(f"Warning: Skipping row with insufficient columns: {row[:50]}...")
            continue
        
        try:
            faculty = {
                "id": str(uuid.uuid4()),
                "srno": parse_integer(columns[0]),
                "name": columns[1].strip(),
                "age": parse_integer(columns[2]),
                "designation": columns[3].strip(),
                "gender": columns[4].strip(),
                "qualification": columns[5].strip(),
                "experience_years": parse_experience(columns[6]),
                "currently_working": parse_boolean(columns[7]),
                "joining_date": parse_date(columns[8]),
                "leaving_date": parse_date(columns[9]),
                "association_type": columns[10].strip() if len(columns) > 10 else None
            }
            faculty_list.append(faculty)
        except Exception as e:
            print(f"Error parsing row: {row[:50]}... - {e}")
            continue
    
    return faculty_list


def create_table(cursor):
    """Create the faculty_details table (drops existing)."""
    print("Creating table faculty_details...")
    cursor.execute(CREATE_TABLE_SQL)
    print("Table created successfully!")


def insert_faculty_data(cursor, faculty_list: list[dict]):
    """Insert faculty data into the table."""
    print(f"Inserting {len(faculty_list)} faculty records...")
    
    # Prepare data as tuples
    values = [
        (
            f["id"],
            f["srno"],
            f["name"],
            f["age"],
            f["designation"],
            f["gender"],
            f["qualification"],
            f["experience_years"],
            f["currently_working"],
            f["joining_date"],
            f["leaving_date"],
            f["association_type"]
        )
        for f in faculty_list
    ]
    
    execute_values(cursor, INSERT_SQL, values)
    print(f"Successfully inserted {len(values)} records!")


def main():
    """Main execution function."""
    print("=" * 60)
    print("Faculty Details Extraction Script")
    print("=" * 60)
    
    # Step 1: Parse markdown
    print(f"\n[1/3] Parsing markdown file: {MARKDOWN_FILE_PATH}")
    faculty_list = extract_faculty_from_markdown(MARKDOWN_FILE_PATH)
    print(f"Extracted {len(faculty_list)} faculty records")
    
    if not faculty_list:
        print("No faculty data found. Exiting.")
        return
    
    # Step 2: Connect to PostgreSQL
    print(f"\n[2/3] Connecting to PostgreSQL...")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = False
        cursor = conn.cursor()
        print(f"Connected to database: {DB_CONFIG['database']}")
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return
    
    try:
        # Step 3: Create table and insert data
        print(f"\n[3/3] Creating table and inserting data...")
        create_table(cursor)
        insert_faculty_data(cursor, faculty_list)
        
        # Commit transaction
        conn.commit()
        print("\n" + "=" * 60)
        print("SUCCESS! All data has been committed to the database.")
        print("=" * 60)
        
        # Print summary
        cursor.execute("SELECT COUNT(*) FROM faculty_details")
        count = cursor.fetchone()[0]
        print(f"\nTotal records in faculty_details: {count}")
        
        cursor.execute("""
            SELECT designation, COUNT(*) 
            FROM faculty_details 
            GROUP BY designation 
            ORDER BY COUNT(*) DESC
        """)
        print("\nRecords by Designation:")
        for row in cursor.fetchall():
            print(f"  {row[0]}: {row[1]}")
        
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
        print("Transaction rolled back.")
        raise
    finally:
        cursor.close()
        conn.close()
        print("\nDatabase connection closed.")


if __name__ == "__main__":
    main()
