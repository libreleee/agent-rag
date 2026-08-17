"""
하이브리드 지식 검색기 (Hybrid Retriever: Dense ChromaDB + Sparse BM25)
"""
from typing import List, Dict, Any
import chromadb
from rank_bm25 import BM25Okapi

class HybridRetriever:
    def __init__(self, persist_dir: str = "./data/vectordb"):
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(name="enterprise_knowledge")

    def search(self, query: str, top_k: int = 4) -> List[Dict[str, Any]]:
        """
        ChromaDB 벡터 검색과 BM25 키워드 점수를 결합한 하이브리드 검색을 수행합니다.
        """
        # 1. ChromaDB Vector 검색
        results = self.collection.query(
            query_texts=[query],
            n_results=min(top_k * 2, 20)
        )

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0] if "distances" in results else [0.0] * len(documents)

        if not documents:
            return []

        # 2. BM25 키워드 스코어링 (Sparse)
        tokenized_corpus = [doc.split() for doc in documents]
        bm25 = BM25Okapi(tokenized_corpus)
        tokenized_query = query.split()
        bm25_scores = bm25.get_scores(tokenized_query)

        # 3. Hybrid 점수 융합 (RRF 방식)
        combined_results = []
        for idx, (doc, meta, dist, bm25_score) in enumerate(zip(documents, metadatas, distances, bm25_scores)):
            vector_score = 1.0 / (1.0 + dist) if dist is not None else 0.5
            # 하이브리드 가중치 (Vector 0.6 + BM25 0.4)
            final_score = (vector_score * 0.6) + (min(bm25_score / 10.0, 1.0) * 0.4)
            combined_results.append({
                "content": doc,
                "metadata": meta,
                "score": round(final_score, 4),
                "source": meta.get("source_file", "unknown")
            })

        # 최종 점수 순 정렬
        combined_results.sort(key=lambda x: x["score"], reverse=True)
        return combined_results[:top_k]
