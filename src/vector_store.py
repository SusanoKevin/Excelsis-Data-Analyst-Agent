"""
ChromaDB vector store backed by HuggingFace sentence-transformer embeddings.

Collections
-----------
policies            – intervention strategies, school attendance policies
attendance_summaries – per-class/student summaries indexed for semantic search

Security
--------
search_records() accepts an `allowed_classes` list; ChromaDB's metadata
$in filter ensures the query never touches rows outside that set.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import chromadb
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-base-en-v1.5")
CHROMA_PATH = Path(os.getenv("CHROMA_PATH", "./data/chroma_db"))

# Built-in seed documents for attendance intervention strategies
_SEED_POLICIES = [
    {
        "text": (
            "Early intervention for at-risk students (below 75% attendance): "
            "Contact parents within 3 absences. Assign a counselor check-in. "
            "Offer flexible scheduling and tutoring support."
        ),
        "metadata": {"category": "intervention", "source": "best_practice"},
    },
    {
        "text": (
            "Chronic absenteeism is defined as missing 10% or more of the school year. "
            "Research shows a strong correlation between chronic absenteeism and academic underperformance. "
            "Schools with attendance rates above 90% consistently outperform peers on standardised tests."
        ),
        "metadata": {"category": "research", "source": "best_practice"},
    },
    {
        "text": (
            "Positive attendance incentive programs — such as recognition assemblies, "
            "certificates, or small rewards for full-week attendance — reduce absenteeism "
            "by 15-20% in middle and high school cohorts."
        ),
        "metadata": {"category": "incentive", "source": "best_practice"},
    },
    {
        "text": (
            "Engage community partners and social services when students show patterns of "
            "excused absences tied to health or family instability. "
            "Coordinate with local clinics to provide on-campus healthcare access."
        ),
        "metadata": {"category": "community", "source": "best_practice"},
    },
    {
        "text": (
            "Data-driven attendance review meetings should occur monthly. "
            "Grade-level teams should review at-risk lists and assign responsibility "
            "for each flagged student to a named staff member."
        ),
        "metadata": {"category": "process", "source": "best_practice"},
    },
]


class AttendanceVectorStore:
    def __init__(self, persist_dir: str = str(CHROMA_PATH)) -> None:
        Path(persist_dir).mkdir(parents=True, exist_ok=True)
        self._persist_dir = persist_dir
        self._embeddings = HuggingFaceEmbeddings(
            model_name=EMBED_MODEL,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
        self._client = chromadb.PersistentClient(path=persist_dir)

        self._policies = Chroma(
            client=self._client,
            collection_name="policies",
            embedding_function=self._embeddings,
        )
        self._records = Chroma(
            client=self._client,
            collection_name="attendance_summaries",
            embedding_function=self._embeddings,
        )
        self._seed_policies()

    # ------------------------------------------------------------------
    # Policies collection
    # ------------------------------------------------------------------

    def _seed_policies(self) -> None:
        existing = self._policies.get(limit=1)
        if existing and existing["ids"]:
            return  # already seeded
        docs = [
            Document(page_content=p["text"], metadata=p["metadata"])
            for p in _SEED_POLICIES
        ]
        try:
            self._policies.add_documents(docs)
        except Exception as e:
            print(f"[vector_store] Could not seed policy documents (HF_TOKEN set?): {e}")

    def add_policy_docs(self, texts: list[str], metadatas: Optional[list[dict]] = None) -> None:
        metas = metadatas or [{} for _ in texts]
        docs = [Document(page_content=t, metadata=m) for t, m in zip(texts, metas)]
        self._policies.add_documents(docs)

    def search_policies(self, query: str, k: int = 3) -> list[Document]:
        return self._policies.similarity_search(query, k=k)

    # ------------------------------------------------------------------
    # Attendance summaries collection (security-aware)
    # ------------------------------------------------------------------

    def index_store_summaries(self, store) -> int:
        """Index per-class summaries from an AttendanceDataStore."""
        df = store.compute_stats("class", "all")
        if df.empty:
            return 0
        col = "class" if "class" in df.columns else df.columns[0]
        docs: list[Document] = []
        for _, row in df.iterrows():
            text = (
                f"Class {row[col]}: attendance rate {row['attendance_rate']:.1f}%. "
                f"Total sessions: {int(row['total'])}. "
                f"Present {int(row['present'])}, Absent {int(row['absent'])}, Late {int(row['late'])}."
            )
            docs.append(
                Document(
                    page_content=text,
                    metadata={"class": str(row[col]), "type": "class_summary"},
                )
            )
        try:
            self._records.add_documents(docs)
        except Exception as e:
            print(f"[vector_store] Could not index summaries (HF_TOKEN set?): {e}")
            return 0
        return len(docs)

    def search_records(
        self,
        query: str,
        k: int = 4,
        allowed_classes: Optional[list[str]] = None,
    ) -> list[Document]:
        """
        Semantic search over attendance summaries.
        If allowed_classes is provided, results are restricted to those classes —
        ChromaDB's metadata filter enforces this at the database layer.
        """
        where = {"class": {"$in": allowed_classes}} if allowed_classes else None
        return self._records.similarity_search(query, k=k, filter=where)

    def format_docs(self, docs: list[Document]) -> str:
        if not docs:
            return "No relevant documents found."
        return "\n\n".join(
            f"[Source: {d.metadata.get('source', d.metadata.get('class', 'unknown'))}]\n{d.page_content}"
            for d in docs
        )
