import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from api.config import settings
from api.dependencies import get_db
from api import crud
from api.db import SessionLocal
from api.models.responses import UploadResponse

router = APIRouter(prefix="/upload", tags=["upload"])


def _make_index_name(session_id: str) -> str:
    return f"pdf_{session_id.replace('-', '_')}"


def _run_ingestion(pdf_path: str, index_name: str, session_id: str):
    db = SessionLocal()
    try:
        from unstructured.partition.pdf import partition_pdf
        from Ingestion.chunking import (
            create_semantic_chunks,
            process_images_with_caption,
            process_tables_with_description,
        )
        from Ingestion.ingestion import ingest_all_content_into_opensearch

        raw_chunks = partition_pdf(
            filename=pdf_path,
            strategy="hi_res",
            infer_table_structure=True,
            extract_image_block_types=["figure", "Image", "Table"],
            extract_image_block_to_payload=True,
            chunking_strategy=None,
        )
        processed_images = process_images_with_caption(raw_chunks, use_openai=True)
        processed_tables = process_tables_with_description(raw_chunks, use_openai=True)

        text_chunks = partition_pdf(
            filename=pdf_path,
            strategy="hi_res",
            max_characters=2000,
            combine_text_under_n_chars=500,
            new_after_n_chars=1500,
            chunking_strategy="by_title",
        )
        semantic_chunks = create_semantic_chunks(text_chunks)

        ingest_all_content_into_opensearch(
            processed_images, processed_tables, semantic_chunks, index_name=index_name
        )
        crud.update_session(db, session_id, status="ready")
    except Exception as e:
        crud.update_session(db, session_id, status="failed", error=str(e))
    finally:
        db.close()
        if os.path.exists(pdf_path):
            os.remove(pdf_path)


@router.post("/", response_model=UploadResponse, status_code=202)
async def upload_pdf(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    session_id = str(uuid.uuid4())
    index_name = _make_index_name(session_id)

    os.makedirs(settings.upload_dir, exist_ok=True)
    pdf_path = os.path.join(settings.upload_dir, f"{session_id}.pdf")

    content = await file.read()
    with open(pdf_path, "wb") as f:
        f.write(content)

    crud.create_session(db, {
        "session_id": session_id,
        "filename": file.filename,
        "index_name": index_name,
        "status": "processing",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "error": None,
    })

    background_tasks.add_task(_run_ingestion, pdf_path, index_name, session_id)

    return UploadResponse(
        session_id=session_id,
        filename=file.filename,
        index_name=index_name,
        status="processing",
        message="PDF uploaded. Ingestion started in the background.",
    )
