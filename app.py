import os
import uuid
import streamlit as st
from dotenv import load_dotenv

from scraper.loader import scrape_website, split_documents, validate_url
from rag.vectorstore import create_vectorstore, load_vectorstore, vectorstore_exists
from graph.workflow import create_workflow
from database.db import (
    init_db, save_analyzed_url, save_message,
    get_chat_history, get_analyzed_urls
)

load_dotenv()

# --- Page Config ---
st.set_page_config(
    page_title="Website Analyst Chatbot",
    page_icon="🌐",
    layout="wide"
)

os.makedirs("vectorstore", exist_ok=True)
init_db()

# --- Session State ---
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "current_url" not in st.session_state:
    st.session_state.current_url = None

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "workflow" not in st.session_state:
    st.session_state.workflow = None

if "analyzed_urls" not in st.session_state:
    st.session_state.analyzed_urls = []


# --- Header ---
st.title("🌐 Website Analyst Chatbot")
st.caption("Paste any business or finance website URL and have a full conversation about it")
st.divider()


# --- Sidebar ---
with st.sidebar:
    st.header("⚙️ Settings")

    st.divider()

    st.subheader("🔗 Analyze a Website")
    url_input = st.text_input(
        "Paste URL here",
        placeholder="https://example.com",
        help="Paste any webpage URL to analyze"
    )

    if st.button("🔍 Analyze Website", use_container_width=True):
        if not url_input:
            st.warning("Please enter a URL")
        elif not url_input.startswith("http"):
            st.warning("URL must start with http or https")
        else:
            with st.spinner("Scraping and indexing website... please wait"):
                try:
                    url = url_input.strip()

                    # Check if already indexed
                    if vectorstore_exists(url):
                        vectorstore = load_vectorstore(url)
                        st.session_state.workflow = create_workflow(vectorstore)
                        st.session_state.current_url = url
                        st.session_state.chat_history = []
                        st.success("✅ URL already indexed. Ready to chat!")
                    else:
                        # Validate URL
                        if not validate_url(url):
                            st.error("URL is not accessible. Please check and try again.")
                        else:
                            # Scrape
                            documents, page_title = scrape_website(url)

                            if documents is None:
                                st.error(f"Error: {page_title}")
                            else:
                                # Split into chunks
                                chunks = split_documents(documents)

                                # Create vectorstore
                                vectorstore = create_vectorstore(chunks, url)

                                # Create workflow
                                st.session_state.workflow = create_workflow(vectorstore)
                                st.session_state.current_url = url
                                st.session_state.chat_history = []

                                # Save to database
                                save_analyzed_url(
                                    st.session_state.session_id,
                                    url,
                                    page_title
                                )

                                # Refresh URL list
                                st.session_state.analyzed_urls = get_analyzed_urls(
                                    st.session_state.session_id
                                )

                                st.success(f"✅ Website analyzed! {len(chunks)} chunks indexed.")
                                st.info(f"Page: {page_title}")

                    st.rerun()

                except Exception as e:
                    st.error(f"Error: {str(e)}")

    st.divider()

    # Previously Analyzed URLs in this session
    st.subheader("📋 Your History")

    analyzed = get_analyzed_urls(st.session_state.session_id)

    if analyzed:
        for item in analyzed:
            short_url = item["url"][:38] + "..." if len(item["url"]) > 38 else item["url"]
            label = item.get("page_title") or short_url
            label = label[:38] + "..." if len(label) > 38 else label

            if st.button(f"🔗 {label}", key=f"url_{item['url']}", use_container_width=True):
                # Switch to this URL
                vectorstore = load_vectorstore(item["url"])
                if vectorstore:
                    st.session_state.workflow = create_workflow(vectorstore)
                    st.session_state.current_url = item["url"]
                    # Load previous chat for this URL
                    st.session_state.chat_history = get_chat_history(
                        st.session_state.session_id,
                        item["url"]
                    )
                    st.rerun()
    else:
        st.caption("No URLs analyzed yet in this session")

    st.divider()

    st.caption(f"Session: {st.session_state.session_id[:8]}...")
    if st.button("🔄 New Session", use_container_width=True):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.current_url = None
        st.session_state.chat_history = []
        st.session_state.workflow = None
        st.rerun()

    st.divider()
    st.caption("Built with LangChain + LangGraph + ChromaDB + Groq")


# --- Main Chat Area ---
col1, col2 = st.columns([3, 1])

with col1:

    if st.session_state.current_url:
        st.info(f"💬 Analyzing: **{st.session_state.current_url}**")
    else:
        st.info("👈 Paste a website URL in the sidebar to get started")

    st.subheader("💬 Chat")

    # Display all chat messages
    for chat in st.session_state.chat_history:
        with st.chat_message(chat["role"]):
            st.write(chat["content"])
            if chat.get("question_type") == "general":
                st.caption("ℹ️ Off-topic question")

    # Chat input box
    user_question = st.chat_input("Ask anything about the website...")

    if user_question:
        if not st.session_state.current_url or not st.session_state.workflow:
            st.warning("Please analyze a website URL first.")
        else:
            # Show user message immediately
            with st.chat_message("user"):
                st.write(user_question)

            st.session_state.chat_history.append({
                "role": "user",
                "content": user_question
            })

            # Get answer from LangGraph workflow
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    try:
                        result = st.session_state.workflow.invoke({
                            "question": user_question,
                            "context": "",
                            "answer": "",
                            "question_type": "",
                            "chat_history": st.session_state.chat_history
                        })

                        answer = result["answer"]
                        question_type = result.get("question_type", "website")

                        st.write(answer)

                        if question_type == "general":
                            st.caption("ℹ️ Off-topic question detected")

                        # Save to database
                        save_message(
                            st.session_state.session_id,
                            st.session_state.current_url,
                            "user",
                            user_question
                        )
                        save_message(
                            st.session_state.session_id,
                            st.session_state.current_url,
                            "assistant",
                            answer
                        )

                        st.session_state.chat_history.append({
                            "role": "assistant",
                            "content": answer,
                            "question_type": question_type
                        })

                    except Exception as e:
                        st.error(f"Error: {str(e)}")

with col2:
    st.subheader("📊 Info")

    analyzed_count = len(get_analyzed_urls(st.session_state.session_id))
    msg_count = len([m for m in st.session_state.chat_history if m["role"] == "user"])

    st.metric("Questions Asked", msg_count)
    st.metric("URLs Analyzed", analyzed_count)

    if st.session_state.chat_history:
        st.divider()
        st.caption("Recent Questions")
        for chat in st.session_state.chat_history:
            if chat["role"] == "user":
                q = chat["content"]
                st.caption(f"• {q[:45]}..." if len(q) > 45 else f"• {q}")
