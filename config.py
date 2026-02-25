# Qdrant
QDRANT_HOST     = "localhost"
QDRANT_PORT     = 6333
COLLECTION_NAME = "srs_docs"

# 模型（本地路径 或 HuggingFace model id）
EMBED_MODEL    = "Qwen/Qwen3-Embedding-0.6B"
RERANKER_MODEL = "Qwen/Qwen3-Reranker-0.6B"

# 飞书
FEISHU_APP_ID     = "your-app-id"
FEISHU_APP_SECRET = "your-app-secret"

# 分块参数
PARENT_CHUNK_SIZE = 4096  # tokens，送给 LLM 的完整上下文
CHILD_CHUNK_SIZE  = 512   # tokens，用于向量检索

# 存储路径（docstore 持久化，保存 parent-child 关系）
STORAGE_DIR = "./storage"
