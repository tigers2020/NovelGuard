from __future__ import annotations

from typing import Any

VALID_SNAPSHOT: dict[str, Any] = {
    "route": "work",
    "theme": "dark",
    "locale": "ko-KR",
    "connection": "test",
    "library": {
        "folderPath": "/tmp",
        "fileCount": 1,
        "totalBytes": 100,
        "duplicateGroups": 0,
        "integrityIssues": 0,
        "lastRun": None,
        "scanOptions": [],
    },
    "pipeline": {
        "phase": "idle",
        "percent": 0,
        "label": "idle",
        "cancellable": False,
    },
    "work": {
        "activeMode": "resolve",
        "scan": {"state": "empty", "lastRun": None},
        "resolve": {
            "queueCount": 0,
            "groupCount": 0,
            "conflictCount": 0,
            "approvedCount": 0,
            "hasPendingApply": False,
            "libraryRevision": 0,
        },
        "quality": {
            "integrityIssueCount": 0,
            "encodingIssueCount": 0,
            "smallFileAnomalyCount": 0,
        },
    },
    "fileListSummary": {
        "totalCount": 1,
        "filteredCount": 1,
        "issueCount": 0,
        "selectedCount": 0,
    },
}
