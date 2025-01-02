from pydantic import BaseModel 
from typing import List, Optional
from datetime import datetime

class ServerData(BaseModel):
    unit_ID: int
    t: List[int]  # Array of temperature values
    h: List[int]  # Array of humidity values
    status:str
    created_at: Optional[datetime] = datetime.utcnow()  # Default to now
    updated_at: Optional[datetime] = datetime.utcnow()  # Default to now
   