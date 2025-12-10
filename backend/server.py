# from dotenv import load_dotenv
# load_dotenv()

from .client.client_rq import queue
from .queues.workers import process_query
from fastapi import FastAPI, Query

app = FastAPI()

@app.get('/')
def root():
    return { "status": 'Server is up and running' }

@app.post('/chat')
def chat(query: str = Query(..., description="The chat of the user")):
    job = queue.enqueue(process_query, query) 
    return { "status": "queued", "job_id": job.id }

@app.get('/job-status')
def get_job(job_id: str = Query(..., description="Job ID")):
    job = queue.fetch_job(job_id=job_id)
    result = job.return_value()

    return { "result": result }