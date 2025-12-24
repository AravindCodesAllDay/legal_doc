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
            chunk_size=1000,
            chunk_overlap=200,
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

    def _get_collection_name(self, session_id: str, filename: str) -> str:
        """Generate a unique collection name for each document"""
        # Sanitize filename for collection name (remove special chars)
        safe_filename = filename.replace(
            ".", "_").replace(" ", "_").replace("-", "_")
        return f"session_{session_id}_doc_{safe_filename}"

    def _get_vectorstore(self, session_id: str, filename: str) -> Chroma:
        """Get vectorstore for a specific document in a session"""
        _, _, chroma_path = self._get_session_paths(session_id)
        collection_name = self._get_collection_name(session_id, filename)

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

        # Store in vectorstore (separate collection per document)
        try:
            vectorstore = self._get_vectorstore(session_id, filename)
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
        use_mmr: bool = True
    ) -> list[Document]:
        """
        Query documents in a session with enhanced retrieval

        Args:
            query: The search query
            session_id: Session identifier
            filenames: Optional list of specific filenames to search. If None, searches all.
            k: Number of results to return
            use_mmr: Whether to use Maximal Marginal Relevance for diversity
        """
        if not filenames:
            # Get all documents in session (physical files)
            _, doc_path, _ = self._get_session_paths(session_id)
            if not os.path.exists(doc_path):
                return []
            filenames = [f for f in os.listdir(
                doc_path) if os.path.isfile(os.path.join(doc_path, f))]

        if not filenames:
            return []

        all_results = []
        # Distribute k across documents
        results_per_doc = max(2, k // len(filenames))

        for filename in filenames:
            try:
                vectorstore = self._get_vectorstore(session_id, filename)

                if use_mmr:
                    # Use MMR for diversity
                    results = vectorstore.max_marginal_relevance_search(
                        query,
                        k=results_per_doc,
                        fetch_k=results_per_doc * 3
                    )
                else:
                    # Simple similarity search
                    results = vectorstore.similarity_search(
                        query, k=results_per_doc)

                all_results.extend(results)

            except Exception as e:
                print(f"Warning: Error querying document {filename}: {e}")
                continue

        # Return top k results
        return all_results[:k]

    async def query_with_scores(
        self,
        query: str,
        session_id: str,
        filenames: list[str] | None = None,
        k: int = 5
    ) -> list[tuple[Document, float]]:
        """Query with similarity scores for better ranking"""
        if not filenames:
            _, doc_path, _ = self._get_session_paths(session_id)
            if not os.path.exists(doc_path):
                return []
            filenames = [f for f in os.listdir(
                doc_path) if os.path.isfile(os.path.join(doc_path, f))]

        if not filenames:
            return []

        all_results = []
        results_per_doc = max(2, k // len(filenames))

        for filename in filenames:
            try:
                vectorstore = self._get_vectorstore(session_id, filename)
                results = vectorstore.similarity_search_with_score(
                    query,
                    k=results_per_doc
                )
                all_results.extend(results)
            except Exception as e:
                print(f"Warning: Error querying document {filename}: {e}")
                continue

        # Sort by score (lower is better for distance metrics)
        all_results.sort(key=lambda x: x[1])
        return all_results[:k]

    async def delete_document(self, session_id: str, filename: str) -> bool:
        """
        Delete a specific document and its vectorstore collection
        Returns True if successful, False otherwise
        """
        success = True

        # Delete vectorstore collection
        try:
            _, _, chroma_path = self._get_session_paths(session_id)
            if os.path.exists(chroma_path):
                vectorstore = self._get_vectorstore(session_id, filename)
                vectorstore.delete_collection()
                # Explicitly try to clean up chroma client if possible
                # Chromadb sometimes locks files on Windows
                gc.collect() 
                print(f"Deleted collection for {filename}")
        except Exception as e:
            print(f"Error deleting vectorstore collection for {filename}: {e}")
            success = False

        # Keep physical file as requested
        print(f"Preserved physical file {filename}, only ChromaDB content removed.")

        return success

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
        """Get statistics about a specific document"""
        try:
            vectorstore = self._get_vectorstore(session_id, filename)
            collection = vectorstore._collection
            count = collection.count()

            # Get a sample document for metadata
            results = vectorstore.similarity_search("", k=1)
            metadata = results[0].metadata if results else {}

            return {
                "filename": filename,
                "chunk_count": count,
                "metadata": metadata
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
