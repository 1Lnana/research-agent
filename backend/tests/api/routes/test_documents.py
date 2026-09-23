import io
import uuid
from pathlib import Path

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.api.routes.documents import BACKEND_DIR,split_text
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

def test_upload_document_rejects_unsupported_file_type(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    files = {
        "file": (
            "notes.docx",
            io.BytesIO(b"not supported"),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    }

    response = client.post(
        f"{settings.API_V1_STR}/documents/",
        headers=superuser_token_headers,
        files=files,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Only PDF, Markdown, and TXT files are supported"

def test_upload_document_rejects_file_larger_than_limit(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
        files = {
            "file": (
                "too-large.txt",
                io.BytesIO(b"x" * (10 * 1024 * 1024 + 1)),
                "text/plain",
        )
    }

        response = client.post(
        f"{settings.API_V1_STR}/documents/",
        headers=superuser_token_headers,
        files=files,
    )

        assert response.status_code == 400
        assert response.json()["detail"] == "File must be 10 MB or smaller"

def test_process_empty_document_returns_error(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    files = {
        "file": (
            "empty.txt",
            io.BytesIO(b""),
            "text/plain",
        )
    }

    upload_response = client.post(
        f"{settings.API_V1_STR}/documents/",
        headers=superuser_token_headers,
        files=files,
    )
    assert upload_response.status_code == 200
    document_id = upload_response.json()["id"]

    process_response = client.post(
        f"{settings.API_V1_STR}/documents/{document_id}/process",
        headers=superuser_token_headers,
    )

    assert process_response.status_code == 400
    assert process_response.json()["detail"] == "Document is empty"

    cleanup_response = client.delete(
        f"{settings.API_V1_STR}/documents/{document_id}",
        headers=superuser_token_headers,
    )
    assert cleanup_response.status_code == 200

def test_process_document_returns_error_when_stored_file_is_missing(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    owner = db.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).one()

    document = Document(
        file_name="missing.txt",
        file_type="text/plain",
        file_size=10,
        storage_path=str(
            Path("uploads") / str(owner.id) / f"{uuid.uuid4()}.txt"
        ),
        owner_id=owner.id,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    response = client.post(
        f"{settings.API_V1_STR}/documents/{document.id}/process",
        headers=superuser_token_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Stored file not found"

    db.delete(document)
    db.commit()

def test_split_text_positions() -> None:
     original = "  ABCDE"
     chunks = split_text(original,chunk_size=3)
     assert chunks == [("ABC",2,5),("DE",5,7)]