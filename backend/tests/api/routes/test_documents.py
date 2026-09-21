import uuid
from pathlib import Path

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.api.routes.documents import BACKEND_DIR
from app.core.config import settings
from app.models import Document, DocumentChunk, User


def test_delete_document_not_found(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    response = client.delete(
        f"{settings.API_V1_STR}/documents/{uuid.uuid4()}",
        headers=superuser_token_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found"

def test_delete_document_removes_record_chunks_and_file(

    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    owner = db.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).one()
    relative_path = Path("uploads") / str(owner.id) / f"{uuid.uuid4()}.txt"
    file_path = BACKEND_DIR / relative_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("Temporary test document", encoding="utf-8")

    document = Document(
        file_name="delete-me.txt",
        file_type="text/plain",
        file_size=file_path.stat().st_size,
        storage_path=str(relative_path),
        owner_id=owner.id,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    document_id = document.id

    chunk = DocumentChunk(
        document_id=document.id,
        chunk_index=0,
        content="Temporary chunk"
    )
    db.add(chunk)
    db.commit()
    chunk_id = chunk.id

    response = client.delete(
        f"{settings.API_V1_STR}/documents/{document_id}",
        headers=superuser_token_headers,
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Document deleted successfully"

    db.expire_all()
    assert db.get(Document,document_id) is None
    assert db.get(DocumentChunk,chunk_id) is None
    assert not file_path.exists()

def test_delete_document_not_enough_permissions(

    client: TestClient,
    normal_user_token_headers: dict[str, str],
    db: Session,
) -> None:
    owner = db.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).one()
    relative_path = Path("uploads") / str(owner.id) / f"{uuid.uuid4()}.txt"
    file_path = BACKEND_DIR / relative_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("Temporary test document", encoding="utf-8")

    document = Document(
        file_name="delete-me.txt",
        file_type="text/plain",
        file_size=file_path.stat().st_size,
        storage_path=str(relative_path),
        owner_id=owner.id,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    document_id = document.id

    chunk = DocumentChunk(
        document_id=document.id,
        chunk_index=0,
        content="Temporary chunk"
    )
    db.add(chunk)
    db.commit()
    chunk_id = chunk.id

    response = client.delete(
        f"{settings.API_V1_STR}/documents/{document_id}",
        headers=normal_user_token_headers,
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Not enough permissions"

    db.expire_all()
    assert db.get(Document,document_id) is not None
    assert db.get(DocumentChunk,chunk_id) is not None
    assert file_path.exists()
