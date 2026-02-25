import sys
from ingest.pdf_loader import load_pdfs
from ingest.feishu_loader import load_feishu_docs
from pipeline.chunker import chunk_pdf_docs, chunk_feishu_docs
from pipeline.indexer import setup_embed_model, build_index, load_index
from pipeline.retriever import build_retriever, build_reranker, retrieve

# 飞书文档 token 列表（URL 中 /docx/<token> 部分）
FEISHU_DOC_TOKENS = [
    # "your-feishu-doc-token-1",
    # "your-feishu-doc-token-2",
]


def cmd_ingest():
    """首次运行：解析所有文档，建立向量索引"""
    setup_embed_model()

    pdf_docs    = load_pdfs("./data/pdfs/")
    feishu_docs = load_feishu_docs(FEISHU_DOC_TOKENS)

    if not pdf_docs and not feishu_docs:
        print("没有找到任何文档，请将 PDF 放入 ./data/pdfs/ 或配置飞书 token")
        return

    pdf_all,    pdf_leaf    = chunk_pdf_docs(pdf_docs)
    feishu_all, feishu_leaf = chunk_feishu_docs(feishu_docs)

    all_nodes  = pdf_all  + feishu_all
    leaf_nodes = pdf_leaf + feishu_leaf

    build_index(all_nodes, leaf_nodes)


def cmd_query(query: str):
    """查询：加载已有索引，检索并打印结果"""
    setup_embed_model()
    index    = load_index()
    retriever = build_retriever(index)
    reranker  = build_reranker()

    results = retrieve(retriever, reranker, query)

    print(f"\n查询: {query}")
    print(f"返回 {len(results)} 条结果\n")
    for i, node in enumerate(results):
        source = node.metadata.get("source", "unknown")
        doc_type = node.metadata.get("type", "unknown")
        score = f"{node.score:.4f}" if node.score is not None else "N/A"
        print(f"--- [{i+1}] {source} ({doc_type}) | 分数: {score} ---")
        print(node.get_content()[:600])
        print()

    return results


def print_usage():
    print("用法:")
    print("  python main.py ingest              # 解析文档，建立索引")
    print("  python main.py query <查询内容>     # 检索")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "ingest":
        cmd_ingest()
    elif cmd == "query":
        if len(sys.argv) < 3:
            print("请提供查询内容，例如: python main.py query 用户登录模块错误码")
            sys.exit(1)
        cmd_query(" ".join(sys.argv[2:]))
    else:
        print_usage()
        sys.exit(1)
