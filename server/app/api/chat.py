from datetime import datetime
from typing import List, Optional

import os
import shutil
import uuid
import json

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.mongo import get_db
from app.models.chat import ChatSession, ChatMessage, DocumentMetadata
from app.services.rag_service import rag_service
from app.services.ollama_service import ollama_service

router = APIRouter(prefix="/chats", tags=["Chat"])


class CreateChatRequest(BaseModel):
    title: Optional[str] = None


class RenameChatRequest(BaseModel):
    title: str


class MessageRequest(BaseModel):
    message: str


@router.post("/", response_model=ChatSession)
async def create_chat_session(
    request: CreateChatRequest,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    session = ChatSession(title=request.title or "New Chat")
    await db["sessions"].insert_one(session.dict())
    return session


@router.get("/", response_model=List[ChatSession])
async def list_chat_sessions(
    skip: int = 0,
    limit: int = 20,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    cursor = db["sessions"].find().sort(
        "updated_at", -1).skip(skip).limit(limit)
    sessions = await cursor.to_list(length=limit)
    return sessions


@router.get("/{session_id}", response_model=ChatSession)
async def get_chat_session(
    session_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    session = await db["sessions"].find_one({"id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.delete("/{session_id}")
async def delete_chat_session(
    session_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    result = await db["sessions"].delete_one({"id": session_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Session not found")

    # Clean up RAG data
    await rag_service.delete_session_data(session_id)
    return {"message": "Session deleted"}


@router.post("/{session_id}/upload")
async def upload_documents(
    session_id: str,
    files: Optional[List[UploadFile]] = File(default=None),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    if not files:
        raise HTTPException(
            status_code=400, detail="No files uploaded or 'files' field missing")

    session = await db["sessions"].find_one({"id": session_id})
    if not session:
        # Create new session if strictly allowed or just handle it as new
        # User requested: "can be added after its created first" -> fix: auto-create
        session = ChatSession(id=session_id, title="New Chat")
        await db["sessions"].insert_one(session.dict())

    uploaded_files = []
    total_chunks = 0

    for file in files:
        temp_path = f"temp_{uuid.uuid4()}_{file.filename}"
        try:
            with open(temp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            try:
                chunk_count = await rag_service.ingest_file(temp_path, file.filename, session_id)
                total_chunks += chunk_count or 0

                # Save Metadata
                doc_meta = DocumentMetadata(
                    filename=file.filename,
                    content_type=file.content_type,
                    size=file.size
                )
                uploaded_files.append(doc_meta.dict())

            except FileExistsError:
                print(f"Skipping duplicate file: {file.filename}")
                continue  # Skip duplicates

        except Exception as e:
            # Continue or fail? Let's log and continue
            print(f"Error uploading {file.filename}: {e}")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    # Bulk push
    if uploaded_files:
        await db["sessions"].update_one(
            {"id": session_id},
            {"$push": {"documents": {"$each": uploaded_files}},
                "$set": {"updated_at": datetime.utcnow()}}
        )

        # Add System Message for Event
        filenames = ", ".join([d["filename"] for d in uploaded_files])
        system_note = ChatMessage(
            role="system", content=f"User uploaded files: {filenames}")
        await db["sessions"].update_one(
            {"id": session_id},
            {"$push": {"messages": system_note.dict()}}
        )

    return {"uploaded_count": len(uploaded_files), "total_chunks_ingested": total_chunks}


@router.post("/{session_id}/message")
async def send_message(
    session_id: str,
    request: MessageRequest,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    session_data = await db["sessions"].find_one({"id": session_id})
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")

    # 1. Retrieve Context
    # 1. Retrieve Context
    related_docs = await rag_service.query(request.message, session_id)
    
    # Format context with source citations
    context_texts = []
    
    # Add list of available documents to system context
    available_docs = [d.get("filename") for d in session_data.get("documents", [])]
    if available_docs:
        doc_list_str = ", ".join(available_docs)
        context_texts.append(f"SYSTEM NOTE: The user has the following documents uploaded in this session: {doc_list_str}. Only answer based on these documents if the user asks about them.")
    
    for doc in related_docs:
        source = doc.metadata.get("source", "Unknown")
        # Ensure we only use context if it matches one of the active documents? 
        # Actually RAG service already filters by chroma collection (session_id), so cross-session contamination is handled by collection isolation.
        # But cross-document contamination within same session:
        context_texts.append(f"[Source: {source}]\n{doc.page_content}")

    # 2. Append User Message
    user_msg = ChatMessage(role="user", content=request.message)
    await db["sessions"].update_one(
        {"id": session_id},
        {"$push": {"messages": user_msg.dict()}, "$set": {
            "updated_at": datetime.utcnow()}}
    )

    # 3. Construct Message History for LLM
    history = session_data.get("messages", [])[-10:]  # Last 10 messages
    history.append(user_msg.dict())

    # 4. Generator for Streaming
    async def event_generator():
        full_response = ""
        async for token in ollama_service.stream_chat(history, context_texts):
            full_response += token
            yield f"data: {json.dumps({'token': token})}\n\n"

        # Save Assistant Message
        assistant_msg = ChatMessage(role="assistant", content=full_response)
        await db["sessions"].update_one(
            {"id": session_id},
            {"$push": {"messages": assistant_msg.dict()}, "$set": {
                "updated_at": datetime.utcnow()}}
        )
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.delete("/{session_id}/documents/{filename}")
async def delete_document(
    session_id: str,
    filename: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    session = await db["sessions"].find_one({"id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # 1. Remove from RAG
    await rag_service.delete_document(session_id, filename)

    # 2. Remove from DB Metadata
    await db["sessions"].update_one(
        {"id": session_id},
        {"$pull": {"documents": {"filename": filename}},
            "$set": {"updated_at": datetime.utcnow()}}
    )

    # System Message
    system_note = ChatMessage(
        role="system", content=f"User removed file: {filename}")
    await db["sessions"].update_one(
        {"id": session_id},
        {"$push": {"messages": system_note.dict()}}
    )

    return {"message": f"Document {filename} deleted"}


@router.patch("/{session_id}")
async def rename_chat_session(
    session_id: str,
    request: RenameChatRequest,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    result = await db["sessions"].update_one(
        {"id": session_id},
        {"$set": {"title": request.title, "updated_at": datetime.utcnow()}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Session not found")

    return {"id": session_id, "title": request.title}


@router.get("/{session_id}/documents/{filename}")
async def get_document_file(
    session_id: str,
    filename: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    # Verify session exists
    session = await db["sessions"].find_one({"id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    storage_path = os.path.join("storage", session_id, "documents", filename)

    try:
        if not os.path.exists(storage_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        # Ensure absolute path for safety
        abs_path = os.path.abspath(storage_path)
        return FileResponse(
            abs_path, 
            filename=filename, 
            media_type="application/pdf", 
            content_disposition_type="inline"
        )
    except Exception as e:
        print(f"Error serving file {filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Could not serve file: {str(e)}")
