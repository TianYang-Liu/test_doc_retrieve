from llama_index.core import VectorStoreIndex
from llama_index.core.retrievers import AutoMergingRetriever
from llama_index.core.postprocessor import SentenceTransformerRerank
from llama_index.core.schema import NodeWithScore
from config import RERANKER_MODEL


def build_retriever(index: VectorStoreIndex) -> AutoMergingRetriever:
    """
    两层检索：
    1. Qdrant 向量检索 top-20 leaf nodes
    2. AutoMerging：同一 parent 下命中多个 leaf 时，自动返回完整 parent chunk
    """
    base_retriever = index.as_retriever(similarity_top_k=20)
    retriever = AutoMergingRetriever(
        base_retriever,
        index.storage_context,
        verbose=False,
    )
    return retriever


def build_reranker() -> SentenceTransformerRerank:
    reranker = SentenceTransformerRerank(
        model=RERANKER_MODEL,
        top_n=5,
        device="cpu",
    )
    print(f"[retriever] Reranker 加载完成: {RERANKER_MODEL}")
    return reranker


def retrieve(
    retriever: AutoMergingRetriever,
    reranker: SentenceTransformerRerank,
    query: str,
) -> list[NodeWithScore]:
    """
    执行检索并重排，返回 top-5 节点。
    每个节点包含：
      - node.get_content()        文本内容
      - node.metadata["source"]   来源文件名 / 飞书 doc token
      - node.metadata["type"]     "pdf" 或 "feishu"
      - node.score                相关性分数
    """
    nodes = retriever.retrieve(query)
    reranked = reranker.postprocess_nodes(nodes, query_str=query)
    return reranked
