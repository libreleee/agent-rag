"""
Agentic RAG Core Configuration
"""
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Agentic Knowledge Hub"
    VERSION: str = "0.1.0"
    
    # 디렉토리 경로
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    RAW_DATA_DIR: Path = DATA_DIR / "raw"
    PROCESSED_DATA_DIR: Path = DATA_DIR / "processed"
    DATASETS_DIR: Path = DATA_DIR / "datasets"
    VECTOR_DB_DIR: Path = DATA_DIR / "vectordb"

    # RAG 설정
    DEFAULT_CHUNK_SIZE: int = 800
    DEFAULT_CHUNK_OVERLAP: int = 150
    
    # 임베딩 모델 (로컬 / 원격)
    EMBEDDING_MODEL: str = "BAAI/bge-m3"

    class Config:
        env_file = ".env"

settings = Settings()

# 필요한 기본 디렉토리 자동 생성
for d in [settings.RAW_DATA_DIR, settings.PROCESSED_DATA_DIR, settings.DATASETS_DIR, settings.VECTOR_DB_DIR]:
    d.mkdir(parents=True, exist_ok=True)
