"""数据模型模块"""

from app.models.database import Entry, JudgeResult, DebateSession, DebateMessage
from app.models.binary_choice_database import (
    BinaryChoiceEntry,
    BinaryChoiceResult,
    BinaryChoiceDebateSession,
    BinaryChoiceMessage,
)
from app.models.schemas import (
    EntryCreate,
    EntryResponse,
    JudgeResultResponse,
    DebateResponse,
    JudgeEntryRequest,
    JudgeEntryResponse,
)
from app.models.binary_choice_schemas import (
    BinaryChoiceRequest,
    BinaryChoiceResponse,
    BinaryChoiceJudgeResult,
)

__all__ = [
    # 原有评分模型
    "Entry",
    "JudgeResult",
    "DebateSession",
    "DebateMessage",
    "EntryCreate",
    "EntryResponse",
    "JudgeResultResponse",
    "DebateResponse",
    "JudgeEntryRequest",
    "JudgeEntryResponse",
    # 二选一模型
    "BinaryChoiceEntry",
    "BinaryChoiceResult",
    "BinaryChoiceDebateSession",
    "BinaryChoiceMessage",
    "BinaryChoiceRequest",
    "BinaryChoiceResponse",
    "BinaryChoiceJudgeResult",
]




