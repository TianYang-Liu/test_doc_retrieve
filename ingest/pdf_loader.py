from pathlib import Path
from docling.document_converter import DocumentConverter
from llama_index.core import Document


def load_pdfs(pdf_dir: str) -> list[Document]:
    """
    用 Docling 解析目录下所有 PDF。
    表格会被识别为结构化 Markdown，不会丢失内容。
    """
    converter = DocumentConverter()
    docs = []

    pdf_paths = list(Path(pdf_dir).glob("*.pdf"))
    if not pdf_paths:
        print(f"[pdf_loader] 未找到 PDF 文件: {pdf_dir}")
        return docs

    for pdf_path in pdf_paths:
        print(f"[pdf_loader] 解析: {pdf_path.name}")
        try:
            result = converter.convert(str(pdf_path))
            md_text = result.document.export_to_markdown()
            docs.append(Document(
                text=md_text,
                metadata={
                    "source": pdf_path.name,
                    "type": "pdf",
                    "file_path": str(pdf_path.resolve()),
                }
            ))
        except Exception as e:
            print(f"[pdf_loader] 解析失败 {pdf_path.name}: {e}")

    print(f"[pdf_loader] 完成，共加载 {len(docs)} 个 PDF")
    return docs
