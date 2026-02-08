from datetime import datetime
from pydantic import BaseModel


class AccountStatusResponse(BaseModel):
    is_active: bool
    email: str
    created_at: datetime
