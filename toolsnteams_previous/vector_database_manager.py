import asyncio
import re
import hashlib
import logging
import random
import time
import os

# Avoid importing config module to prevent PYTHONPATH/package issues in containers.
# Read from environment with safe defaults matching config/config.py.
QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
try:
    QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
except ValueError:
    QDRANT_PORT = 6333
try:
    QDRANT_READY_TIMEOUT = float(os.getenv("QDRANT_READY_TIMEOUT", "8.0"))
except Exception:
    QDRANT_READY_TIMEOUT = 8.0

# Optional tuning via environment
EMBED_BACKEND = os.getenv("VDB_EMBEDDINGS_BACKEND", "sentence").strip().lower()
try:
    BATCH_SIZE_ENV = int(os.getenv("VDB_EMBED_BATCH_SIZE", "256"))
except ValueError:
    BATCH_SIZE_ENV = 256

try:  # pragma: no cover - optional
    from qdrant_client import QdrantClient
    from qdrant_client.http.models import (
        Distance,
        FieldCondition,
        Filter,
        MatchValue,
        PointIdsList,
        PointStruct,
        VectorParams,
    )
except Exception:  # pragma: no cover - qdrant not available
    QdrantClient = None
    Distance = FieldCondition = Filter = MatchValue = PointIdsList = PointStruct = VectorParams = None


from neuro_san.interfaces.coded_tool import CodedTool


class _HashEmbedder:
    """Deterministic fallback embedder using SHA256 hashes."""

    def __init__(self, dim: int = 384) -> None:
        self.dim = dim

    def _embed(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        # Repeat digest to fill dimension and normalise to [0,1]
        data = (digest * ((self.dim // len(digest)) + 1))[: self.dim]
        return [b / 255 for b in data]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:  # pragma: no cover - simple
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:  # pragma: no cover - simple
        return self._embed(text)


class _InMemoryCollection:
    """Minimal stand‑in for a vector collection."""

    def __init__(self) -> None:
        self._docs: dict[str, dict] = {}

    def add(
        self,
        documents: list[str],
        metadatas: list[dict],
        ids: list[str],
        embeddings: list[list[float]] | None = None,
    ) -> None:
        for doc, md, _id in zip(documents, metadatas, ids):
            self._docs[_id] = {"document": doc, "metadata": md}

    def query(
        self,
        query_texts: list[str] | None = None,
        query_embeddings: list[list[float]] | None = None,
        n_results: int = 10,
        where: dict | None = None,
    ) -> dict:
        docs = []
        metas = []
        ids = []
        for _id, data in self._docs.items():
            md = data["metadata"]
            if where and md.get("visibility") != where.get("visibility"):
                continue
            docs.append(data["document"])
            metas.append(md | {"id": _id})
            ids.append(_id)
            if len(docs) >= n_results:
                break
        return {"documents": [docs], "metadatas": [metas], "ids": [ids]}

    def get(self, ids: list[str]) -> dict:  # pragma: no cover - trivial
        found = [_id for _id in ids if _id in self._docs]
        return {"ids": found}

    def delete(self, ids: list[str]) -> None:  # pragma: no cover - trivial
        for _id in ids:
            self._docs.pop(_id, None)

    def count(self) -> int:  # pragma: no cover - trivial
        return len(self._docs)

    def persist(self) -> None:  # pragma: no cover - no-op
        return None


class _InMemoryClient:
    """Process-local in-memory vector store with named collections.

    Note: Persisted only for the lifetime of the process. Collections are reused
    by name to ensure counts reflect prior inserts across manager instances.
    """

    def __init__(self) -> None:
        self._collections: dict[str, _InMemoryCollection] = {}

    def get_or_create_collection(self, name: str) -> _InMemoryCollection:  # pragma: no cover - simple
        coll = self._collections.get(name)
        if coll is None:
            coll = _InMemoryCollection()
            self._collections[name] = coll
        return coll


_GLOBAL_CLIENT = None
_GLOBAL_EMBEDDER = None  # process-wide cache for SentenceTransformer wrapper


class VectorDatabaseManager(CodedTool):
    """Vector DB manager preferring Qdrant with graceful fallbacks."""

    def __init__(self, case_id: int | str | None = None, **kwargs):
        super().__init__(**kwargs)
        # normalize case_id to a safe string segment
        self.case_id = str(case_id) if case_id is not None else "default"
        self.embedder = self._init_embedder()
        # Default embedding dimension from internal embedder; may be overridden
        self.dim = len(self.embedder.embed_documents(["dimension"])[0])
        self.use_qdrant = False

        if QdrantClient is not None:
            try:
                self.client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
                # Actively verify the service is reachable; the client
                # constructor does not perform a network call so a missing
                # server would otherwise surface later during queries.
                if self._qdrant_ready():
                    self.use_qdrant = True
                else:
                    raise RuntimeError("/readyz returned non-200 or not ok")
            except Exception as exc:  # pragma: no cover - best effort
                logging.warning("Qdrant unavailable (%s); falling back", exc)

        if not self.use_qdrant:
            self._init_fallback()

        # For compatibility with previous code paths, compute per-case names
        if self.use_qdrant:
            self.collection = self._make_collection_name("legal_documents")
            self.msg_collection = self._make_collection_name("chat_messages")
            self.convo_collection = self._make_collection_name("conversations")

        self._query_cache: dict[tuple, dict] = {}
        self._msg_cache: dict[tuple, dict] = {}
        self._convo_cache: dict[tuple, dict] = {}

    # ---- initialisation helpers -------------------------------------------

    def _init_embedder(self):  # pragma: no cover - simple
        global _GLOBAL_EMBEDDER
        if _GLOBAL_EMBEDDER is not None:
            return _GLOBAL_EMBEDDER
        # Allow forcing a lightweight hash-based embedder via env
        if EMBED_BACKEND != "sentence":
            _GLOBAL_EMBEDDER = _HashEmbedder()
            return _GLOBAL_EMBEDDER
        try:
            from sentence_transformers import SentenceTransformer

            model = SentenceTransformer("all-MiniLM-L6-v2")

            class _STEmbedder:
                def __init__(self, m):
                    self.m = m

                def embed_documents(self, texts: list[str]) -> list[list[float]]:
                    return self.m.encode(texts, normalize_embeddings=True).tolist()

                def embed_query(self, text: str) -> list[float]:
                    return self.m.encode([text], normalize_embeddings=True)[0].tolist()

            _GLOBAL_EMBEDDER = _STEmbedder(model)
            return _GLOBAL_EMBEDDER
        except Exception:  # pragma: no cover - fallback
            _GLOBAL_EMBEDDER = _HashEmbedder()
            return _GLOBAL_EMBEDDER

    def _qdrant_ready(self) -> bool:
        """Return True if Qdrant responds healthy.

        Supports multiple client versions by probing available paths, and falls
        back to a direct HTTP GET to `/readyz`.
        """
        # Try client-provided health method if present
        try:
            http = getattr(self.client, "http", None)
            if http is not None and hasattr(http, "readyz"):
                try:
                    http.readyz()  # type: ignore[call-arg]
                    return True
                except Exception:
                    pass
        except Exception:
            pass

        # Fallback: direct HTTP GET to /readyz
        url = f"http://{QDRANT_HOST}:{QDRANT_PORT}/readyz"
        try:
            try:
                import requests  # type: ignore

                resp = requests.get(url, timeout=QDRANT_READY_TIMEOUT)
                if resp.status_code == 200:
                    return True
            except Exception:
                # No requests or it failed; try urllib
                import urllib.request  # type: ignore

                with urllib.request.urlopen(url, timeout=QDRANT_READY_TIMEOUT) as r:  # nosec B310
                    if getattr(r, "status", None) == 200:
                        return True
        except Exception:
            return False
        return False

    def _init_fallback(self) -> None:
        global _GLOBAL_CLIENT
        if _GLOBAL_CLIENT is None:
            _GLOBAL_CLIENT = _InMemoryClient()
        self.client = _GLOBAL_CLIENT
        self.collection = self.client.get_or_create_collection(self._make_collection_name("legal_documents"))
        self.msg_collection = self.client.get_or_create_collection(self._make_collection_name("chat_messages"))
        self.convo_collection = self.client.get_or_create_collection(self._make_collection_name("conversations"))

    # ---- utility ----------------------------------------------------------

    def _invalidate_cache(self) -> None:
        self._query_cache.clear()
        self._msg_cache.clear()
        self._convo_cache.clear()

    def _ensure_qdrant_collection(self, name: str, dim: int) -> None:
        """Create a Qdrant collection if missing with the given dimension."""
        if not self.use_qdrant:
            return
        try:
            self.client.get_collection(name)
        except Exception:
            self.client.create_collection(
                name, vectors_config=VectorParams(size=dim, distance=Distance.COSINE)
            )

    def _make_collection_name(self, base: str) -> str:
        """Return per-case collection name for Qdrant or in-memory store."""
        safe_case = re.sub(r"[^a-zA-Z0-9_\-]", "_", self.case_id)
        return f"{base}_case_{safe_case}"

    def _build_filter(self, where: dict | None):
        if not where or not self.use_qdrant:
            return None
        conditions = [
            FieldCondition(key=k, match=MatchValue(value=v)) for k, v in where.items()
        ]
        return Filter(must=conditions)

    def _with_retry(self, func, *args, max_retries: int = 4, base_delay: float = 0.25, **kwargs):
        last_exc: Exception | None = None
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as exc:  # pragma: no cover - best effort
                last_exc = exc
                delay = base_delay * (2 ** attempt) + random.uniform(0, base_delay)
                logging.warning("vector op failed (%s); retrying in %.2fs", exc, delay)
                time.sleep(delay)
        if last_exc:
            raise last_exc
        return None

    def persist(self) -> None:  # pragma: no cover - best effort
        try:
            if not self.use_qdrant:
                self.client.persist()
        except Exception as exc:
            logging.warning("Vector DB persist failed: %s", exc)

    # ---- document operations ---------------------------------------------

    def add_documents(
        self,
        documents: list[str],
        metadatas: list[dict],
        ids: list[str],
        embeddings: list[list[float]] | None = None,
    ) -> None:
        if self.use_qdrant:
            total = len(documents)
            if len(metadatas) < total:
                metadatas = metadatas + [{}] * (total - len(metadatas))
            if embeddings is None:
                embeddings = self.embedder.embed_documents(documents)
            elif len(embeddings) < total:
                embeddings = embeddings + self.embedder.embed_documents(
                    documents[len(embeddings) :]
                )
            self._ensure_qdrant_collection(self.collection, len(embeddings[0]))
            points = [
                PointStruct(
                    id=ids[i],
                    vector=embeddings[i],
                    payload=metadatas[i] | {"document": documents[i]},
                )
                for i in range(total)
            ]
            self.client.upsert(collection_name=self.collection, points=points)
        else:
            # existing logic with metadata padding
            safe_docs: list[str] = []
            safe_metadatas: list[dict] = []
            safe_ids: list[str] = []
            safe_embeddings: list[list[float]] = []

            if len(metadatas) < len(documents):
                metadatas = metadatas + [{}] * (len(documents) - len(metadatas))

            emb_iter = embeddings or [None] * len(documents)
            for doc, md, doc_id, emb in zip(documents, metadatas, ids, emb_iter):
                try:
                    existing = self.collection.get(ids=[doc_id])
                    if existing and existing.get("ids"):
                        continue
                except Exception:
                    pass

                safe_docs.append(doc)
                safe_ids.append(doc_id)
                if emb is not None:
                    safe_embeddings.append(emb)
                if not isinstance(md, dict) or not md:
                    safe_metadatas.append({"source": "unknown", "id": doc_id})
                else:
                    cleaned = {k: v for k, v in md.items() if v}
                    safe_metadatas.append(cleaned or {"source": "unknown", "id": doc_id})

            if not safe_docs:
                return

            if embeddings:
                self._with_retry(
                    self.collection.add,
                    documents=safe_docs,
                    metadatas=safe_metadatas,
                    ids=safe_ids,
                    embeddings=safe_embeddings,
                )
            else:
                self._with_retry(
                    self.collection.add,
                    documents=safe_docs,
                    metadatas=safe_metadatas,
                    ids=safe_ids,
                )
        self._invalidate_cache()

    def add_documents_batched(
        self,
        documents: list[str],
        metadatas: list[dict],
        ids: list[str],
        embeddings: list[list[float]] | None = None,
        batch_size: int = 256,
    ) -> None:
        # Respect env-configured default batch size when callers pass non-positive value
        try:
            bs = int(batch_size)
        except Exception:
            bs = BATCH_SIZE_ENV
        if bs <= 0:
            bs = BATCH_SIZE_ENV
        total = len(documents)
        if len(metadatas) < total:
            metadatas = metadatas + [{}] * (total - len(metadatas))
        if embeddings is not None and len(embeddings) < total:
            embeddings = embeddings + [[]] * (total - len(embeddings))  # type: ignore

        for i in range(0, total, bs):
            j = min(i + bs, total)
            docs = documents[i:j]
            mds = metadatas[i:j]
            _ids = ids[i:j]
            embs = embeddings[i:j] if embeddings is not None else None
            self.add_documents(docs, mds, _ids, embs)
        try:
            self.persist()
        except Exception:
            pass

    async def aadd_documents(
        self,
        documents: list[str],
        metadatas: list[dict],
        ids: list[str],
        embeddings: list[list[float]] | None = None,
    ) -> None:
        await asyncio.to_thread(self.add_documents, documents, metadatas, ids, embeddings)

    def query(
        self,
        query_texts: list[str],
        n_results: int = 10,
        where: dict | None = None,
    ) -> dict:
        key = (tuple(query_texts), n_results, frozenset(where.items()) if where else None)
        if key in self._query_cache:
            return self._query_cache[key]

        if self.use_qdrant:
            vector = self.embedder.embed_query(query_texts[0])
            flt = self._build_filter(where)
            hits = self.client.search(
                collection_name=self.collection,
                query_vector=vector,
                limit=n_results,
                query_filter=flt,
                with_payload=True,
            )
            docs = [h.payload.get("document", "") for h in hits]
            metas = [
                {k: v for k, v in (h.payload or {}).items() if k != "document"}
                for h in hits
            ]
            ids = [str(h.id) for h in hits]
            result = {"documents": [docs], "metadatas": [metas], "ids": [ids]}
        else:
            result = self.collection.query(
                query_texts=query_texts, n_results=n_results, where=where
            )

        self._query_cache[key] = result
        return result

    def get_document_count(self) -> int:
        if self.use_qdrant:
            try:
                return self.client.count(self.collection, exact=True).count  # type: ignore[attr-defined]
            except Exception:
                # Fallback to 0 on transient errors; callers treat as advisory
                return 0
        return self.collection.count()

    def delete_documents(self, ids: list[str]) -> None:
        if self.use_qdrant:
            self.client.delete(
                collection_name=self.collection,
                points_selector=PointIdsList(points=ids),
            )
        else:
            self.collection.delete(ids=ids)
        self._invalidate_cache()

    # ---- message operations ----------------------------------------------

    def add_messages(
        self,
        messages: list[str],
        metadatas: list[dict],
        ids: list[str],
        embeddings: list[list[float]] | None = None,
    ) -> None:
        if self.use_qdrant:
            total = len(messages)
            if len(metadatas) < total:
                metadatas = metadatas + [{}] * (total - len(metadatas))
            if embeddings is None:
                embeddings = self.embedder.embed_documents(messages)
            elif len(embeddings) < total:
                embeddings = embeddings + self.embedder.embed_documents(
                    messages[len(embeddings) :]
                )
            self._ensure_qdrant_collection(self.msg_collection, len(embeddings[0]))
            payloads = []
            for i in range(total):
                md = metadatas[i] if isinstance(metadatas[i], dict) else {}
                md.setdefault("visibility", "public")
                payloads.append(md | {"message": messages[i]})
            points = [
                PointStruct(id=ids[i], vector=embeddings[i], payload=payloads[i])
                for i in range(total)
            ]
            self.client.upsert(collection_name=self.msg_collection, points=points)
        else:
            if len(metadatas) < len(messages):
                metadatas = metadatas + [{}] * (len(messages) - len(metadatas))
            safe_md = []
            for md, mid in zip(metadatas, ids):
                if not isinstance(md, dict) or not md:
                    safe_md.append({"message_id": mid, "visibility": "public"})
                else:
                    md.setdefault("visibility", "public")
                    safe_md.append(md)
            if embeddings is None:
                embeddings = self.embedder.embed_documents(messages)
            self.msg_collection.add(
                documents=messages,
                metadatas=safe_md,
                ids=ids,
                embeddings=embeddings,
            )
        self._invalidate_cache()

    async def aadd_messages(
        self,
        messages: list[str],
        metadatas: list[dict],
        ids: list[str],
        embeddings: list[list[float]] | None = None,
    ) -> None:
        await asyncio.to_thread(self.add_messages, messages, metadatas, ids, embeddings)

    def add_conversations(
        self,
        texts: list[str],
        metadatas: list[dict],
        ids: list[str],
        embeddings: list[list[float]] | None = None,
    ) -> None:
        if self.use_qdrant:
            total = len(texts)
            if len(metadatas) < total:
                metadatas = metadatas + [{}] * (total - len(metadatas))
            if embeddings is None:
                embeddings = self.embedder.embed_documents(texts)
            elif len(embeddings) < total:
                embeddings = embeddings + self.embedder.embed_documents(
                    texts[len(embeddings) :]
                )
            self._ensure_qdrant_collection(self.convo_collection, len(embeddings[0]))
            points = [
                PointStruct(
                    id=ids[i],
                    vector=embeddings[i],
                    payload=metadatas[i] | {"conversation": texts[i]},
                )
                for i in range(total)
            ]
            self.client.upsert(collection_name=self.convo_collection, points=points)
        else:
            if len(metadatas) < len(texts):
                metadatas = metadatas + [{}] * (len(texts) - len(metadatas))
            if embeddings is None:
                embeddings = self.embedder.embed_documents(texts)
            self.convo_collection.add(
                documents=texts,
                metadatas=metadatas,
                ids=ids,
                embeddings=embeddings,
            )
        self._invalidate_cache()

    async def aadd_conversations(
        self,
        texts: list[str],
        metadatas: list[dict],
        ids: list[str],
        embeddings: list[list[float]] | None = None,
    ) -> None:
        await asyncio.to_thread(self.add_conversations, texts, metadatas, ids, embeddings)

    def query_messages(
        self,
        query_texts: list[str] | None = None,
        n_results: int = 10,
        where: dict | None = None,
        query_embeddings: list[list[float]] | None = None,
    ) -> dict:
        key = (
            tuple(query_texts) if query_texts else None,
            n_results,
            frozenset(where.items()) if where else None,
            tuple(map(tuple, query_embeddings)) if query_embeddings else None,
        )
        if key in self._msg_cache:
            return self._msg_cache[key]

        if self.use_qdrant:
            if query_embeddings is None:
                query_embeddings = [self.embedder.embed_query(query_texts[0])]
            flt = self._build_filter(where)
            hits = self.client.search(
                collection_name=self.msg_collection,
                query_vector=query_embeddings[0],
                limit=n_results,
                query_filter=flt,
                with_payload=True,
            )
            docs = [h.payload.get("message", "") for h in hits]
            metas = [
                {k: v for k, v in (h.payload or {}).items() if k != "message"}
                for h in hits
            ]
            ids = [str(h.id) for h in hits]
            result = {"documents": [docs], "metadatas": [metas], "ids": [ids]}
        else:
            result = self.msg_collection.query(
                query_texts=query_texts if query_embeddings is None else None,
                query_embeddings=query_embeddings,
                n_results=n_results,
                where=where,
            )
        self._msg_cache[key] = result
        return result

    def query_conversations(
        self,
        query_texts: list[str],
        n_results: int = 10,
        where: dict | None = None,
    ) -> dict:
        key = (tuple(query_texts), n_results, frozenset(where.items()) if where else None)
        if key in self._convo_cache:
            return self._convo_cache[key]

        if self.use_qdrant:
            vector = self.embedder.embed_query(query_texts[0])
            flt = self._build_filter(where)
            hits = self.client.search(
                collection_name=self.convo_collection,
                query_vector=vector,
                limit=n_results,
                query_filter=flt,
                with_payload=True,
            )
            docs = [h.payload.get("conversation", "") for h in hits]
            metas = [
                {k: v for k, v in (h.payload or {}).items() if k != "conversation"}
                for h in hits
            ]
            ids = [str(h.id) for h in hits]
            result = {"documents": [docs], "metadatas": [metas], "ids": [ids]}
        else:
            result = self.convo_collection.query(
                query_texts=query_texts, n_results=n_results, where=where
            )
        self._convo_cache[key] = result
        return result

    # ---- async wrappers ---------------------------------------------------

    async def aquery(
        self, query_texts: list[str], n_results: int = 10, where: dict | None = None
    ) -> dict:
        return await asyncio.to_thread(self.query, query_texts, n_results, where)

    async def aquery_messages(
        self,
        query_texts: list[str] | None = None,
        n_results: int = 10,
        where: dict | None = None,
        query_embeddings: list[list[float]] | None = None,
    ) -> dict:
        return await asyncio.to_thread(
            self.query_messages, query_texts, n_results, where, query_embeddings
        )

    async def aquery_conversations(
        self, query_texts: list[str], n_results: int = 10, where: dict | None = None
    ) -> dict:
        return await asyncio.to_thread(self.query_conversations, query_texts, n_results, where)

