from pydantic import BaseModel
from typing import Optional

class DkxxBase(BaseModel):
    dkbm: str
    dkmc: Optional[str] = None
    scmj: Optional[float] = None

class DkxxShpAttr(DkxxBase):
    id: int
    class Config:
        orm_mode = True
