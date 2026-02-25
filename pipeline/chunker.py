from llama_index.core import Document
from llama_index.core.node_parser import HierarchicalNodeParser, get_leaf_nodes
from llama_index.core.schema import BaseNode
from config import PARENT_CHUNK_SIZE, CHILD_CHUNK_SIZE


def _make_hier_parser() -> HierarchicalNodeParser:
    return HierarchicalNodeParser.from_defaults(
        chunk_sizes=[PARENT_CHUNK_SIZE, CHILD_CHUNK_SIZE]
    )


def chunk_pdf_docs(docs: list[Document]) -> tuple[list[BaseNode], list[BaseNode]]:
    """
    PDF 分块策略：
    - Docling 已将 PDF 导出为结构化 Markdown（表格完整保留）
    - 用 HierarchicalNodeParser 按 heading 层级递归拆分
    - 超大章节会被拆到 CHILD_CHUNK_SIZE，小章节保持完整
    返回 (all_nodes, leaf_nodes)
    """
    parser = _make_hier_parser()
    all_nodes = parser.get_nodes_from_documents(docs, show_progress=True)
    leaf_nodes = get_leaf_nodes(all_nodes)
    print(f"[chunker] PDF: {len(docs)} 文档 → {len(all_nodes)} 节点，{len(leaf_nodes)} 叶子节点")
    return all_nodes, leaf_nodes


def chunk_feishu_docs(docs: list[Document]) -> tuple[list[BaseNode], list[BaseNode]]:
    """
    飞书文档分块策略：
    - 飞书导出的 Markdown 天然有 heading 层级结构
    - 同样用 HierarchicalNodeParser 按层级拆分
    返回 (all_nodes, leaf_nodes)
    """
    parser = _make_hier_parser()
    all_nodes = parser.get_nodes_from_documents(docs, show_progress=True)
    leaf_nodes = get_leaf_nodes(all_nodes)
    print(f"[chunker] 飞书: {len(docs)} 文档 → {len(all_nodes)} 节点，{len(leaf_nodes)} 叶子节点")
    return all_nodes, leaf_nodes
