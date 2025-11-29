import requests
import time
import sys

def query_rag(question):
    base_url = "http://localhost:8080"
    
    print(f"Sending query: {question}")
    try:
        # 1. Submit Query
        response = requests.post(f"{base_url}/chat", params={"query": question})
        response.raise_for_status()
        data = response.json()
        
        job_id = data.get("job_id")
        if not job_id:
            print("Error: No job_id returned")
            print(data)
            return

        print(f"Job submitted. ID: {job_id}")
        
        # 2. Poll for status
        while True:
            status_res = requests.get(f"{base_url}/job-status", params={"job_id": job_id})
            status_res.raise_for_status()
            status_data = status_res.json()
            
            result = status_data.get("result")
            if result:
                print("\n--- Response ---")
                print(result)
                print("----------------")
                break
            
            print("Waiting for result...", end="\r")
            time.sleep(1)
            
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to server. Is it running on localhost:8080?")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        q = " ".join(sys.argv[1:])
    else:
        q = "How many students are in the PG program?"
    
    query_rag(q)
