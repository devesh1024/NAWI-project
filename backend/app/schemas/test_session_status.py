from pydantic import BaseModel


class TestSessionStatusUpdate(BaseModel):
    status: str
    # Required when returning a session for correction: what must be fixed.
    reason: str | None = None
