import time
import requests
from llama_index.core import Document
from config import FEISHU_APP_ID, FEISHU_APP_SECRET


def _get_tenant_token() -> str:
    resp = requests.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["tenant_access_token"]


def _create_export_task(token: str, doc_token: str) -> str:
    """创建导出任务，返回 ticket"""
    resp = requests.post(
        "https://open.feishu.cn/open-apis/drive/v1/export_tasks",
        headers={"Authorization": f"Bearer {token}"},
        json={"file_extension": "md", "token": doc_token, "type": "docx"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["data"]["ticket"]


def _poll_export_task(token: str, ticket: str, doc_token: str, max_retries: int = 20) -> str:
    """轮询导出任务状态，返回 file_token"""
    url = f"https://open.feishu.cn/open-apis/drive/v1/export_tasks/{ticket}"
    for attempt in range(max_retries):
        resp = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            params={"token": doc_token},
            timeout=10,
        )
        resp.raise_for_status()
        result = resp.json()["data"]["result"]
        status = result["job_status"]
        if status == 0:       # 成功
            return result["file_token"]
        elif status in (3, 4):  # 失败
            raise RuntimeError(f"导出任务失败，状态码: {status}，错误: {result.get('job_error_msg')}")
        # status == 1/2 表示进行中，继续等待
        print(f"[feishu_loader] 导出中... ({attempt + 1}/{max_retries})")
        time.sleep(2)
    raise TimeoutError(f"导出任务超时: ticket={ticket}")


def _download_file(token: str, file_token: str) -> str:
    """下载导出文件，返回 Markdown 文本"""
    resp = requests.get(
        f"https://open.feishu.cn/open-apis/drive/v1/export_tasks/file/{file_token}/download",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.content.decode("utf-8")


def load_feishu_docs(doc_tokens: list[str]) -> list[Document]:
    """
    通过飞书开放平台 API 拉取文档并导出为 Markdown。
    doc_tokens: 飞书文档的 token 列表（URL 中 /docx/<token> 部分）
    """
    if not doc_tokens:
        return []

    tenant_token = _get_tenant_token()
    docs = []

    for doc_token in doc_tokens:
        print(f"[feishu_loader] 拉取文档: {doc_token}")
        try:
            ticket     = _create_export_task(tenant_token, doc_token)
            file_token = _poll_export_task(tenant_token, ticket, doc_token)
            md_text    = _download_file(tenant_token, file_token)
            docs.append(Document(
                text=md_text,
                metadata={
                    "source": doc_token,
                    "type": "feishu",
                }
            ))
            print(f"[feishu_loader] 完成: {doc_token}，字符数: {len(md_text)}")
        except Exception as e:
            print(f"[feishu_loader] 失败 {doc_token}: {e}")

    print(f"[feishu_loader] 共加载 {len(docs)} 个飞书文档")
    return docs
