from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: str
    file_name: str
    file_type: str
    file_size: int
    status: str

    class Config:
        from_attributes = True