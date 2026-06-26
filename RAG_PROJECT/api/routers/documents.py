"""Admin-only document management endpoints."""
import asyncio
import tempfile
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from api.deps import require_admin
from api.schemas import DocumentDeleteResponse, DocumentListItem, DocumentUploadResponse
from services.doc_store import add_doc_meta, delete_doc_meta, get_doc_meta, list_docs
from services.user_store import User
from utils.log_utils import log

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])

_ALLOWED_EXTENSIONS = {".md", ".txt"}
_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@router.get("", response_model=List[DocumentListItem])
async def list_documents(_: User = Depends(require_admin)):
    docs = list_docs()
    return [
        DocumentListItem(
            doc_id=d.doc_id,
            filename=d.filename,
            chunk_count=d.chunk_count,
            uploaded_at=d.uploaded_at,
        )
        for d in docs
    ]


@router.post("", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    admin: User = Depends(require_admin),
):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"仅支持 {', '.join(_ALLOWED_EXTENSIONS)} 格式",
        )

    content = await file.read()
    if len(content) > _MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="文件大小不能超过 10 MB",
        )

    # Write to a temp dir with the original filename so MarkdownParser metadata is correct
    original_name = file.filename or "upload"
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = str(Path(tmp_dir) / original_name)
        Path(tmp_path).write_bytes(content)

        try:
            from documents.markdown_parser import MarkdownParser
            from documents.milvus_db import MilvusVectorSave

            loop = asyncio.get_event_loop()

            def _ingest():
                parser = MarkdownParser()
                docs = parser.parse_markdown_to_documents(tmp_path)
                if not docs:
                    return 0
                mv = MilvusVectorSave()
                mv.create_connection()
                mv.add_documents(docs)
                return len(docs)

            chunks = await loop.run_in_executor(None, _ingest)
        except Exception as exc:
            log.error(f"文档写入失败: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"文档写入失败: {exc}",
            )

    meta = add_doc_meta(
        filename=file.filename or "unknown",
        chunk_count=chunks,
        uploaded_by=admin.user_id,
    )
    log.info(f"文档上传成功: {meta.filename}, chunks={chunks}, by={admin.username}")
    return DocumentUploadResponse(
        filename=meta.filename,
        chunks_added=chunks,
        message="上传成功",
    )


@router.delete("/{doc_id}", response_model=DocumentDeleteResponse)
async def delete_document(doc_id: str, _: User = Depends(require_admin)):
    meta = get_doc_meta(doc_id)
    if not meta:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在")

    # Delete from Milvus by filename filter (filename field set by MarkdownParser via UnstructuredMarkdownLoader)
    deleted_count = 0
    try:
        from pymilvus import MilvusClient
        from core.config import get_settings

        s = get_settings()
        loop = asyncio.get_event_loop()
        safe_filename = meta.filename.replace('"', '\\"')

        def _delete():
            client = MilvusClient(uri=s.milvus_uri)
            results = client.query(
                collection_name=s.milvus_collection,
                filter=f'filename == "{safe_filename}"',
                output_fields=["id"],
                limit=16384,
            )
            ids = [r["id"] for r in results]
            if ids:
                client.delete(collection_name=s.milvus_collection, ids=ids)
            return len(ids)

        deleted_count = await loop.run_in_executor(None, _delete)
    except Exception as exc:
        log.warning(f"Milvus删除失败 (元数据仍会删除): {exc}")

    delete_doc_meta(doc_id)
    log.info(f"文档删除: {meta.filename}, milvus_deleted={deleted_count}")
    return DocumentDeleteResponse(
        deleted_count=deleted_count,
        message=f"已删除文档 '{meta.filename}'，共清除 {deleted_count} 个向量块",
    )
