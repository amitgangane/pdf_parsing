from api.models.orm import SessionRecord

# ALl the database CRUD operations related to session management are defined here. This includes creating a new session, updating an existing session, 
# retrieving a session by its ID, and listing all sessions. Each function interacts with the database using SQLAlchemy's ORM capabilities to perform the necessary operations on the SessionRecord model.
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
