import streamlit as st
import requests
import uuid

API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Website Analyst Chatbot",
    page_icon="🌐",
    layout="wide"
)

# Session State
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "current_url" not in st.session_state:
    st.session_state.current_url = None

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "analyzed_urls" not in st.session_state:
    st.session_state.analyzed_urls = []


# Helper Functions
def analyze_url(url, session_id):
    response = requests.post(
        f"{API_URL}/analyze",
        json={"url": url, "session_id": session_id},
        timeout=60
    )
    return response


def ask_question(question, url, session_id):
    response = requests.post(
        f"{API_URL}/chat",
        json={"question": question, "url": url, "session_id": session_id},
        timeout=60
    )
    return response


def get_analyzed_urls(session_id):
    response = requests.get(f"{API_URL}/urls/{session_id}", timeout=10)
    if response.status_code == 200:
        return response.json().get("urls", [])
    return []


# Header
st.title("🌐 Website Analyst Chatbot")
st.caption("Paste any website URL and have a conversation about its content")
st.divider()

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")

    # API Health Check
    try:
        health = requests.get(f"{API_URL}/health", timeout=3).json()
        st.success("✅ API Running")
    except:
        st.error("❌ API not running\nRun: uvicorn api.main:app --reload")

    st.divider()

    # URL Input
    st.subheader("🔗 Analyze a Website")
    url_input = st.text_input(
        "Paste URL here",
        placeholder="https://example.com",
        help="Paste any website URL to analyze"
    )

    if st.button("🔍 Analyze Website", use_container_width=True):
        if not url_input:
            st.warning("Please enter a URL")
        elif not url_input.startswith("http"):
            st.warning("URL must start with http or https")
        else:
            with st.spinner("Scraping and indexing website..."):
                try:
                    response = analyze_url(url_input, st.session_state.session_id)
                    if response.status_code == 200:
                        data = response.json()
                        st.success(f"✅ {data['message']}")

                        if not data.get("already_indexed"):
                            st.info(f"Chunks indexed: {data.get('total_chunks', 0)}")

                        # Set as current URL and clear chat
                        st.session_state.current_url = url_input
                        st.session_state.chat_history = []

                        # Refresh URL list
                        st.session_state.analyzed_urls = get_analyzed_urls(
                            st.session_state.session_id
                        )
                        st.rerun()
                    else:
                        st.error(response.json().get("detail", "Error analyzing URL"))
                except Exception as e:
                    st.error(f"Connection error: {str(e)}")

    st.divider()

    # Previously Analyzed URLs
    st.subheader("📋 Analyzed URLs")

    if st.session_state.analyzed_urls:
        for item in st.session_state.analyzed_urls:
            url_display = item["url"][:40] + "..." if len(item["url"]) > 40 else item["url"]
            if st.button(f"🔗 {url_display}", key=item["url"], use_container_width=True):
                st.session_state.current_url = item["url"]
                st.session_state.chat_history = []
                st.rerun()
    else:
        st.caption("No URLs analyzed yet")

    st.divider()

    # Session Info
    st.caption(f"Session: {st.session_state.session_id[:8]}...")
    if st.button("🔄 New Session", use_container_width=True):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.current_url = None
        st.session_state.chat_history = []
        st.session_state.analyzed_urls = []
        st.rerun()


# Main Chat Area
col1, col2 = st.columns([3, 1])

with col1:
    # Show current URL being analyzed
    if st.session_state.current_url:
        st.info(f"💬 Chatting about: {st.session_state.current_url}")
    else:
        st.info("👈 Paste a URL in the sidebar to get started")

    st.subheader("💬 Chat")

    # Display messages
    for chat in st.session_state.chat_history:
        with st.chat_message(chat["role"]):
            st.write(chat["content"])
            if chat.get("question_type") == "general":
                st.caption("ℹ️ Off-topic question redirected")

    # Chat input
    user_question = st.chat_input("Ask anything about the website...")

    if user_question:
        if not st.session_state.current_url:
            st.warning("Please analyze a website URL first using the sidebar.")
        else:
            with st.chat_message("user"):
                st.write(user_question)

            st.session_state.chat_history.append({
                "role": "user",
                "content": user_question
            })

            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    try:
                        response = ask_question(
                            user_question,
                            st.session_state.current_url,
                            st.session_state.session_id
                        )

                        if response.status_code == 200:
                            data = response.json()
                            answer = data["answer"]
                            question_type = data.get("question_type", "website")

                            st.write(answer)

                            if question_type == "general":
                                st.caption("ℹ️ Off-topic question")

                            st.session_state.chat_history.append({
                                "role": "assistant",
                                "content": answer,
                                "question_type": question_type
                            })
                        else:
                            st.error(response.json().get("detail", "Error getting answer"))

                    except requests.exceptions.ConnectionError:
                        st.error("Cannot connect to API. Make sure FastAPI is running.")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")

with col2:
    st.subheader("📊 Info")
    st.metric("Messages", len(st.session_state.chat_history))
    st.metric("URLs Analyzed", len(st.session_state.analyzed_urls))

    if st.session_state.current_url:
        st.divider()
        st.caption("Current URL")
        st.caption(st.session_state.current_url[:50])
