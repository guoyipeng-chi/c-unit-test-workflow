#!/usr/bin/env python3
"""
Experience Store for failure-fix learning.
Persist fix experiences and retrieve similar past cases.
"""

import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional


class ExperienceStore:
    """JSONL-backed experience memory for compile/run failure fixes."""

    def __init__(self, db_path: str):
        self.db_path = os.path.abspath(db_path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        if not os.path.exists(self.db_path):
            with open(self.db_path, "w", encoding="utf-8"):
                pass

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        if not text:
            return []
        return [
            tok for tok in re.findall(r"[a-zA-Z_][a-zA-Z0-9_]{2,}", text.lower())
            if tok not in {"error", "failed", "failure", "test", "compile", "runtime", "phase"}
        ]

    def add_experience(self, entry: Dict[str, Any]) -> None:
        row = dict(entry)
        row.setdefault("timestamp", datetime.now().isoformat(timespec="seconds"))
        with open(self.db_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def _load_all(self) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        if not os.path.exists(self.db_path):
            return rows
        with open(self.db_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if isinstance(obj, dict):
                        rows.append(obj)
                except Exception:
                    continue
        return rows

    def query_experiences(self,
                          root_cause: str,
                          error_type: str = "unknown",
                          phase: str = "unknown",
                          key_symbols: Optional[List[str]] = None,
                          top_k: int = 3) -> List[Dict[str, Any]]:
        key_symbols = key_symbols or []
        top_k = max(1, int(top_k or 3))

        rows = self._load_all()
        if not rows:
            return []

        query_tokens = set(self._tokenize(root_cause) + [s.lower() for s in key_symbols if s])
        candidates = []
        for row in rows:
            score = 0.0
            row_error_type = str(row.get("error_type", "unknown"))
            row_phase = str(row.get("phase", "unknown"))

            if error_type and row_error_type == error_type:
                score += 2.0
            if phase and row_phase == phase:
                score += 1.5

            row_tokens = set(
                self._tokenize(str(row.get("root_cause", "")))
                + self._tokenize(str(row.get("summary", "")))
                + [s.lower() for s in (row.get("key_symbols") or []) if isinstance(s, str)]
            )
            overlap = len(query_tokens.intersection(row_tokens))
            score += min(5.0, overlap * 0.8)

            if score > 0:
                candidates.append((score, row))

        candidates.sort(key=lambda item: item[0], reverse=True)

        result = []
        for score, row in candidates[:top_k]:
            result.append({
                "score": round(float(score), 3),
                "phase": row.get("phase", "unknown"),
                "error_type": row.get("error_type", "unknown"),
                "root_cause": row.get("root_cause", ""),
                "summary": row.get("summary", ""),
                "key_symbols": row.get("key_symbols", []),
                "fix_strategy": row.get("fix_strategy", []),
                "outcome": row.get("outcome", "unknown"),
                "timestamp": row.get("timestamp", "")
            })
        return result
