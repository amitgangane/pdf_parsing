from api.models.orm import SessionRecord


def create_session(db, data: dict) -> None:
    db.add(SessionRecord(**data))
    db.commit()


def update_session(db, session_id: str, **fields) -> None:
    db.query(SessionRecord).filter_by(session_id=session_id).update(fields)
    db.commit()


def get_session(db, session_id: str) -> dict | None:
    row = db.query(SessionRecord).filter_by(session_id=session_id).first()
    if row is None:
        return None
    return {k: v for k, v in row.__dict__.items() if not k.startswith("_")}


def list_sessions(db) -> list[dict]:
    rows = db.query(SessionRecord).order_by(SessionRecord.created_at.desc()).all()
    return [{k: v for k, v in row.__dict__.items() if not k.startswith("_")} for row in rows]
