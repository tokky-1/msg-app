from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from repository.mes_repo import MessageRepository
from repository.user_repo import UserRepository
from core.errors import (
    AuthenticationError,
    ConflictError,
    EmailTakenError,
    SelfMessagingError,
    UserNotFoundError,
    UsernameTakenError,
)
from core.security import createhash, verifyhash
from models.user import User
from schema.auth import LoginRequest, RegisterRequest

# Verified against when the username doesn't exist, so an unknown user costs the same
# hash time as a wrong password and response timing doesn't reveal which usernames exist.
_DUMMY_HASH = createhash("dummy-password-for-timing")

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

    def register(self, data: RegisterRequest) -> User:
        if self.user_repo.get_user_by_username(data.username):
            raise UsernameTakenError(data.username)

        if self.user_repo.get_by_email(data.email):
            raise EmailTakenError(data.email)

        hashed_password = createhash(data.password)

        # The checks above can race with a concurrent registration; the unique constraints are the real guard.
        try:
            return self.user_repo.create_user(
                username=data.username,
                email=data.email,
                hashed_password=hashed_password,
            )
        except IntegrityError as e:
            # Postgres default names for the unnamed UniqueConstraints on users.
            constraint = getattr(getattr(e.orig, "diag", None), "constraint_name", None)
            if constraint == "users_username_key":
                raise UsernameTakenError(data.username) from e
            if constraint == "users_email_key":
                raise EmailTakenError(data.email) from e
            raise ConflictError("Username or email is already registered.") from e

    def authenticate(self, data: LoginRequest) -> User:
        user = self.user_repo.get_user_by_username(data.username)

        if user is None:
            verifyhash(data.password, _DUMMY_HASH)
            raise AuthenticationError("Incorrect username or password")

        if not verifyhash(data.password, user.hashed_password):
            raise AuthenticationError("Incorrect username or password")

        return user
