import streamlit as st
import asyncio
from memory_manager import store_message, retrieve_messages
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from document_loader import load_and_chunk_documents_with_multiple_strategies
from qdrant_helper import index_document_with_strategies, query_qdrant_multi_strategy,hybrid_search
from rag import generate_answer
from web_crawl import get_scrape_content

SESSION_ID = "user_session"
COLLECTION_NAME = "document_chunks"

# Initialize session state if not present
if "messages" not in st.session_state:
    st.session_state.messages = retrieve_messages(SESSION_ID)

if "last_retrieved_chunks" not in st.session_state:
    st.session_state.last_retrieved_chunks = []

# Add sidebar for document upload
st.sidebar.header("Upload Documents")
uploaded_files = st.sidebar.file_uploader(
    "Choose your documents (PDF, DOCX, TXT)", 
    type=["pdf", "docx", "txt"], 
    accept_multiple_files=True
)

# Handle file uploads
if uploaded_files:
    for uploaded_file in uploaded_files:
        st.sidebar.write(f"**{uploaded_file.name}**")
        if st.sidebar.button(f"Upload {uploaded_file.name}"):
            file_path = f"uploads/{uploaded_file.name}"
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.sidebar.write(f"✅ Saved {uploaded_file.name}")
            chunks = load_and_chunk_documents_with_multiple_strategies(file_path)
            response = index_document_with_strategies(COLLECTION_NAME, uploaded_file.name, chunks)
            if response["status"] == "success":
                st.sidebar.success(f"Indexed {len(chunks)} chunks for {uploaded_file.name}")
            else:
                st.sidebar.error(f"Failed to index {uploaded_file.name}: {response['message']}")

# Add sidebar for URL input
st.sidebar.header("Upload URL")
url = st.sidebar.text_input("Enter the URL of the website to scrape")

# Handle URL input
if url:
    if st.sidebar.button("Scrape URL"):
        st.sidebar.write(f"Scraping {url}...")
        try:
            scraped_content = asyncio.run(get_scrape_content(url))  # Assuming this function returns the scraped text
            st.sidebar.write(f"✅ Scraped content from {url}")
            chunks = load_and_chunk_documents_with_multiple_strategies(scraped_content)
            response = index_document_with_strategies(COLLECTION_NAME, url, chunks)
            if response["status"] == "success":
                st.sidebar.success(f"Indexed {len(chunks)} chunks for {url}")
            else:
                st.sidebar.error(f"Failed to index {url}: {response['message']}")
        except Exception as e:
            st.sidebar.error(f"Failed to scrape {url}: {str(e)}")



# Left sidebar for showing sources
with st.sidebar:
    st.header("Sources")
    if st.session_state.last_retrieved_chunks:
        for i, chunk in enumerate(st.session_state.last_retrieved_chunks):
            source = chunk["metadata"].get("source", "Unknown Source")
            score = chunk.get("score", "N/A")
            with st.expander(f"Source {i+1} (Score: {score:.2f}) - {source}"):
                st.write(chunk["text"])
    else:
        st.write("No sources to display. Ask a question to see relevant sources.")

# Collapsible Chat History
with st.sidebar:
    st.header("Chat History")
    if st.button("Show Chat History"):
        with st.expander("Chat History", expanded=True):
            for message in st.session_state.messages:
                if isinstance(message, HumanMessage):
                    st.markdown(f"**User:** {message.content}")
                elif isinstance(message, AIMessage):
                    st.markdown(f"**Assistant:** {message.content}")

# Chat input for user query
query = st.chat_input("Ask a question about your documents...")

if query:
    st.session_state.messages.append(HumanMessage(content=query))
    store_message(SESSION_ID, query, "user")
    
    with st.chat_message("user"):
        st.write(query)
    
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            #retrieved_chunks = query_qdrant_multi_strategy(COLLECTION_NAME, query)
            retrieved_chunks = hybrid_search(COLLECTION_NAME, query)
            
            if retrieved_chunks:
                st.session_state.last_retrieved_chunks = retrieved_chunks  # Store for sidebar
                unique_contexts = list({chunk["text"] for chunk in retrieved_chunks})  # Set removes duplicates
                combined_context = " ".join(unique_contexts)
                answer = generate_answer(query, combined_context)
                
                context_message = SystemMessage(content=f"Use the following context to answer the question:\n{combined_context}")
                st.session_state.messages.append(context_message)
                st.session_state.messages.append(AIMessage(content=answer))
                st.write(answer)
                store_message(SESSION_ID, answer, "assistant")
            
            else:
                no_info_msg = "I don't have enough information to answer that question. Please try a different question or upload relevant documents."
                st.write(no_info_msg)
                st.session_state.messages.append(AIMessage(content=no_info_msg))
                store_message(SESSION_ID, no_info_msg, "assistant")

# Button to clear chat history and sources
if st.button("Clear Chat History"):
    st.session_state.messages = [
        SystemMessage(content="I am a helpful AI assistant that can answer questions about your documents.")
    ]
    st.session_state.last_retrieved_chunks = []  # Clear sources
