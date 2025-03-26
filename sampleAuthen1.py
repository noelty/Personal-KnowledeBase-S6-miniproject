import streamlit as st
import os
import asyncio
import bcrypt
import uuid
import json
from datetime import datetime, timedelta
from memory_manager import store_message
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from document_loader import load_and_chunk_documents_with_multiple_strategies
from qdrant_helper import index_document_with_strategies, query_qdrant_multi_strategy, hybrid_search
from langchain.schema import Document
from memory_manager import (
    retrieve_context_relevant_messages,
    get_all_session_messages,
    format_context_messages
)
from conversation_aware_rag import (
    answer_query_with_conversation_context,
    create_context_message
)
from rag import generate_answer
from web_crawl import get_scrape_content

# User authentication constants
USER_DB_FILE = "user_database.json"
SESSION_DURATION = timedelta(hours=24)

# Initialize user database if it doesn't exist
def init_user_db():
    if not os.path.exists(USER_DB_FILE):
        with open(USER_DB_FILE, "w", encoding='utf-8') as f:
            json.dump({"users": {}}, f, ensure_ascii=False)
        return {"users": {}}
    
    with open(USER_DB_FILE, "r", encoding='utf-8') as f:
        return json.load(f)

# Save user database
def save_user_db(db):
    with open(USER_DB_FILE, "w", encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False)

# Hash password
def hash_password(password):
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode(), salt)
    return hashed.decode()

# Verify password
def verify_password(stored_password, provided_password):
    return bcrypt.checkpw(provided_password.encode(), stored_password.encode())

# Create new user
def create_user(username, password, email):
    db = init_user_db()
    
    if username in db["users"]:
        return False, "Username already exists"
    
    for user_data in db["users"].values():
        if user_data.get("email") == email:
            return False, "Email already registered"
    
    hashed_password = hash_password(password)
    
    db["users"][username] = {
        "password": hashed_password,
        "email": email,
        "created_at": datetime.now().isoformat(),
        "documents": []
    }
    
    save_user_db(db)
    return True, "User created successfully"

# Authenticate user
def authenticate_user(username, password):
    db = init_user_db()
    
    if username not in db["users"]:
        return False, "Invalid username or password"
    
    if not verify_password(db["users"][username]["password"], password):
        return False, "Invalid username or password"
    
    session_id = str(uuid.uuid4())
    expiry = (datetime.now() + SESSION_DURATION).isoformat()
    
    if "sessions" not in db:
        db["sessions"] = {}
    
    db["sessions"][session_id] = {
        "username": username,
        "expires": expiry
    }
    
    save_user_db(db)
    return True, session_id

# Validate session
def validate_session(session_id):
    db = init_user_db()
    
    if "sessions" not in db or session_id not in db["sessions"]:
        return False, None
    
    session = db["sessions"][session_id]
    expiry = datetime.fromisoformat(session["expires"])
    
    if datetime.now() > expiry:
        del db["sessions"][session_id]
        save_user_db(db)
        return False, None
    
    return True, session["username"]

# Logout user
def logout_user(session_id):
    db = init_user_db()
    if "sessions" in db and session_id in db["sessions"]:
        del db["sessions"][session_id]
        save_user_db(db)
        return True
    return False

# Initialize session state
def init_auth_state():
    st.session_state.setdefault("authenticated", False)
    st.session_state.setdefault("username", None)
    st.session_state.setdefault("session_id", None)

# Main application
def main():
    init_auth_state()
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("scraped", exist_ok=True)
    
    if st.session_state.authenticated:
        st.title(f"📚 RAG Assistant - Welcome, {st.session_state.username}!")
        if st.button("Logout"):
            logout_user(st.session_state.session_id)
            st.session_state.clear()
            st.rerun()
        
        st.header("📄 Upload Documents")
        uploaded_files = st.file_uploader("Choose documents", type=["pdf", "docx", "txt"], accept_multiple_files=True)
        
        if uploaded_files:
            user_upload_dir = f"uploads/{st.session_state.username}"
            os.makedirs(user_upload_dir, exist_ok=True)
            
            for uploaded_file in uploaded_files:
                file_path = os.path.join(user_upload_dir, uploaded_file.name)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                st.success(f"Uploaded {uploaded_file.name}")

    else:
        st.title("📚 Conversation-Aware RAG System")
        tab1, tab2 = st.tabs(["Login", "Sign Up"])
        
        with tab1:
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.button("Login"):
                success, result = authenticate_user(username, password)
                if success:
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.session_state.session_id = result
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error(result)
        
        with tab2:
            new_username = st.text_input("Choose Username")
            new_email = st.text_input("Email")
            new_password = st.text_input("Choose Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            if st.button("Create Account"):
                if new_password == confirm_password:
                    success, message = create_user(new_username, new_password, new_email)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
                else:
                    st.error("Passwords do not match")

if __name__ == "__main__":
    main()
