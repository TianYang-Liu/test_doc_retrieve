from llama_index.core import VectorStoreIndex, StorageContext, Settings
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core.schema import BaseNode
from qdrant_client import QdrantClient
from config import QDRANT_HOST, QDRANT_PORT, COLLECTION_NAME, EMBED_MODEL, STORAGE_DIR


def setup_embed_model() -> HuggingFaceEmbedding:
    embed_model = HuggingFaceEmbedding(
        model_name=EMBED_MODEL,
        max_length=32768,
        device="cpu",
    )
    Settings.embed_model = embed_model
    print(f"[indexer] Embedding 模型加载完成: {EMBED_MODEL}")
    return embed_model


def _get_qdrant_store() -> tuple[QdrantClient, QdrantVectorStore]:
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    store = QdrantVectorStore(client=client, collection_name=COLLECTION_NAME)
    return client, store


def build_index(
    all_nodes: list[BaseNode],
    leaf_nodes: list[BaseNode],
) -> VectorStoreIndex:
    """
    建立索引：
    - leaf_nodes 向量化后存入 Qdrant（用于检索）
    - all_nodes 存入 docstore（保存 parent-child 关系，AutoMerging 用）
    - docstore 持久化到 STORAGE_DIR
    """
    _, vector_store = _get_qdrant_store()

    docstore = SimpleDocumentStore()
    docstore.add_documents(all_nodes)

    storage_context = StorageContext.from_defaults(
        vector_store=vector_store,
        docstore=docstore,
    )

    print(f"[indexer] 开始向量化 {len(leaf_nodes)} 个节点，写入 Qdrant...")
    index = VectorStoreIndex(
        leaf_nodes,
        storage_context=storage_context,
        show_progress=True,
    )

    storage_context.persist(persist_dir=STORAGE_DIR)
    print(f"[indexer] 索引完成，docstore 已持久化到 {STORAGE_DIR}")
    return index


def load_index() -> VectorStoreIndex:
    """
    已建库后直接加载，跳过解析和 embedding 步骤。
    """
    _, vector_store = _get_qdrant_store()

    storage_context = StorageContext.from_defaults(
        vector_store=vector_store,
        persist_dir=STORAGE_DIR,
    )
    index = VectorStoreIndex.from_vector_store(
        vector_store,
        storage_context=storage_context,
    )
    print("[indexer] 索引加载完成")
    return index
