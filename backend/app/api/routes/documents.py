import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, UploadFile
from sqlmodel import col, select

from app.api.deps import CurrentUser, SessionDep
from app.models import (
    Document,
    DocumentChunk,
    DocumentChunkPublic,
    DocumentPublic,
    DocumentsPublic,
)
from pypdf import PdfReader

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_FILE_TYPES = {
    ".pdf": "application/pdf",
    ".md": "text/markdown",
    ".txt": "text/plain",
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
BACKEND_DIR = Path(__file__).resolve().parents[3]
UPLOADS_DIR = BACKEND_DIR / "uploads"

def split_text(content: str, chunk_size: int = 500) -> list[str]:
    text = content.strip()
    return [
        text[start : start + chunk_size]
        for start in range(0, len(text), chunk_size)
        if text[start : start + chunk_size].strip()
    ]

@router.get("/", response_model=DocumentsPublic)
def read_documents(
    session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> Any:
    """
    Retrieve the current user's documents.
    """
    statement = (
        select(Document)
        .where(Document.owner_id == current_user.id)
        .order_by(col(Document.created_at).desc())
        .offset(skip)
        .limit(limit)
    )
    documents = session.exec(statement).all()
    documents_public = [
        DocumentPublic.model_validate(document) for document in documents
    ]
    return DocumentsPublic(data=documents_public, count=len(documents_public))

@router.get("/{id}/chunks", response_model=list[DocumentChunkPublic])
def read_document_chunks(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Any:
    """
    Retrieve the chunks created from one document.
    """
    document = session.get(Document, id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if document.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    statement = (
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document.id)
        .order_by(col(DocumentChunk.chunk_index))
    )
    chunks = session.exec(statement).all()
    return [DocumentChunkPublic.model_validate(chunk) for chunk in chunks]

@router.post("/", response_model=DocumentPublic)
async def upload_document(
    session: SessionDep, current_user: CurrentUser, file: UploadFile
) -> Any:
    """
    Upload a PDF, Markdown, or TXT document.
    """
    file_name = Path(file.filename or "").name
    extension = Path(file_name).suffix.lower()

    if extension not in ALLOWED_FILE_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Only PDF, Markdown, and TXT files are supported",
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File must be 10 MB or smaller")

    relative_path = Path("uploads") / str(current_user.id) / f"{uuid.uuid4()}{extension}"
    destination = BACKEND_DIR / relative_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)

    document = Document(
        file_name=file_name,
        file_type=ALLOWED_FILE_TYPES[extension],
        file_size=len(content),
        storage_path=str(relative_path),
        owner_id=current_user.id,
    )
    session.add(document)
    session.commit()
    session.refresh(document)
    return document

@router.post("/{id}/process", response_model=DocumentPublic)
def process_document(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Any:
    """
    Read a document and save its text chunks.
    """
    document = session.get(Document, id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if document.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    file_path = BACKEND_DIR / document.storage_path
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Stored file not found")

    if document.file_type == "application/pdf":
        try:
            reader = PdfReader(file_path)
            content = "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as error:
            raise HTTPException(
                status_code=400, detail="Could not read text from PDF"
            ) from error
    else:
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as error:
            raise HTTPException(
                status_code=400,
                detail="This text file is not UTF-8 encoded",
            ) from error

    chunks = split_text(content)
    if not chunks:
        raise HTTPException(status_code=400, detail="Document is empty")

    existing_chunks = session.exec(
        select(DocumentChunk).where(DocumentChunk.document_id == document.id)
    ).all()
    for chunk in existing_chunks:
        session.delete(chunk)

    for index, chunk_content in enumerate(chunks):
        session.add(
            DocumentChunk(
                document_id=document.id,
                chunk_index=index,
                content=chunk_content,
            )
        )

    document.status = "ready"
    session.add(document)
    session.commit()
    session.refresh(document)
    return document
