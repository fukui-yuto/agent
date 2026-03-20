"""Long-term memory using ChromaDB for vector search, scoped per project."""
import uuid
from datetime import datetime

from agent.config import config, CHROMA_DIR, PROJECT_SESSION_ID
from agent.utils.logger import log_memory, log_warning


class LongTermMemory:
    def __init__(self, llm_client=None, project_id: str = None):
        self._collection = None
        self._llm = llm_client
        self._available = False
        self._project_id = project_id or PROJECT_SESSION_ID
        self._setup()

    def _setup(self) -> None:
        try:
            import chromadb
            client = chromadb.PersistentClient(path=str(CHROMA_DIR))
            # Collection name is scoped to the project
            collection_name = f"memory_{self._project_id}"
            self._collection = client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            self._available = True
            log_memory(f"Long-term memory loaded ({self._collection.count()} entries) [{self._project_id}]")
        except ImportError:
            log_warning("chromadb not installed. Long-term memory disabled.")
        except Exception as e:
            log_warning(f"Long-term memory unavailable: {e}")

    def _embed(self, text: str) -> list[float]:
        if self._llm:
            return self._llm.embed(text)
        return []

    def save(self, content: str, category: str = "general") -> None:
        if not self._available:
            return
        embedding = self._embed(content)
        doc_id = str(uuid.uuid4())
        kwargs = dict(
            documents=[content],
            ids=[doc_id],
            metadatas=[{"category": category, "timestamp": datetime.now().isoformat()}],
        )
        if embedding:
            kwargs["embeddings"] = [embedding]
        self._collection.add(**kwargs)

    def search(self, query: str, k: int = None) -> list[str]:
        if not self._available or self._collection.count() == 0:
            return []
        k = k or config.memory_top_k
        embedding = self._embed(query)
        if embedding:
            kwargs = dict(query_embeddings=[embedding],
                          n_results=min(k, self._collection.count()))
        else:
            kwargs = dict(query_texts=[query],
                          n_results=min(k, self._collection.count()))
        try:
            results = self._collection.query(**kwargs)
            return results["documents"][0] if results["documents"] else []
        except Exception as e:
            log_warning(f"Memory search error: {e}")
            return []

    def all(self) -> list[str]:
        if not self._available:
            return []
        results = self._collection.get()
        return results.get("documents", [])

    @property
    def available(self) -> bool:
        return self._available
