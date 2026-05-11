from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import chromadb
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_core.documents import Document

EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
CHROMA_PATH = Path(os.getenv("CHROMA_PATH", "./data/chroma_db"))

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
        self._embeddings = OllamaEmbeddings(model=EMBED_MODEL)
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

    def _seed_policies(self) -> None:
        existing = self._policies.get(limit=1)
        if existing and existing["ids"]:
            return
        docs = [
            Document(page_content=p["text"], metadata=p["metadata"])
            for p in _SEED_POLICIES
        ]
        try:
            self._policies.add_documents(docs)
        except Exception as e:
            print(f"[vector_store] Could not seed policy documents: {e}")

    def search_policies(self, query: str, k: int = 3) -> list[Document]:
        return self._policies.similarity_search(query, k=k)

    def index_store_summaries(self, store) -> int:
        """Index per-class summaries from an AttendanceDataStore."""
        df = store.compute_stats("class", "all")
        if df.empty:
            return 0
        col = "class" if "class" in df.columns else df.columns[0]
        docs = [
            Document(
                page_content=(
                    f"Class {row[col]}: attendance rate {row['attendance_rate']:.1f}%. "
                    f"Total sessions: {int(row['total'])}. "
                    f"Present {int(row['present'])}, Absent {int(row['absent'])}, Late {int(row['late'])}."
                ),
                metadata={"class": str(row[col]), "type": "class_summary"},
            )
            for _, row in df.iterrows()
        ]
        try:
            self._records.add_documents(docs)
        except Exception as e:
            print(f"[vector_store] Could not index summaries: {e}")
            return 0
        return len(docs)

    def search_records(
        self,
        query: str,
        k: int = 4,
        allowed_classes: Optional[list[str]] = None,
    ) -> list[Document]:
        where = {"class": {"$in": allowed_classes}} if allowed_classes else None
        return self._records.similarity_search(query, k=k, filter=where)

    def format_docs(self, docs: list[Document]) -> str:
        if not docs:
            return "No relevant documents found."
        return "\n\n".join(
            f"[Source: {d.metadata.get('source', d.metadata.get('class', 'unknown'))}]\n{d.page_content}"
            for d in docs
        )
