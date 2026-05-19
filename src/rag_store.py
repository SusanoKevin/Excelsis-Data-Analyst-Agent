from __future__ import annotations

from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings


class ExcelsisRAGStore:
    SCHEMA_COLLECTION = "excelsis_schema"
    POLICY_COLLECTION = "excelsis_policy"

    def __init__(
        self,
        chroma_path: str = ".chroma",
        embed_model: str = "nomic-embed-text",
        ollama_base_url: str = "http://localhost:11434",
        schema_k: int = 6,
        policy_k: int = 4,
    ) -> None:
        self._schema_k = schema_k
        self._policy_k = policy_k
        embeddings = OllamaEmbeddings(
            model=embed_model,
            base_url=ollama_base_url,
        )
        self._schema_vs = Chroma(
            collection_name=self.SCHEMA_COLLECTION,
            embedding_function=embeddings,
            persist_directory=chroma_path,
        )
        self._policy_vs = Chroma(
            collection_name=self.POLICY_COLLECTION,
            embedding_function=embeddings,
            persist_directory=chroma_path,
        )

    def schema_collection(self) -> Chroma:
        return self._schema_vs

    def policy_collection(self) -> Chroma:
        return self._policy_vs

    def retrieve_schema(self, query: str) -> str:
        docs = self._schema_vs.similarity_search(query, k=self._schema_k)
        if not docs:
            return "No schema information found."
        return "\n\n---\n\n".join(d.page_content for d in docs)

    def retrieve_policy(self, query: str) -> str:
        docs = self._policy_vs.similarity_search(query, k=self._policy_k)
        if not docs:
            return "No policy information found."
        return "\n\n---\n\n".join(d.page_content for d in docs)
