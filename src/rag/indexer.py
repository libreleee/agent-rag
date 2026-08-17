"""
지식 베이스(KM) RAG 인덱서
파싱된 Markdown 문서를 청킹하여 ChromaDB 및 메타데이터 인덱스에 저장
"""
from pathlib import Path
from typing import List, Dict, Any
import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter

class KnowledgeIndexer:
    def __init__(self, persist_dir: str | Path = "./data/vectordb"):
        self.persist_dir = str(persist_dir)
        self.client = chromadb.PersistentClient(path=self.persist_dir)
        self.collection = self.client.get_or_create_collection(name="enterprise_knowledge")
        
        # 텍스트 청커
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=150,
            separators=["\n## ", "\n\n", "\n", " ", ""]
        )

    def index_parsed_document(self, parsed_data: Dict[str, Any], extra_metadata: Dict[str, Any] = None) -> int:
        """
        파싱된 문서를 청킹하고 ChromaDB에 인덱싱합니다.
        """
        markdown_text = parsed_data.get("markdown", "")
        if not markdown_text.strip():
            return 0

        source_file = parsed_data.get("source_file", "unknown")
        file_type = parsed_data.get("file_type", "unknown")

        # 텍스트 청킹
        chunks = self.text_splitter.split_text(markdown_text)
        if not chunks:
            return 0

        documents = []
        metadatas = []
        ids = []

        for idx, chunk in enumerate(chunks):
            chunk_id = f"{source_file}_chunk_{idx}"
            ids.append(chunk_id)
            documents.append(chunk)

            meta = {
                "source_file": source_file,
                "file_type": file_type,
                "chunk_index": idx,
                "total_chunks": len(chunks)
            }
            if extra_metadata:
                meta.update(extra_metadata)
            metadatas.append(meta)

        # ChromaDB에 저장 (Chroma 기본 내장 임베딩 활용)
        self.collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )

        return len(chunks)

    def delete_document(self, source_file: str) -> int:
        """지정된 원본 파일명(source_file)에 해당하는 모든 지식 청크를 ChromaDB에서 삭제합니다."""
        results = self.collection.get(where={"source_file": source_file})
        ids_to_delete = results.get("ids", [])
        if ids_to_delete:
            self.collection.delete(ids=ids_to_delete)
        return len(ids_to_delete)

