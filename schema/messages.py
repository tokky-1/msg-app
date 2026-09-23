from pydantic import BaseModel,ConfigDict
from datetime import datetime

class MessageCreate(BaseModel):     
    receiver_id: int
    content: str

class MessageUpdate(BaseModel):
    content: str

class MessageResponse(BaseModel):
    id: int
    sender_id: int
    receiver_id: int
    content: str
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class InboxItem(BaseModel):
    """One conversation in the inbox: its latest message plus who it's with."""
    message: MessageResponse
    partner_username: str
