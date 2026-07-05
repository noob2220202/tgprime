from pydantic import BaseModel, ConfigDict


class AutoReplyRuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    account_id: str
    enabled: bool
    reply_text: str
    cooldown_minutes: int


class AutoReplyRuleUpdate(BaseModel):
    enabled: bool
    reply_text: str
    cooldown_minutes: int = 60
