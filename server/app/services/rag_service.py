import os
import shutil
import gc
import time
from datetime import datetime, timezone
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
            chunk_size=700,
            chunk_overlap=150,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        self.storage_base = "storage"
        os.makedirs(self.storage_base, exist_ok=True)

    def _get_session_paths(self, session_id: str):
        """Get all paths for a session"""
        session_root = os.path.join(self.storage_base, session_id)
        doc_path = os.path.join(session_root, "documents")
        chroma_path = os.path.join(session_root, "chroma")
        return session_root, doc_path, chroma_path

    def _get_collection_name(self, session_id: str) -> str:
        """Generate a unique collection name for a session"""
        return f"session_{session_id}_v2"

    def _get_vectorstore(self, session_id: str) -> Chroma:
        """Get vectorstore for a session"""
        _, _, chroma_path = self._get_session_paths(session_id)
        collection_name = self._get_collection_name(session_id)

        return Chroma(
            collection_name=collection_name,
            embedding_function=self.embeddings,
            persist_directory=chroma_path
        )

    def _extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF with better error handling"""
        try:
            doc = fitz.open(file_path)
            text = ""
            for page_num, page in enumerate(doc):
                page_text = page.get_text()
                if page_text.strip():
                    text += f"\n--- Page {page_num + 1} ---\n{page_text}"
            doc.close()
            return text
        except Exception as e:
            raise Exception(f"Failed to extract text from PDF: {str(e)}")

    def _extract_text_from_file(self, file_path: str, filename: str) -> str:
        """Extract text based on file type"""
        if filename.lower().endswith(".pdf"):
            return self._extract_text_from_pdf(file_path)
        elif filename.lower().endswith((".txt", ".md", ".csv", ".json")):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    return f.read()
            except UnicodeDecodeError:
                # Try with latin-1 encoding as fallback
                with open(file_path, "r", encoding="latin-1") as f:
                    return f.read()
        else:
            raise ValueError(f"Unsupported file type: {filename}")

    async def ingest_file(
        self,
        temp_file_path: str,
        filename: str,
        session_id: str
    ) -> dict:
        """
        Ingest a file into the RAG system with enhanced metadata and stats
        Returns statistics about the ingestion
        """
        _, doc_path, _ = self._get_session_paths(session_id)
        os.makedirs(doc_path, exist_ok=True)

        target_file_path = os.path.join(doc_path, filename)

        # Copy file to permanent storage (overwrite if exists)
        shutil.copy(temp_file_path, target_file_path)

        # Extract text
        try:
            text = self._extract_text_from_file(target_file_path, filename)
        except Exception as e:
            # Cleanup on failure
            if os.path.exists(target_file_path):
                os.remove(target_file_path)
            raise Exception(f"Failed to extract text: {str(e)}")

        if not text or not text.strip():
            if os.path.exists(target_file_path):
                os.remove(target_file_path)
            raise ValueError(f"No text content found in {filename}")

        # Split into chunks
        chunks = self.text_splitter.split_text(text)

        if not chunks:
            if os.path.exists(target_file_path):
                os.remove(target_file_path)
            raise ValueError(f"Failed to create chunks from {filename}")

        # Create documents with enhanced metadata
        ingestion_time = datetime.now(timezone.utc).isoformat()
        documents = [
            Document(
                page_content=chunk,
                metadata={
                    "source": filename,
                    "session_id": session_id,
                    "chunk_index": idx,
                    "total_chunks": len(chunks),
                    "ingested_at": ingestion_time,
                    "file_type": filename.split(".")[-1].lower()
                }
            ) for idx, chunk in enumerate(chunks)
        ]

        # Store in vectorstore (unified session collection)
        try:
            vectorstore = self._get_vectorstore(session_id)
            vectorstore.add_documents(documents)
        except Exception as e:
            # Cleanup on failure
            if os.path.exists(target_file_path):
                os.remove(target_file_path)
            raise Exception(
                f"Failed to add documents to vectorstore: {str(e)}")

        # Return statistics
        avg_chunk_size = sum(len(chunk) for chunk in chunks) / len(chunks)

        return {
            "chunk_count": len(chunks),
            "total_text_length": len(text),
            "avg_chunk_size": int(avg_chunk_size),
            "file_type": filename.split(".")[-1].lower()
        }

    async def query(
        self,
        query: str,
        session_id: str,
        filenames: list[str] | None = None,
        k: int = 5,
        use_mmr: bool = True,
        expand_query: bool = True
    ) -> list[Document]:
        """
        Query documents in a session with optional Multi-Query expansion
        """
        from app.services.ollama_service import ollama_service

        # Generate queries if expansion is enabled
        queries = [query]
        if expand_query:
            try:
                queries = await ollama_service.generate_queries(query, count=2)
                print(f"Expanded queries: {queries}")
            except Exception as e:
                print(f"Query expansion failed: {e}")

        try:
            vectorstore = self._get_vectorstore(session_id)
            
            # Use metadata filter if specific files are requested
            filter_dict = None
            if filenames:
                filter_dict = {"source": {"$in": filenames}}

            all_results = []
            
            # Run search for each query variation
            for q in queries:
                if use_mmr:
                    results = vectorstore.max_marginal_relevance_search(
                        q,
                        k=k,
                        fetch_k=k * 3,
                        filter=filter_dict
                    )
                else:
                    results = vectorstore.similarity_search(
                        q, 
                        k=k,
                        filter=filter_dict
                    )
                all_results.extend(results)

            # Deduplicate results based on content and metadata
            seen_content = set()
            unique_results = []
            for doc in all_results:
                content_hash = hash(doc.page_content + doc.metadata.get("source", ""))
                if content_hash not in seen_content:
                    seen_content.add(content_hash)
                    unique_results.append(doc)

            # Re-sort by score/relevance if possible, or just return top k
            # Since we have multiple queries, we simple return the first k unique matches
            return unique_results[:k]

        except Exception as e:
            print(f"Error querying session {session_id}: {e}")
            return []

    async def query_with_scores(
        self,
        query: str,
        session_id: str,
        filenames: list[str] | None = None,
        k: int = 5
    ) -> list[tuple[Document, float]]:
        """Query with similarity scores using unified collection"""
        try:
            vectorstore = self._get_vectorstore(session_id)
            
            filter_dict = None
            if filenames:
                filter_dict = {"source": {"$in": filenames}}

            return vectorstore.similarity_search_with_score(
                query,
                k=k,
                filter=filter_dict
            )
        except Exception as e:
            print(f"Error querying sessions {session_id} with scores: {e}")
            return []

    async def delete_document(self, session_id: str, filename: str) -> bool:
        """
        Delete a specific document's chunks from the shared vectorstore
        """
        try:
            vectorstore = self._get_vectorstore(session_id)
            # LangChain Chroma doesn't have a direct 'delete by filter' in all versions
            # But we can access the underlying collection
            collection = vectorstore._collection
            collection.delete(where={"source": filename})
            
            gc.collect() 
            print(f"Deleted chunks for {filename} from session {session_id}")
            return True
        except Exception as e:
            print(f"Error deleting chunks for {filename}: {e}")
            return False

    async def delete_session_data(self, session_id: str) -> bool:
        """
        Delete all data for a session (documents and vectorstores)
        Returns True if successful, False otherwise
        """
        session_root, _, _ = self._get_session_paths(session_id)

        if not os.path.exists(session_root):
            print(f"Session {session_id} directory does not exist")
            return True

        # Force garbage collection to release file handles before deleting directory
        gc.collect()
        
        # Retry mechanism for Windows file locks
        for attempt in range(3):
            try:
                shutil.rmtree(session_root)
                print(f"Deleted all data for session {session_id}")
                return True
            except Exception as e:
                print(f"Attempt {attempt + 1}: Error deleting session data for {session_id}: {e}")
                time.sleep(0.5)
                gc.collect()
        
        return False

    async def get_document_stats(self, session_id: str, filename: str) -> dict | None:
        """Get statistics about a specific document's chunks"""
        try:
            vectorstore = self._get_vectorstore(session_id)
            collection = vectorstore._collection
            
            # Count chunks for this specific file
            all_metadatas = collection.get(where={"source": filename}, include=['metadatas'])
            count = len(all_metadatas['metadatas']) if all_metadatas and 'metadatas' in all_metadatas else 0

            return {
                "filename": filename,
                "chunk_count": count,
                "session_id": session_id
            }
        except Exception as e:
            print(f"Error getting stats for {filename}: {e}")
            return None

    async def list_session_documents(self, session_id: str) -> list[str]:
        """List all documents in a session"""
        _, doc_path, _ = self._get_session_paths(session_id)

        if not os.path.exists(doc_path):
            return []

        return [f for f in os.listdir(doc_path) if os.path.isfile(os.path.join(doc_path, f))]


rag_service = RAGService()
