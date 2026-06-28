import requests
from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter


def scrape_website(url):
    print(f"Scraping URL: {url}")

    try:
        loader = WebBaseLoader(url)
        documents = loader.load()

        if not documents:
            return None, "No content found on this page"

        # Get page title from metadata if available
        page_title = documents[0].metadata.get("title", url)
        print(f"Page title: {page_title}")
        print(f"Content length: {len(documents[0].page_content)} characters")

        return documents, page_title

    except Exception as e:
        return None, f"Error scraping website: {str(e)}"


def split_documents(documents):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )

    chunks = text_splitter.split_documents(documents)
    print(f"Total chunks created: {len(chunks)}")
    return chunks


def validate_url(url):
    try:
        response = requests.head(url, timeout=10, allow_redirects=True)
        return response.status_code < 400
    except:
        return False
