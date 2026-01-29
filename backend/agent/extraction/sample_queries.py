"""
Sample Queries for Faculty Details Table
Run this after extraction.py to test the data.
"""

import psycopg2
from tabulate import tabulate


# PostgreSQL Configuration (same as extraction.py)
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "nirf",
    "user": "postgres",      # Change this
    "password": "mypassword"   # Change this
}


def run_query(cursor, title: str, query: str, params=None):
    """Execute and display query results."""
    print(f"\n{'=' * 60}")
    print(f"📊 {title}")
    print(f"{'=' * 60}")
    print(f"Query: {query[:100]}..." if len(query) > 100 else f"Query: {query}")
    print("-" * 60)
    
    cursor.execute(query, params)
    results = cursor.fetchall()
    
    if results:
        headers = [desc[0] for desc in cursor.description]
        print(tabulate(results, headers=headers, tablefmt="grid"))
    else:
        print("No results found.")
    
    print(f"Rows returned: {len(results)}")


def main():
    print("=" * 60)
    print("Faculty Details - Sample Queries")
    print("=" * 60)
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        print("Connected to database successfully!")
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return
    
    try:
        # Query 1: Total faculty count
        run_query(
            cursor,
            "Total Faculty Count",
            "SELECT COUNT(*) as total_faculty FROM faculty_details"
        )
        
        # Query 2: Faculty by Designation
        run_query(
            cursor,
            "Faculty Count by Designation",
            """
            SELECT designation, COUNT(*) as count 
            FROM faculty_details 
            GROUP BY designation 
            ORDER BY count DESC
            """
        )
        
        # Query 3: Gender Distribution
        run_query(
            cursor,
            "Gender Distribution",
            """
            SELECT gender, COUNT(*) as count,
                   ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
            FROM faculty_details 
            GROUP BY gender
            """
        )
        
        # Query 4: Currently Working vs Left
        run_query(
            cursor,
            "Currently Working Status",
            """
            SELECT 
                CASE WHEN currently_working THEN 'Currently Working' ELSE 'Left' END as status,
                COUNT(*) as count
            FROM faculty_details 
            GROUP BY currently_working
            """
        )
        
        # Query 5: Faculty by Association Type
        run_query(
            cursor,
            "Faculty by Association Type",
            """
            SELECT association_type, COUNT(*) as count 
            FROM faculty_details 
            GROUP BY association_type 
            ORDER BY count DESC
            """
        )
        
        # Query 6: Average Experience by Designation
        run_query(
            cursor,
            "Average Experience (Years) by Designation",
            """
            SELECT designation, 
                   ROUND(AVG(experience_years)::numeric, 1) as avg_experience,
                   MIN(experience_years) as min_exp,
                   MAX(experience_years) as max_exp
            FROM faculty_details 
            WHERE experience_years IS NOT NULL
            GROUP BY designation 
            ORDER BY avg_experience DESC
            """
        )
        
        # Query 7: Age Distribution
        run_query(
            cursor,
            "Age Statistics by Designation",
            """
            SELECT designation,
                   ROUND(AVG(age)::numeric, 1) as avg_age,
                   MIN(age) as youngest,
                   MAX(age) as oldest
            FROM faculty_details 
            WHERE age IS NOT NULL
            GROUP BY designation 
            ORDER BY avg_age DESC
            """
        )
        
        # Query 8: Qualifications
        run_query(
            cursor,
            "Faculty by Qualification",
            """
            SELECT qualification, COUNT(*) as count 
            FROM faculty_details 
            GROUP BY qualification 
            ORDER BY count DESC
            """
        )
        
        # Query 9: Senior Faculty (30+ years experience)
        run_query(
            cursor,
            "Senior Faculty (30+ Years Experience)",
            """
            SELECT name, designation, experience_years, age
            FROM faculty_details 
            WHERE experience_years >= 30 
            ORDER BY experience_years DESC
            LIMIT 10
            """
        )
        
        # Query 10: Female Professors
        run_query(
            cursor,
            "Female Professors",
            """
            SELECT name, experience_years, qualification
            FROM faculty_details 
            WHERE gender = 'Female' AND designation = 'Professor'
            ORDER BY experience_years DESC
            LIMIT 10
            """
        )
        
        # Query 11: Joinings by Year
        run_query(
            cursor,
            "Faculty Joining Trend (Top Years)",
            """
            SELECT EXTRACT(YEAR FROM joining_date)::INTEGER as year, 
                   COUNT(*) as joinings
            FROM faculty_details 
            WHERE joining_date IS NOT NULL
            GROUP BY year 
            ORDER BY joinings DESC
            LIMIT 10
            """
        )
        
        # Query 12: Sample Faculty Records
        run_query(
            cursor,
            "Sample Faculty Records (First 5)",
            """
            SELECT srno, name, designation, gender, experience_years
            FROM faculty_details 
            ORDER BY srno 
            LIMIT 5
            """
        )
        
    except Exception as e:
        print(f"Error executing query: {e}")
    finally:
        cursor.close()
        conn.close()
        print("\n" + "=" * 60)
        print("Database connection closed.")


if __name__ == "__main__":
    main()
