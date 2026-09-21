from sqlalchemy.orm import Session
from repository.mes_repo import MessageRepository
from repository.user_repo import UserRepository
from core.errors import SelfMessagingError, UserNotFoundError

class UserService:
    def __init__(self, db: Session):
        self.message_repo = MessageRepository(db)
        self.user_repo = UserRepository(db)

    def get_conversation_by_username(self, current_user_id: int, target_username: str):
        # Step 1: Look up the user by username
        target_user = self.user_repo.get_user_by_username(target_username)
        
        # Guard clause: If the user doesn't exist, stop and return a 404
        if not target_user:
            raise UserNotFoundError(target_username)
            
        # Optional: Prevent querying a conversation with yourself
        if target_user.id == current_user_id:
            raise SelfMessagingError("You cannot have a conversation with yourself.")           

        # Step 2: Use the newly found ID to query the messages
        return self.message_repo.get_conversation(
            user_1_id=current_user_id, 
            user_2_id=target_user.id
        )