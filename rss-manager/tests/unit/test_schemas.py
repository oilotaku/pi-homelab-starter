from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas import CreateRequest


def test_valid_keyword_is_trimmed() -> None:
    req = CreateRequest(keyword="  海賊王  ")
    assert req.keyword == "海賊王"


@pytest.mark.parametrize(
    "bad",
    ["", "   ", "a" * 61, "有/斜線", "有\\反斜線", "有..兩點", "有\n換行", "有\r換行"],
)
def test_invalid_keyword_raises(bad: str) -> None:
    with pytest.raises(ValidationError):
        CreateRequest(keyword=bad)
