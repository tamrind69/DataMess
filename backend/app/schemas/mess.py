from pydantic import BaseModel, ConfigDict


class MessResponse(BaseModel):
    id: int
    name: str
    location: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)