from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.dependencies import get_db
from api import crud
from api.models.responses import SessionInfo, SessionListResponse

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("/", response_model=SessionListResponse)
def list_sessions(db: Session = Depends(get_db)):
    sessions = crud.list_sessions(db)
    return SessionListResponse(
        sessions=[SessionInfo(**s) for s in sessions],
        total=len(sessions),
    )


@router.get("/{session_id}", response_model=SessionInfo)
def get_session(session_id: str, db: Session = Depends(get_db)):
    session = crud.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    return SessionInfo(**session)
