from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from ..deps import get_services
from ..ingest import EmptyDocumentError, UnsupportedFileError
from ..schemas import DocumentOut
from ..services import Services

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("", response_model=list[DocumentOut])
def list_documents(svc: Services = Depends(get_services)):
    """List every uploaded document, newest first."""
    return svc.store.list_documents()


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile, svc: Services = Depends(get_services)):
    """Upload a PDF, DOCX, TXT or MD file. It is parsed, chunked and indexed for search."""
    max_bytes = svc.settings.max_upload_mb * 1024 * 1024
    data = await file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(413, f"File is larger than {svc.settings.max_upload_mb} MB")
    if not data:
        raise HTTPException(400, "The file is empty")
    try:
        doc_id = svc.ingest(file.filename or "document.txt", data)
    except UnsupportedFileError as e:
        raise HTTPException(415, str(e)) from e
    except EmptyDocumentError as e:
        raise HTTPException(422, str(e)) from e
    return svc.store.get_document(doc_id)


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(doc_id: str, svc: Services = Depends(get_services)):
    """Delete a document and all of its indexed chunks."""
    if not svc.store.delete_document(doc_id):
        raise HTTPException(404, "Document not found")
