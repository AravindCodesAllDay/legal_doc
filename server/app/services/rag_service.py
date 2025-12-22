import os
import shutil
from typing import List
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
import fitz  
from app.core.settings import settings

class RAGService:
    def __init__(self):
        self.embeddings = OllamaEmbeddings(
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_HOST
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        self.storage_base = "storage"
        os.makedirs(self.storage_base, exist_ok=True)
        
    def _get_session_paths(self, session_id: str):
        session_root = os.path.join(self.storage_base, session_id)
        doc_path = os.path.join(session_root, "documents")
        chroma_path = os.path.join(session_root, "chroma")
        return session_root, doc_path, chroma_path

    def _get_vectorstore(self, session_id: str):
        _, _, chroma_path = self._get_session_paths(session_id)
        return Chroma(
            collection_name=f"chat_{session_id}",
            embedding_function=self.embeddings,
            persist_directory=chroma_path
        )

    async def ingest_file(self, temp_file_path: str, filename: str, session_id: str) -> int:
        _, doc_path, _ = self._get_session_paths(session_id)
        os.makedirs(doc_path, exist_ok=True)
        
        target_file_path = os.path.join(doc_path, filename)
        
        # Check duplicate
        if os.path.exists(target_file_path):
            raise FileExistsError(f"File {filename} already exists in this session.")

        # Move file to permanent storage
        shutil.copy(temp_file_path, target_file_path)

        text = ""
        if filename.endswith(".pdf"):
            doc = fitz.open(target_file_path)
            for page in doc:
                text += page.get_text()
        else:
            with open(target_file_path, "r", encoding="utf-8") as f:
                text = f.read()

        if not text:
            return 0

        chunks = self.text_splitter.split_text(text)
        # Add source path or just filename. Filename is better for citation display.
        documents = [Document(page_content=chunk, metadata={"source": filename}) for chunk in chunks]
        
        vectorstore = self._get_vectorstore(session_id)
        vectorstore.add_documents(documents)
        return len(chunks)

    async def query(self, query: str, session_id: str, k: int = 3) -> List[Document]:
        vectorstore = self._get_vectorstore(session_id)
        # Search
        results = vectorstore.similarity_search(query, k=k)
        return results

    async def delete_session_data(self, session_id: str):
        session_root, _, _ = self._get_session_paths(session_id)
        if os.path.exists(session_root):
            shutil.rmtree(session_root)

    async def delete_document(self, session_id: str, filename: str):
        vectorstore = self._get_vectorstore(session_id)
        # Delete from Chroma
        results = vectorstore.get(where={"source": filename})
        if results and results["ids"]:
             vectorstore.delete(ids=results["ids"])
        
        # Delete file from storage
        _, doc_path, _ = self._get_session_paths(session_id)
        file_path = os.path.join(doc_path, filename)
        if os.path.exists(file_path):
            os.remove(file_path)

rag_service = RAGService()
