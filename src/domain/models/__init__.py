"""Pydantic/Dataclass 엔티티."""

from domain.models.file_record import FileRecord
from domain.models.duplicate_group import DuplicateGroup
from domain.models.evidence import Evidence
from domain.models.integrity_issue import IntegrityIssue
from domain.models.action_plan import ActionPlan, ActionItem, ActionResult
from domain.models.file_feature import FileFeature
from domain.models.candidate_edge import CandidateEdge

__all__ = [
    "FileRecord",
    "DuplicateGroup",
    "Evidence",
    "IntegrityIssue",
    "ActionPlan",
    "ActionItem",
    "ActionResult",
    "FileFeature",
    "CandidateEdge",
]
