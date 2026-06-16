from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class DiagnosticStatus(str, Enum):
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class DiagnosticCheckResult:
    component: str
    status: DiagnosticStatus
    detail: str
    checked_at: datetime
