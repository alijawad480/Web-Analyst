import os
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from scraper.loader import scrape_website, split_documents, validate_url
from rag.vectorstore import create_vectorstore, load_vectorstore, vectorstore_exists
from graph.workflow import create_workflow
from database.db import (
    init_db, save_analyzed_url, save_message,
    get_chat_history, get_analyzed_urls, get_all_sessions
)

# App Setup 
app = FastAPI(
    title="Website Analyst Chatbot API",
    description="Paste any website URL and have a conversation about it"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

os.makedirs("vectorstore", exist_ok=True)

# Initialize database on startup
init_db()


workflow_cache = {}


# Request Models
class AnalyzeRequest(BaseModel):
    url: str
    session_id: str


class ChatRequest(BaseModel):
    question: str
    url: str
    session_id: str


# Helper
def get_or_create_workflow(url):
    
    if url not in workflow_cache:
        vectorstore = load_vectorstore(url)
        if vectorstore is None:
            return None
        workflow_cache[url] = create_workflow(vectorstore)
    return workflow_cache[url]


# Endpoints

@app.get("/")
def home():
    return {"message": "Website Analyst Chatbot API is running"}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "cached_workflows": len(workflow_cache)
    }


@app.get("/new-session")
def new_session():
    """Generate a new session ID"""
    return {"session_id": str(uuid.uuid4())}


@app.post("/analyze")
def analyze_url(request: AnalyzeRequest):
    url = request.url.strip()

    if not url.startswith("http"):
        raise HTTPException(status_code=400, detail="Please provide a valid URL starting with http or https")

    # Check if URL is accessible
    if not validate_url(url):
        raise HTTPException(status_code=400, detail="URL is not accessible. Please check the URL and try again.")

    # If already indexed, just load and return
    if vectorstore_exists(url):
        vectorstore = load_vectorstore(url)
        workflow_cache[url] = create_workflow(vectorstore)

        # save to user's session history
        save_analyzed_url(request.session_id, url, url)

        return {
            "message": "URL already indexed. Ready to chat!",
            "url": url,
            "already_indexed": True
        }

    # Scrape the website
    documents, page_title = scrape_website(url)

    if documents is None:
        raise HTTPException(status_code=400, detail=page_title)  # page_title has error msg

    # Split into chunks
    chunks = split_documents(documents)

    if not chunks:
        raise HTTPException(status_code=400, detail="Could not extract any content from this URL")

    # Create vectorstore
    vectorstore = create_vectorstore(chunks, url)

    # Create workflow and cache it
    workflow_cache[url] = create_workflow(vectorstore)

    # Save to database
    save_analyzed_url(request.session_id, url, page_title)

    return {
        "message": "Website analyzed successfully. Ready to chat!",
        "url": url,
        "page_title": page_title,
        "total_chunks": len(chunks),
        "already_indexed": False
    }


@app.post("/chat")
def chat(request: ChatRequest):
   
    url = request.url.strip()

    if not vectorstore_exists(url):
        raise HTTPException(
            status_code=400,
            detail="This URL has not been analyzed yet. Please call /analyze first."
        )

    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    # Get workflow for this URL
    workflow = get_or_create_workflow(url)

    if workflow is None:
        raise HTTPException(status_code=500, detail="Could not load workflow for this URL")

    # Get previous chat history from database
    history = get_chat_history(request.session_id, url)

    try:
        # Run the LangGraph workflow
        result = workflow.invoke({
            "question": request.question,
            "context": "",
            "answer": "",
            "question_type": "",
            "chat_history": history
        })

        answer = result["answer"]
        question_type = result["question_type"]

        # Save to database
        save_message(request.session_id, url, "user", request.question)
        save_message(request.session_id, url, "assistant", answer)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating answer: {str(e)}")

    return {
        "answer": answer,
        "question_type": question_type,
        "url": url,
        "session_id": request.session_id
    }


@app.get("/history/{session_id}")
def get_history(session_id: str, url: str):
    """Get chat history for a session and URL"""
    history = get_chat_history(session_id, url)
    return {
        "session_id": session_id,
        "url": url,
        "total_messages": len(history),
        "history": history
    }


@app.get("/urls/{session_id}")
def get_urls(session_id: str):
    """Get all URLs analyzed by this session"""
    urls = get_analyzed_urls(session_id)
    return {
        "session_id": session_id,
        "total_urls": len(urls),
        "urls": urls
    }


@app.get("/sessions")
def get_sessions():
# Get all sessions
    sessions = get_all_sessions()
    return {"total_sessions": len(sessions), "sessions": sessions}
