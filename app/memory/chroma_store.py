import hashlib
import os
from typing import Dict, Any, Optional, List
from datetime import datetime


EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_VERSION = "v1"


def _get_embedding(text: str) -> List[float]:
    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(EMBEDDING_MODEL)
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    except Exception:
        return [0.0] * 384


def _compute_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


class ChromaMemoryStore:
    _instance = None
    _client = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _initialize(self):
        if self._initialized:
            return
        try:
            import chromadb

            chroma_path = os.environ.get("CHROMA_PERSIST_DIR", "./chroma_data")
            self._client = chromadb.PersistentClient(path=chroma_path)
            self._setup_collections()
            self._initialized = True
        except Exception:
            self._client = None

    def _setup_collections(self):
        if not self._client:
            return
        self._repo_patterns = self._client.get_or_create_collection(
            "repo_patterns",
            metadata={
                "description": "Repository pattern embeddings",
                "version": EMBEDDING_VERSION,
            },
        )
        self._successful_strategies = self._client.get_or_create_collection(
            "successful_strategies",
            metadata={
                "description": "Successful recovery strategies",
                "version": EMBEDDING_VERSION,
            },
        )
        self._failure_memory = self._client.get_or_create_collection(
            "failure_memory",
            metadata={
                "description": "Failure signatures and strategies",
                "version": EMBEDDING_VERSION,
            },
        )

    def store_repo_pattern(
        self,
        repo_type: str,
        language: str,
        size_bucket: str,
        pattern_text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        if not self._client:
            return ""
        doc_id = _compute_hash(f"{repo_type}:{language}:{size_bucket}:{pattern_text}")
        embedding = _get_embedding(pattern_text)
        self._repo_patterns.add(
            ids=[doc_id],
            embeddings=[embedding],
            documents=[pattern_text],
            metadatas=[
                {
                    "repo_type": repo_type,
                    "language": language,
                    "size_bucket": size_bucket,
                    "embedding_version": EMBEDDING_VERSION,
                    "created_at": datetime.utcnow().isoformat(),
                    **(metadata or {}),
                }
            ],
        )
        return doc_id

    def query_repo_patterns(
        self,
        query_text: str,
        repo_type: Optional[str] = None,
        language: Optional[str] = None,
        n_results: int = 3,
    ) -> List[Dict[str, Any]]:
        if not self._client:
            return []
        embedding = _get_embedding(query_text)
        where = {}
        if repo_type:
            where["repo_type"] = repo_type
        if language:
            where["language"] = language
        results = self._repo_patterns.query(
            query_embeddings=[embedding],
            n_results=n_results,
            where=where if where else None,
        )
        return self._format_results(results)

    def store_successful_strategy(
        self,
        error_signature: str,
        strategy: str,
        repo_type: str,
        language: str,
        failure_class: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        if not self._client:
            return ""
        doc_id = _compute_hash(f"success:{error_signature}:{strategy}")
        embedding = _get_embedding(error_signature)
        self._successful_strategies.add(
            ids=[doc_id],
            embeddings=[embedding],
            documents=[f"Error: {error_signature}\nStrategy: {strategy}"],
            metadatas=[
                {
                    "strategy": strategy,
                    "repo_type": repo_type,
                    "language": language,
                    "failure_class": failure_class,
                    "embedding_version": EMBEDDING_VERSION,
                    "success_count": 1,
                    "created_at": datetime.utcnow().isoformat(),
                    **(metadata or {}),
                }
            ],
        )
        return doc_id

    def query_successful_strategies(
        self, error_signature: str, n_results: int = 3
    ) -> List[Dict[str, Any]]:
        if not self._client:
            return []
        embedding = _get_embedding(error_signature)
        results = self._successful_strategies.query(
            query_embeddings=[embedding], n_results=n_results
        )
        return self._format_results(results)

    def store_failure_memory(
        self,
        error_signature: str,
        failed_step: str,
        repo_type: str,
        language: str,
        failure_class: str,
        stack_trace_hash: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        if not self._client:
            return ""
        doc_id = _compute_hash(f"failure:{stack_trace_hash}")
        embedding = _get_embedding(error_signature)
        self._failure_memory.add(
            ids=[doc_id],
            embeddings=[embedding],
            documents=[error_signature],
            metadatas=[
                {
                    "error_signature": error_signature,
                    "failed_step": failed_step,
                    "repo_type": repo_type,
                    "language": language,
                    "failure_class": failure_class,
                    "stack_trace_hash": stack_trace_hash,
                    "embedding_version": EMBEDDING_VERSION,
                    "created_at": datetime.utcnow().isoformat(),
                    "failure_count": 1,
                    **(metadata or {}),
                }
            ],
        )
        return doc_id

    def query_failure_memory(
        self, error_signature: str, threshold: float = 0.85, n_results: int = 5
    ) -> List[Dict[str, Any]]:
        if not self._client:
            return []
        embedding = _get_embedding(error_signature)
        results = self._failure_memory.query(
            query_embeddings=[embedding], n_results=n_results
        )
        filtered = self._format_results(results)
        return [r for r in filtered if r.get("confidence", 0) >= threshold]

    def _format_results(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not results or not results.get("ids"):
            return []
        formatted = []
        for i, doc_id in enumerate(results["ids"][0]):
            formatted.append(
                {
                    "id": doc_id,
                    "document": results["documents"][0][i]
                    if results["documents"]
                    else "",
                    "metadata": results["metadatas"][0][i]
                    if results["metadatas"]
                    else {},
                    "distance": results["distances"][0][i]
                    if results.get("distances")
                    else 1.0,
                    "confidence": 1.0
                    - (results["distances"][0][i] if results.get("distances") else 1.0),
                }
            )
        return formatted


def get_chroma_store() -> ChromaMemoryStore:
    store = ChromaMemoryStore()
    store._initialize()
    return store
