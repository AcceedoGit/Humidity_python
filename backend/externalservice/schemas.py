from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class BoardData(BaseModel):
    unit_ID: int
    t: int
    h: int
    w: int
    eb: int
    ups: int
    x: int
    y: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None