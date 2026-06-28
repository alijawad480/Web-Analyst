# Website Analyst Chatbot

Paste any website URL and have a full multi-turn conversation about its content.
Built with LangChain, LangGraph, ChromaDB, HuggingFace, FastAPI, and Streamlit.

---

## What This Project Does

- Paste any website URL (company page, news article, finance page etc.)
- App scrapes and indexes the page automatically
- Ask questions in plain English about the page content
- Multi-turn conversation with memory (remembers previous questions)
- Tracks all URLs you have analyzed in your session
- Off-topic questions are detected and redirected using LangGraph routing
- All history saved in SQLite database

---

## Project Structure

```
website_analyst/
├── scraper/
│   └── loader.py        # WebBaseLoader to scrape any URL
├── rag/
│   └── vectorstore.py   # ChromaDB per URL (each URL gets own collection)
├── graph/
│   └── workflow.py      # LangGraph workflow with 4 nodes
├── api/
│   └── main.py          # FastAPI backend
├── frontend/
│   └── app.py           # Streamlit (local with FastAPI)
├── database/
│   └── db.py            # SQLite for user history and URLs
├── app.py               # Standalone Streamlit (for deployment)
├── requirements.txt
└── .env
```

---

## LangGraph Workflow

```
User Question
     |
     v
[classify node]  -> Is this about the website or off-topic?
     |
     |-- website --> [retrieve node] -> Get top 4 chunks from ChromaDB
     |                    |
     |                    v
     |              [answer node]  -> Generate answer with context + history
     |
     |-- general --> [general node] -> Politely redirect to website topic
```

---

## Setup Instructions

### Step 1: Create Virtual Environment

```bash
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Add Groq API Key

Open `.env` and add your free Groq API key from https://console.groq.com:

```
GROQ_API_KEY=gsk_your_key_here
```

---

## How to Run (Local)

### Option 1: Standalone (no FastAPI needed)

```bash
streamlit run app.py
```

### Option 2: With FastAPI backend

Terminal 1:
```bash
uvicorn api.main:app --reload
```

Terminal 2:
```bash
streamlit run frontend/app.py
```

FastAPI docs available at: http://localhost:8000/docs

---

## How to Deploy on Streamlit Cloud

1. Push to GitHub
2. Go to https://share.streamlit.io
3. Select your repo, set main file to `app.py`
4. Add secret: `GROQ_API_KEY = your_key`
5. Deploy

---

## API Endpoints

| Method | Endpoint | What it does |
|--------|----------|-------------|
| GET | /health | Check API status |
| GET | /new-session | Get new session ID |
| POST | /analyze | Scrape and index a URL |
| POST | /chat | Ask question about a URL |
| GET | /history/{session_id}?url=... | Get chat history |
| GET | /urls/{session_id} | Get all analyzed URLs |

---

## Sample URLs to Test

- https://www.systemslimited.com
- https://arbisoft.com
- https://folio3.com
- Any news article or company about page

## Sample Questions to Ask

- What does this company do?
- Who are their clients?
- What services do they offer?
- Where are they located?
- What technologies do they use?
