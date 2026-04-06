"""Knowledge Base RAG retrieval service.

Provides semantic search, keyword filtering, and hybrid retrieval
against Milvus vector database for the three knowledge bases:
- automation_case
- cost_model
- logistics_case
"""

import asyncio
import hashlib
import structlog
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential
from pymilvus import (
    connections,
    Collection,
    CollectionSchema,
    FieldSchema,
    DataType,
    utility,
)
import openai

from app.core.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

# Embedding dimension for text-embedding-3-small
EMBEDDING_DIM = 1536


class KnowledgeService:
    """RAG knowledge retrieval service backed by Milvus."""

    def __init__(
        self,
        milvus_host: str | None = None,
        milvus_port: int | None = None,
        embedding_model: str | None = None,
    ):
        self.milvus_host = milvus_host or settings.milvus_host
        self.milvus_port = milvus_port or settings.milvus_port
        self.embedding_model = embedding_model or settings.embedding_model
        self._connected = False

        # OpenAI client for embeddings
        self._openai = openai.AsyncOpenAI(api_key=settings.openai_api_key)

    # ──────────────────────────────────────────
    # Connection management
    # ──────────────────────────────────────────

    async def connect(self) -> None:
        """Establish connection to Milvus."""
        if self._connected:
            return
        try:
            await asyncio.to_thread(
                connections.connect,
                alias="default",
                host=self.milvus_host,
                port=self.milvus_port,
            )
            self._connected = True
            logger.info("milvus_connected", host=self.milvus_host, port=self.milvus_port)
        except Exception as e:
            logger.error("milvus_connection_failed", error=str(e))
            raise

    async def disconnect(self) -> None:
        """Close Milvus connection."""
        try:
            await asyncio.to_thread(connections.disconnect, alias="default")
            self._connected = False
        except Exception:
            pass

    # ──────────────────────────────────────────
    # Collection management
    # ──────────────────────────────────────────

    async def create_collection(
        self, collection_name: str, dimension: int = EMBEDDING_DIM
    ) -> None:
        """Create a Milvus collection with standard schema.

        Schema:
            - id:        VARCHAR(128), primary key
            - content:   VARCHAR(65535), document text
            - category:  VARCHAR(64), e.g. automation_case / cost_model / logistics_case
            - tags:      VARCHAR(512), comma-separated tags
            - metadata:  VARCHAR(8192), JSON string for extra fields
            - embedding: FLOAT_VECTOR(dimension)
        """
        await self.connect()

        exists = await asyncio.to_thread(utility.has_collection, collection_name)
        if exists:
            logger.info("collection_exists", name=collection_name)
            return

        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=128),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="category", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="tags", dtype=DataType.VARCHAR, max_length=512),
            FieldSchema(name="metadata", dtype=DataType.VARCHAR, max_length=8192),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dimension),
        ]
        schema = CollectionSchema(fields=fields, description=f"Knowledge base: {collection_name}")

        await asyncio.to_thread(Collection, name=collection_name, schema=schema)

        # Create IVF_FLAT index on embedding field
        collection = Collection(collection_name)
        index_params = {
            "index_type": "IVF_FLAT",
            "metric_type": "COSINE",
            "params": {"nlist": 128},
        }
        await asyncio.to_thread(
            collection.create_index, field_name="embedding", index_params=index_params
        )

        logger.info("collection_created", name=collection_name, dimension=dimension)

    # ──────────────────────────────────────────
    # Embedding generation
    # ──────────────────────────────────────────

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=15))
    async def _get_embedding(self, text: str) -> list[float]:
        """Generate embedding vector for a text string."""
        # Truncate to ~8000 tokens worth of text
        truncated = text[:16000]
        response = await self._openai.embeddings.create(
            model=self.embedding_model,
            input=truncated,
        )
        return response.data[0].embedding

    async def _get_embeddings_batch(self, texts: list[str], batch_size: int = 64) -> list[list[float]]:
        """Generate embeddings for multiple texts in batches."""
        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = [t[:16000] for t in texts[i : i + batch_size]]
            response = await self._openai.embeddings.create(
                model=self.embedding_model,
                input=batch,
            )
            all_embeddings.extend([d.embedding for d in response.data])
        return all_embeddings

    # ──────────────────────────────────────────
    # Indexing documents
    # ──────────────────────────────────────────

    async def index_documents(
        self, collection_name: str, documents: list[dict[str, Any]]
    ) -> int:
        """Index documents into Milvus.

        Args:
            collection_name: Target collection.
            documents: List of dicts with keys:
                - id (str): Unique document ID.
                - content (str): Document text.
                - category (str, optional): Document category.
                - tags (list[str], optional): Tag list.
                - metadata (dict, optional): Extra metadata.

        Returns:
            Number of documents indexed.
        """
        await self.connect()

        if not documents:
            return 0

        # Ensure collection exists
        await self.create_collection(collection_name)

        # Prepare data
        ids: list[str] = []
        contents: list[str] = []
        categories: list[str] = []
        tags_list: list[str] = []
        metadata_list: list[str] = []

        for doc in documents:
            doc_id = doc.get("id") or hashlib.md5(doc["content"][:500].encode()).hexdigest()
            ids.append(doc_id)
            contents.append(doc["content"][:65000])
            categories.append(doc.get("category", ""))
            tags_list.append(",".join(doc.get("tags", [])))

            import json
            meta = doc.get("metadata", {})
            metadata_list.append(json.dumps(meta, ensure_ascii=False, default=str)[:8000])

        # Generate embeddings
        logger.info("generating_embeddings", count=len(contents), collection=collection_name)
        embeddings = await self._get_embeddings_batch(contents)

        # Insert into Milvus
        collection = Collection(collection_name)
        data = [ids, contents, categories, tags_list, metadata_list, embeddings]
        await asyncio.to_thread(collection.insert, data)
        await asyncio.to_thread(collection.flush)

        logger.info("documents_indexed", count=len(ids), collection=collection_name)
        return len(ids)

    # ──────────────────────────────────────────
    # Semantic search
    # ──────────────────────────────────────────

    async def search(
        self,
        collection_name: str,
        query: str,
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Semantic search: query → embedding → ANN search.

        Args:
            collection_name: Collection to search.
            query: Natural language query.
            top_k: Number of results.
            filters: Optional field filters, e.g. {"category": "automation_case"}.

        Returns:
            List of results with id, content, score, category, tags, metadata.
        """
        await self.connect()

        query_embedding = await self._get_embedding(query)

        collection = Collection(collection_name)
        await asyncio.to_thread(collection.load)

        # Build filter expression
        expr = self._build_filter_expr(filters)

        search_params = {"metric_type": "COSINE", "params": {"nprobe": 16}}

        results = await asyncio.to_thread(
            collection.search,
            data=[query_embedding],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            expr=expr,
            output_fields=["content", "category", "tags", "metadata"],
        )

        return self._format_results(results)

    # ──────────────────────────────────────────
    # Hybrid search
    # ──────────────────────────────────────────

    async def hybrid_search(
        self,
        collection_name: str,
        query: str,
        keyword: str | None = None,
        top_k: int = 5,
        category: str | None = None,
    ) -> list[dict[str, Any]]:
        """Hybrid search: semantic search + keyword filter + re-ranking.

        Combines vector similarity with keyword matching for better precision.

        Args:
            collection_name: Collection to search.
            query: Natural language query for semantic matching.
            keyword: Optional keyword for content filtering.
            top_k: Number of results to return.
            category: Optional category filter.

        Returns:
            Re-ranked list of results.
        """
        await self.connect()

        # Step 1: Semantic search with 3x over-fetch for re-ranking pool
        semantic_results = await self.search(
            collection_name=collection_name,
            query=query,
            top_k=top_k * 3,
            filters={"category": category} if category else None,
        )

        if not semantic_results:
            return []

        # Step 2: Keyword boost — increase score for results containing the keyword
        if keyword:
            keyword_lower = keyword.lower()
            for result in semantic_results:
                content_lower = result["content"].lower()
                tags_lower = result.get("tags", "").lower()
                if keyword_lower in content_lower or keyword_lower in tags_lower:
                    result["score"] = min(result["score"] * 1.25, 1.0)

        # Step 3: Re-rank by adjusted score and return top_k
        semantic_results.sort(key=lambda r: r["score"], reverse=True)

        return semantic_results[:top_k]

    # ──────────────────────────────────────────
    # Delete
    # ──────────────────────────────────────────

    async def delete_documents(self, collection_name: str, ids: list[str]) -> int:
        """Delete documents by ID.

        Args:
            collection_name: Collection to delete from.
            ids: List of document IDs.

        Returns:
            Number of documents deleted.
        """
        await self.connect()

        collection = Collection(collection_name)
        id_list = ", ".join(f'"{i}"' for i in ids)
        expr = f"id in [{id_list}]"

        result = await asyncio.to_thread(collection.delete, expr=expr)
        await asyncio.to_thread(collection.flush)

        logger.info("documents_deleted", count=len(ids), collection=collection_name)
        return len(ids)

    # ──────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────

    @staticmethod
    def _build_filter_expr(filters: dict[str, Any] | None) -> str:
        """Build Milvus boolean filter expression from a dict."""
        if not filters:
            return ""
        parts: list[str] = []
        for key, value in filters.items():
            if value is None:
                continue
            if isinstance(value, str):
                parts.append(f'{key} == "{value}"')
            elif isinstance(value, list):
                vals = ", ".join(f'"{v}"' for v in value)
                parts.append(f"{key} in [{vals}]")
            else:
                parts.append(f"{key} == {value}")
        return " and ".join(parts) if parts else ""

    @staticmethod
    def _format_results(raw_results) -> list[dict[str, Any]]:
        """Format Milvus search results into clean dicts."""
        import json

        output: list[dict[str, Any]] = []
        if not raw_results or len(raw_results) == 0:
            return output

        for hit in raw_results[0]:
            entity = hit.entity
            meta_str = entity.get("metadata", "{}")
            try:
                metadata = json.loads(meta_str)
            except (json.JSONDecodeError, TypeError):
                metadata = {}

            output.append({
                "id": hit.id,
                "content": entity.get("content", ""),
                "score": round(hit.score, 4),
                "category": entity.get("category", ""),
                "tags": entity.get("tags", ""),
                "metadata": metadata,
            })

        return output


# ──────────────────────────────────────────
# Singleton
# ──────────────────────────────────────────

_knowledge_service: KnowledgeService | None = None


def get_knowledge_service() -> KnowledgeService:
    global _knowledge_service
    if _knowledge_service is None:
        _knowledge_service = KnowledgeService()
    return _knowledge_service
