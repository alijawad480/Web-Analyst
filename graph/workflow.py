import os
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

load_dotenv()


# State Definition
class AgentState(TypedDict):
    question: str       # User's question
    context: str        # Retrieved chunks from vectorstore
    answer: str         # Final answer
    question_type: str  # "website" or "general"
    chat_history: List[dict]  # Previous messages in this session


def get_llm():

    llm = ChatGroq(
        model="openai/gpt-oss-20b",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.3
    )
    return llm


# Node Functions

def classify_node(state: AgentState):
    
    llm = get_llm()

    prompt = ChatPromptTemplate.from_template("""
You are a classifier. A user is analyzing a website and asked this question:
"{question}"

Is this question asking about the website content?
Reply with only one word: "website" or "general"
""")

    chain = prompt | llm
    result = chain.invoke({"question": state["question"]})
    question_type = result.content.strip().lower()

    # Safety check - default to website if unclear
    if "website" not in question_type and "general" not in question_type:
        question_type = "website"
    elif "website" in question_type:
        question_type = "website"
    else:
        question_type = "general"

    print(f"Question classified as: {question_type}")
    return {"question_type": question_type}


def retrieve_node(state: AgentState, vectorstore):
    
    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
    docs = retriever.invoke(state["question"])

    # Join all chunks into one context string
    context = "\n\n".join([doc.page_content for doc in docs])

    print(f"Retrieved {len(docs)} chunks from vectorstore")
    return {"context": context}


def answer_node(state: AgentState):
    
    llm = get_llm()

    # Format last 3 exchanges from chat history as text
    history_text = ""
    recent_history = state["chat_history"][-6:]  # last 3 user + 3 assistant
    for msg in recent_history:
        role = "User" if msg["role"] == "user" else "Assistant"
        history_text += f"{role}: {msg['content']}\n"

    prompt = ChatPromptTemplate.from_template("""
You are a helpful website analyst. Answer the user's question based only on the website content below.
If the answer is not found in the content, say "I could not find this information on the website."
Keep your answer clear and to the point.

Previous Conversation:
{history}

Website Content:
{context}

User Question: {question}

Answer:
""")

    chain = prompt | llm
    result = chain.invoke({
        "question": state["question"],
        "context": state["context"],
        "history": history_text
    })

    return {"answer": result.content}


def general_node(state: AgentState):
   
    return {
        "answer": "I am designed to answer questions about the website you provided. Please ask me something about the website content, like its products, services, company info, or any topic covered on that page."
    }


# Routing Function
def route_after_classify(state: AgentState):
    
    return state["question_type"]


# Build Workflow
def create_workflow(vectorstore):

    def retrieve_with_store(state: AgentState):
        return retrieve_node(state, vectorstore)

    # Create the graph with our state schema
    workflow = StateGraph(AgentState)

    # Add all nodes
    workflow.add_node("classify", classify_node)
    workflow.add_node("retrieve", retrieve_with_store)
    workflow.add_node("answer", answer_node)
    workflow.add_node("general", general_node)

    # Set starting point
    workflow.set_entry_point("classify")

    # After classify: go to retrieve or general based on question type
    workflow.add_conditional_edges(
        "classify",
        route_after_classify,
        {
            "website": "retrieve",
            "general": "general"
        }
    )

    # After retrieve: always go to answer
    workflow.add_edge("retrieve", "answer")

    # After answer or general: end the workflow
    workflow.add_edge("answer", END)
    workflow.add_edge("general", END)

    # Compile into a runnable app
    app = workflow.compile()
    print("LangGraph workflow created")
    return app
