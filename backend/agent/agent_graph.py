from dotenv import load_dotenv
import os

load_dotenv()

from langchain_qdrant import QdrantVectorStore
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_tavily import TavilySearch
from typing_extensions import TypedDict, NotRequired
from typing import List
from langchain_core.documents import Document
from langgraph.graph import END, StateGraph
from langgraph.checkpoint.memory import MemorySaver
import pprint

# LLM Models
base_llm = "llama-3.3-70b-versatile"
heavier_llm = "openai/gpt-oss-120b"

# Embeddings and Vector Store
embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")

vectorstore = QdrantVectorStore.from_existing_collection(
    url="http://localhost:6333",
    collection_name="PONDICHERRY_UNIVERSITY_INFO",
    embedding=embeddings
)
retriever = vectorstore.as_retriever()

# Relevance grader
grader_model = ChatGroq(model=base_llm, temperature=1)
grader_llm = grader_model.with_structured_output(method="json_mode")

grader_prompt = PromptTemplate(
    template="""You are a grader assessing relevance 
    of a retrieved document to a user question. If the document contains any information or keywords related to the user question, 
    grade it as relevant. This is a very lenient test - the document does not need to fully answer the question to be considered relevant.
    
    Give a binary score 'yes' or 'no' to indicate whether the document is relevant to the question.
    Also provide a brief explanation for your decision.
    
    Return your response as a JSON with two keys: 'score' (either 'yes' or 'no') and 'explanation'.
     
    Here is the retrieved document: 
    {document}
    
    Here is the user question: 
    {question}
    """,
    input_variables=["question", "document"],
)

retrieval_grader = grader_prompt | grader_llm

# Generate
rag_prompt = PromptTemplate(
    template="""You are an assistant for question-answering tasks. 
    Use the following pieces of retrieved context to answer the question. If you don't know the answer, just say that you don't know. 
    Output the answer with as much details as possible
    Question: {question} 
    Context: {context} 
    Answer: 
    """,
    input_variables=["question", "document"],
)

rag_llm = ChatGroq(model=base_llm, temperature=0)

# Chain
rag_chain = rag_prompt | rag_llm | StrOutputParser()

# Basic Response
basic_prompt = PromptTemplate(
    template="""You are an assistant for question-answering tasks regarding Pondicherry University
    Look at the question and just simply greet the user with a warm message, introduce your capabilities of producing incredibly high quality low error data regarding the university data. Moveover you can do data analysis and get latest realtime data about the university.
    If you have information about the question, output it but make sure to greet the user.
    Question: {question} 
    """,
    input_variables=["question"],
)

basic_llm = ChatGroq(model=heavier_llm, temperature=0)
basic_rag_chain = basic_prompt | basic_llm | StrOutputParser()

# Hallucination Grader
hallucination_llm = ChatGroq(model=heavier_llm, temperature=0)

hallucination_prompt = PromptTemplate(
    template="""You are a grader assessing whether 
    an answer is grounded in / supported by a set of facts. Give a binary score 'yes' or 'no' score to indicate 
    whether the answer is grounded in / supported by a set of facts. Provide the binary score as a JSON with a 
    single key 'score' and no preamble or explanation.
    
    Here are the facts:
    {documents} 

    Here is the answer: 
    {generation}
    """,
    input_variables=["generation", "documents"],
)

hallucination_grader = hallucination_prompt | hallucination_llm | JsonOutputParser()

# Answer Grader
answer_llm = ChatGroq(model=heavier_llm, temperature=0)

answer_prompt = PromptTemplate(
    template="""You are a grader assessing whether an 
    answer is useful to resolve a question. Give a binary score 'yes' or 'no' to indicate whether the answer is 
    useful to resolve a question. Provide the binary score as a JSON with a single key 'score' and no preamble or explanation.
     
    Here is the answer:
    {generation} 

    Here is the question: {question}
    """,
    input_variables=["generation", "question"],
)

answer_grader = answer_prompt | answer_llm | JsonOutputParser()

# Router
router_llm = ChatGroq(model=heavier_llm)

router_prompt = PromptTemplate(
    template="""You are an expert routing model designed for GPT-OSS-120B.

            Your task is to decide how a user query should be handled.

            Routing Options:
            - "basic"        → For greetings or simple conversational messages that do NOT require any information retrieval or web search
            - "vectorstore"  → For questions that can be answered using internal or curated knowledge
            - "web_search"   → For questions that require real-time, current, or latest information

            Routing Rules:
            - If the user greets (e.g., "hi", "hello", "hey", "good morning") or writes a simple message that does not require retrieving information, choose "basic".
            - Use "vectorstore" for questions related to:
            - University-specific or internal information
            - Historical data, reports, statistics, funding, placements
            - Policies, rules, notices, circulars stored internally
            - Use "web_search" for questions that require:
            - Real-time or time-sensitive information
            - Latest updates, announcements, weather, or current events
            - Semantic similarity is sufficient; exact keyword matching is NOT required.

            Examples:

            Question: Hi
            Answer: {{"datasource": "basic"}}

            Question: What is the weather at Pondicherry University?
            Answer: {{"datasource": "web_search"}}

            Question: What are the fundings received in the last 3 years?
            Answer: {{"datasource": "vectorstore"}}

            Question: What are the placement data of the university?
            Answer: {{"datasource": "vectorstore"}}

            Question: What is the latest circular?
            Answer: {{"datasource": "web_search"}}

            Question to route:
            {question}
            """,
    input_variables=["question"],
)

question_router = router_prompt | router_llm | JsonOutputParser()

# Search
web_search_tool = TavilySearch(k=3)

# State
class GraphState(TypedDict):
    """
    Represents the state of our graph.

    Attributes:
        question: question
        generation: LLM generation
        web_search: whether to add search
        documents: list of documents 
        retry_count: hallucination retry attempts
        limit_exhausted: whether retry cap was hit
        decision: scratch key for routing decisions
    """
    question : str
    generation : str
    web_search : str
    documents : List[Document]
    retry_count: NotRequired[int]
    limit_exhausted: NotRequired[bool]
    decision: NotRequired[str]

# Nodes
def retrieve(state):
    """
    Retrieve documents from vectorstore

    Args:
        state (dict): The current graph state

    Returns:
        state (dict): New key added to state, documents, that contains retrieved documents
    """
    print("---RETRIEVE---")
    question = state["question"]

    # Retrieval
    documents = retriever.invoke(question)
    return {"documents": documents, "question": question}

def generate(state):
    """
    Generate answer using RAG on retrieved documents

    Args:
        state (dict): The current graph state

    Returns:
        state (dict): New key added to state, generation, that contains LLM generation
    """
    print("---GENERATE---")
    question = state["question"]
    documents = state["documents"]
    
    # RAG generation
    generation = rag_chain.invoke({"context": documents, "question": question})
    return {"documents": documents, "question": question, "generation": generation}

def grade_documents(state):
    """
    Determines whether the retrieved documents are relevant to the question
    If any document is not relevant, we will set a flag to run web search

    Args:
        state (dict): The current graph state

    Returns:
        state (dict): Filtered out irrelevant documents and updated web_search state
    """

    print("---CHECK DOCUMENT RELEVANCE TO QUESTION---")
    question = state["question"]
    documents = state["documents"]
    
    # Score each doc
    filtered_docs = []
    web_search = "No"
    for d in documents:
        score = retrieval_grader.invoke({"question": question, "document": d.page_content})
        grade = score['score']
        # Document relevant
        if grade.lower() == "yes":
            print("---GRADE: DOCUMENT RELEVANT---")
            filtered_docs.append(d)
        # Document not relevant
        else:
            print("---GRADE: DOCUMENT NOT RELEVANT---")
            # We do not include the document in filtered_docs
            # We set a flag to indicate that we want to run web search
            web_search = "Yes"
            continue
    return {"documents": filtered_docs, "question": question, "web_search": web_search}
    
def web_search(state):
    """
    Web search based based on the question

    Args:
        state (dict): The current graph state

    Returns:
        state (dict): Appended web results to documents
    """

    print("---WEB SEARCH---")
    question = state["question"]
    documents = state.get("documents", [])

    # Web search
    docs = web_search_tool.invoke({"query": question})
    web_results = "\n".join([d["content"] for d in docs["results"]])
    web_results = Document(page_content=web_results)
    if documents is not None:
        documents.append(web_results)
    else:
        documents = [web_results]
    return {"documents": documents, "question": question }

# Conditional edge
def route_question(state):
    """
    Route question to web search or RAG.

    Args:
        state (dict): The current graph state

    Returns:
        str: Next node to call
    """

    print("---ROUTE QUESTION---")
    question = state["question"]
    print(question)
    source = question_router.invoke({"question": question})  
    print(source)
    print(source['datasource'])
    if source['datasource'] == 'web_search':
        print("---ROUTE QUESTION TO WEB SEARCH---")
        return "websearch"
    elif source['datasource'] == 'vectorstore':
        print("---ROUTE QUESTION TO RAG---")
        return "vectorstore"
    elif source['datasource'] == 'basic':
        print("---ROUTE QUESTION TO BASIC REPLY---")
        return "basic"

def basic_response(state):
    print("---BASIC RESPONSE---")
    question = state["question"]

    print(question)
    generate = basic_rag_chain.invoke({"question": question})
    print(generate)

    return { "question": question, "generation": generate }

def decide_to_generate(state):
    """
    Determines whether to generate an answer, or add web search

    Args:
        state (dict): The current graph state

    Returns:
        str: Binary decision for next node to call
    """

    print("---ASSESS GRADED DOCUMENTS---")
    question = state["question"]
    web_search = state["web_search"]
    filtered_documents = state["documents"]

    if web_search == "Yes":
        # All documents have been filtered check_relevance
        # We will re-generate a new query
        print("---DECISION: ALL DOCUMENTS ARE NOT RELEVANT TO QUESTION, INCLUDE WEB SEARCH---")
        return "websearch"
    else:
        # We have relevant documents, so generate answer
        print("---DECISION: GENERATE---")
        return "generate"

# Conditional edge
def grade_generation_v_documents_and_question(state):
    """
    Determines whether the generation is grounded in the document and answers question.

    Args:
        state (dict): The current graph state

    Returns:
        str: Decision for next node to call
    """

    print("---CHECK HALLUCINATIONS---")
    question = state["question"]
    documents = state["documents"]
    generation = state["generation"]

    score = hallucination_grader.invoke({"documents": documents, "generation": generation})
    grade = score['score']

    # Check hallucination
    if grade == "yes":
        print("---DECISION: GENERATION IS GROUNDED IN DOCUMENTS---")
        # Check question-answering
        print("---GRADE GENERATION vs QUESTION---")
        score = answer_grader.invoke({"question": question,"generation": generation})
        grade = score['score']
        if grade == "yes":
            print("---DECISION: GENERATION ADDRESSES QUESTION---")
            return "useful"
        else:
            print("---DECISION: GENERATION DOES NOT ADDRESS QUESTION---")
            return "not useful"
    else:
        print("---DECISION: GENERATION IS NOT GROUNDED IN DOCUMENTS, RE-TRY---")
        print(f'question: {question}, documents: {documents}, generation: {generation}, grade: {grade}')
        return "not supported"


def handle_hallucination(state):
    """
    Track hallucination retries and decide next step.
    After MAX_RETRIES, do one websearch fallback; if still ungrounded, return the last generation with a warning.
    """

    MAX_RETRIES = 3
    retry_count = state.get("retry_count", 0) + 1
    limit_exhausted = state.get("limit_exhausted", False)

    # Bubble retry count through state
    state = {**state, "retry_count": retry_count}

    if retry_count >= MAX_RETRIES:
        if limit_exhausted:
            generation = state.get("generation", "")
            warning = "\n\n[Note: Verification limit reached after 3 attempts; consider more sources.]"
            state["generation"] = f"{generation}{warning}"
            state["decision"] = "force_return"
            return state

        # First time hitting the limit: trigger a web search fallback once
        state["web_search"] = "Yes"
        state["limit_exhausted"] = True
        state["decision"] = "fallback_websearch"
        return state

    # Under retry limit → try generating again
    state["decision"] = "retry"
    return state

# Build workflow
workflow = StateGraph(GraphState)

# Define the nodes
workflow.add_node("websearch", web_search) # web search
workflow.add_node("retrieve", retrieve) # retrieve
workflow.add_node("grade_documents", grade_documents) # grade documents
workflow.add_node("generate", generate) # generate
workflow.add_node("basic_response", basic_response)

# Build graph
workflow.set_conditional_entry_point(
    route_question,
    {
        "websearch": "websearch",
        "vectorstore": "retrieve",
        "basic": "basic_response"
    },
)

workflow.add_edge("retrieve", "grade_documents")
workflow.add_conditional_edges(
    "grade_documents",
    decide_to_generate,
    {
        "websearch": "websearch",
        "generate": "generate",
    },
)
workflow.add_edge("websearch", "generate")
workflow.add_node("handle_hallucination", handle_hallucination)

workflow.add_conditional_edges(
    "generate",
    grade_generation_v_documents_and_question,
    {
        "not supported": "handle_hallucination",
        "useful": END,
        "not useful": "websearch",
    },
)

workflow.add_conditional_edges(
    "handle_hallucination",
    lambda state: state.get("decision", "retry"),
    {
        "retry": "generate",
        "fallback_websearch": "websearch",
        "force_return": END,
    },
)
workflow.set_finish_point("basic_response")

# Compile
memory = MemorySaver()
agent = workflow.compile(checkpointer=memory)

# Interactive loop
if __name__ == "__main__":
    config = {"configurable": {"thread_id": "1"}}
    
    print("RAG Chatbot initialized. Type 'x' to exit.")
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() == 'x':
            break
        
        inputs = {"question": user_input}
        for output in agent.stream(inputs, config=config):
            for key, value in output.items():
                pprint.pprint(f"Finished running: {key}:")
        
        if "generation" in value:
            pprint.pprint(value["generation"])