from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from api.dependencies import get_db
from api import crud
from api.models.requests import QueryRequest
from api.models.responses import QueryResponse

router = APIRouter(prefix="/query", tags=["query"])


def _resolve_session(session_id: str, db: Session) -> dict:
    session = crud.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    if session["status"] == "processing":
        raise HTTPException(status_code=409, detail="Session is still processing. Try again later.")
    if session["status"] == "failed":
        raise HTTPException(
            status_code=422,
            detail=f"Session ingestion failed: {session.get('error', 'unknown error')}",
        )
    return session


@router.post("/", response_model=QueryResponse)
def query(request: QueryRequest, db: Session = Depends(get_db)):
    from Ingestion.generation import generate_rag_response

    session = _resolve_session(request.session_id, db)

    answer = "".join(generate_rag_response(
        query=request.question,
        index_name=session["index_name"],
        search_type=request.search_type,
        top_k=request.top_k,
        model_type=request.model_type,
        stream=True,
    ))

    return QueryResponse(
        session_id=request.session_id,
        question=request.question,
        answer=answer,
        search_type=request.search_type,
        model_type=request.model_type,
    )


@router.post("/stream")
def query_stream(request: QueryRequest, db: Session = Depends(get_db)):
    from Ingestion.generation import generate_rag_response

    session = _resolve_session(request.session_id, db)

    def generate():
        yield from generate_rag_response(
            query=request.question,
            index_name=session["index_name"],
            search_type=request.search_type,
            top_k=request.top_k,
            model_type=request.model_type,
            stream=True,
        )

    return StreamingResponse(generate(), media_type="text/plain")
