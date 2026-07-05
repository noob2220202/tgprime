from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class CurrentUser(BaseModel):
    id: str
    username: str
