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
        "background": None,
    },
    "work": {
        "activeMode": "resolve",
        "scan": {
            "state": "empty",
            "lastRun": None,
            "indexReady": False,
            "deepAnalysisComplete": False,
            "deepAnalysisStatus": "idle",
            "deepAnalysisError": None,
        },
        "resolve": {
            "queueCount": 0,
            "moveReadyCount": 0,
            "reviewSignalCount": 0,
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
            "hasPendingQualityRepair": False,
        },
        "finalize": {
            "lastReportId": None,
            "lastStatus": "idle",
            "lastRunAt": None,
            "blockerCount": 0,
            "warningCount": 0,
        },
    },
    "fileListSummary": {
        "totalCount": 1,
        "filteredCount": 1,
        "issueCount": 0,
        "selectedCount": 0,
    },
}
