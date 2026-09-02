from __future__ import annotations

from pydantic import BaseModel, field_validator

_BAD_CHARS = ("/", "\\", "..", "\x00", "\n", "\r")


class CreateRequest(BaseModel):
    keyword: str

    @field_validator("keyword")
    @classmethod
    def validate_keyword(cls, v: str) -> str:
        kw = v.strip()
        if not kw:
            raise ValueError("關鍵字不可為空")
        if len(kw) > 60:
            raise ValueError("關鍵字太長")
        for bad in _BAD_CHARS:
            if bad in kw:
                raise ValueError("關鍵字包含不允許的字元")
        return kw


class CreateResponse(BaseModel):
    ok: bool = True
    keyword: str
    save_path: str
    feed_url: str
    matched_count: int
    matched_titles: list[str]
