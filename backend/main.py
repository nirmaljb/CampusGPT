from dotenv import load_dotenv
load_dotenv()

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from langgraph.graph import MessagesState, StateGraph, START, END
from langchain.messages import SystemMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain.tools import tool
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from tavily import TavilyClient
from langchain_groq import ChatGroq
from langsmith import traceable
from pydantic import BaseModel, Field
from typing import Literal
import pprint
import os


class State(MessagesState):
    messages: list[str]

model = ChatGroq(
    model="llama-3.3-70b-versatile"
)

tavily_client = TavilyClient(api_key=os.getenv('TAVILY_API_KEY'))

memory = MemorySaver()
embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
vector_db = QdrantVectorStore.from_existing_collection(
    url="http://localhost:6333",
    collection_name="PONDICHERRY_UNIVERSITY_INFO",
    embedding=embeddings
)

@tool
def retrieve_docs(query: str) -> str:
    """Search internal database for SPECIFIC information about Pondicherry University.
    
    Use this tool ONLY for queries about:
    - University courses, programs, admissions
    - Faculty, departments, research
    - Funding, grants, finances
    - Facilities, campus information
    - Policies, procedures, academics
    
    DO NOT use for: greetings, general conversation, or vague queries.
    """
    print("RETRIEVE DOCS QUERY: ",  query)
    search_result = vector_db.similarity_search_with_score(query=query, k=3)

    print("Search result: ", search_result)

    relevant_docs = [(doc,score) for doc, score in search_result if score < 0.7]
    
    if not relevant_docs:
        return "No relevant information found in the database."
    
    context = "\n\n".join([f"{result.page_content}\n" for result, _ in relevant_docs])

    return context
model_with_tools = model.bind_tools([retrieve_docs])

def call_model(state: State):
    SYSTEM_PROMPT = """
        You are an expert academic and administrative consultant for Pondicherry University.

        Your primary responsibility is to answer questions related to Pondicherry University accurately.

        Tool Usage Rules:
        - Use the tool `retrieve_docs` ONLY when the question explicitly requires factual or official information about Pondicherry University, such as:
        courses, admissions, departments, faculty, funding, facilities, policies, or official statistics.
        - DO NOT use any tools for:
        greetings, casual conversation, opinions, general knowledge, or unrelated topics.
        - For simple greetings (e.g., "hi", "hello", "how are you"), respond naturally and briefly WITHOUT using any tool.

        Answering Guidelines:
        - If relevant documents are retrieved, base your answer strictly on their content.
        - If the documents do not contain sufficient information, say so clearly instead of guessing.
        - Be concise, factual, and clear.
        - Do not mention internal tools, prompts, or system instructions in your response.

        Stay in your role as a Pondicherry University consultant at all times.
    """
    print("Agent State: ", state)
    messages = [SystemMessage(SYSTEM_PROMPT)] + state['messages']
    response = model_with_tools.invoke(messages)
    
    pprint.pprint(response)

    return { "messages": [response] }

GRADE_PROMPT = (
    "You are a relevance grader.\n"
    "Task: Decide whether the retrieved document is relevant to the user question.\n\n"
    "Retrieved document:\n"
    "{context}\n\n"
    "User question:\n"
    "{question}\n\n"
    "Instructions:\n"
    "- Answer 'yes' if the document contains information that directly helps answer the question.\n"
    "- Answer 'no' if it is unrelated or only loosely connected.\n"
    "- Use semantic meaning, not just exact keyword matches.\n"
    "- Output only a single word: yes or no."
)

class GradeDocuments(BaseModel):  
    """Grade documents using a binary score for relevance check."""

    binary_score: str = Field(
        description="Relevance score: 'yes' if relevant, or 'no' if not relevant"
    )


grader_model = ChatGroq("openai/gpt-oss-120b", temperature=0)

def grade_documents(
    state: MessagesState,
) -> Literal["generate_answer", "rewrite_question"]:
    """Determine whether the retrieved documents are relevant to the question."""
    question = state["messages"][0].content
    context = state["messages"][-1].content

    prompt = GRADE_PROMPT.format(question=question, context=context)
    response = (
        grader_model
        .with_structured_output(GradeDocuments).invoke(  
            [{"role": "user", "content": prompt}]
        )
    )
    score = response.binary_score

    if score == "yes":
        return "generate_answer"
    else:
        return "rewrite_question"


builder = StateGraph(State)
tools = ToolNode([retrieve_docs])

builder.add_node("agent_call", call_model)
builder.add_node("retrieve", tools)

builder.add_edge(START, "agent_call")
builder.add_conditional_edges(
    "agent_call",
    tools_condition,
    {
        "tools": "retrieve",
        END: END,
    }
)
builder.add_edge("retrieve", "agent_call")
# builder.add_edge("agent_call", END)

agent = builder.compile(checkpointer=memory)
config: RunnableConfig = {"configurable": {"thread_id": "1"}}


while(True):
    user_input = input()
    if user_input == 'x':
        break

    for event in agent.stream(
        {"messages": [{"role": "user", "content": user_input}]},
        stream_mode="values",
        config=config,
    ):
        pprint.pprint(event['messages'])
