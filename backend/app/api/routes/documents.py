import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, UploadFile
from sqlmodel import col, select

from app.api.deps import CurrentUser, SessionDep
from app.models import Document, DocumentPublic, DocumentsPublic

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_FILE_TYPES = {
    ".pdf": "application/pdf",
    ".md": "text/markdown",
    ".txt": "text/plain",
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
BACKEND_DIR = Path(__file__).resolve().parents[3]
UPLOADS_DIR = BACKEND_DIR / "uploads"


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