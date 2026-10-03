from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from models.user import User

class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_user_by_username(self, username: str) -> User | None:
        """Query the database to find a user by their exact username."""
        return self.db.query(User).filter(User.username == username).first()

    def create_user(self, username: str, email: str, hashed_password: str) -> User: 
        user_db = User(username= username,email = email, hashed_password = hashed_password)
        self.db.add(user_db)
        try:
            self.db.commit()
        except IntegrityError:
            # Leave the session usable, then let the service decide what the failure means.
            self.db.rollback()
            raise 
        self.db.refresh(user_db)
        return user_db 

    def get_by_email(self, email: str) -> User | None:
        return self.db.query(User).filter(User.email == email).first()

    def get_by_id(self, user_id: int) -> User | None:
        return self.db.query(User).filter(User.id == user_id).first()

    def lock_for_update(self, user_id: int) -> None:
        """Take a row lock on this user for the rest of the transaction.

        The rate limit counts and then inserts, which is two statements: two
        concurrent sends could both read a count under the cap and both be
        allowed. Serialising per sender closes that window. It only blocks the
        same user's simultaneous sends, never anyone else's.
        """
        self.db.query(User).filter(User.id == user_id).with_for_update().one_or_none()
