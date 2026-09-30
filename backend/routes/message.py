from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from core.dependencies import get_current_user
from db.connect import get_db
from models.user import User
from schema.messages import InboxItem, MessageCreate, MessageResponse, MessageUpdate
from services.mes_service import MessageService
from services.user_service import UserService

router = APIRouter(prefix="/messages", tags=["messages"])

@router.post("", response_model=MessageResponse, status_code=201)
def send_message(data: MessageCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return MessageService(db).send_message(current_user.id, data)

# Declared before /{message_id}: FastAPI matches top-to-bottom, and a literal
# "inbox" would otherwise be parsed as message_id: int and 422 before reaching here.
@router.get("/inbox", response_model=list[InboxItem])
def get_inbox(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [
        InboxItem(message=MessageResponse.model_validate(message), partner_username=partner_username)
        for message, partner_username in MessageService(db).get_inbox(current_user.id)
    ]

@router.get("/{message_id}", response_model=MessageResponse)
def get_message(message_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return MessageService(db).get_message(message_id, current_user.id)

@router.patch("/{message_id}", response_model=MessageResponse)
def edit_message(message_id: int, data: MessageUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return MessageService(db).edit_message(message_id, current_user.id, data.content)

@router.delete("/{message_id}")
def delete_message(message_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return MessageService(db).delete_message(message_id, current_user.id)

@router.get("/conversation/{username}", response_model=list[MessageResponse])
def get_conversation(
    username: str,
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Resolve the username to an id first; the message layer only ever deals in ids.
    partner = UserService(db).get_conversation_partner(current_user.id, username)
    return MessageService(db).get_conversation_history(
        current_user.id, partner.id, limit=limit, offset=offset
    )
