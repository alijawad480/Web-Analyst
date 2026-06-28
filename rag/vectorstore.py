import os
import hashlib
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma


def get_embeddings():
    """Load HuggingFace embedding model"""
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
    return embeddings


def get_collection_name(url):
    """
    Create a unique short ID from a URL.
    We use this as the ChromaDB collection name.
    Example: https://example.com -> url_a1b2c3d4e5
    """
    return "url_" + hashlib.md5(url.encode()).hexdigest()[:10]


def create_vectorstore(chunks, url):
    """
    Create embeddings for scraped chunks and store in ChromaDB.
    Each URL gets its own collection so they do not mix.
    """
    collection_name = get_collection_name(url)
    persist_dir = f"vectorstore/{collection_name}"

    print(f"Creating vectorstore for: {url}")

    embeddings = get_embeddings()

    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=persist_dir,
        collection_name=collection_name
    )

    print(f"Vectorstore saved to: {persist_dir}")
    return vectorstore


def load_vectorstore(url):
    """
    Load existing vectorstore for a URL from disk.
    Returns None if not found.
    """
    collection_name = get_collection_name(url)
    persist_dir = f"vectorstore/{collection_name}"

    if not os.path.exists(persist_dir):
        return None

    embeddings = get_embeddings()

    vectorstore = Chroma(
        persist_directory=persist_dir,
        embedding_function=embeddings,
        collection_name=collection_name
    )

    print(f"Vectorstore loaded for: {url}")
    return vectorstore


def vectorstore_exists(url):
    """Check if this URL has already been indexed"""
    collection_name = get_collection_name(url)
    persist_dir = f"vectorstore/{collection_name}"
    return os.path.exists(persist_dir)
