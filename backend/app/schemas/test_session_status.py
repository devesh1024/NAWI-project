from pydantic import BaseModel


class TestSessionStatusUpdate(BaseModel):
    status: str