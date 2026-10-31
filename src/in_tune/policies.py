"""The store manual, as the numbered sections extracted to data/policies.md."""

from __future__ import annotations

import re
from pathlib import Path

DEFAULT_POLICY_FILE = Path(__file__).resolve().parents[2] / "data" / "policies.md"
SECTION = re.compile(r"^## (\S+) — (.+)$", re.MULTILINE)


class Policies:
    def __init__(self, path: Path = DEFAULT_POLICY_FILE):
        text = path.read_text(encoding="utf-8")
        headings = list(SECTION.finditer(text))
        self.sections: dict[str, tuple[str, str]] = {}
        for match, following in zip(headings, headings[1:] + [None], strict=True):
            end = following.start() if following else len(text)
            self.sections[match[1]] = (match[2], text[match.end() : end].strip())

    def index(self) -> str:
        """One line per section, for the system prompt."""
        return "\n".join(f"{number} — {title}" for number, (title, _) in self.sections.items())

    def get(self, section: str) -> dict:
        """A section with its subsections: '4' returns 4, 4.1, 4.2, 4.3 and 4.4."""
        section = section.strip().removeprefix("§").rstrip(".")
        wanted = [n for n in self.sections if n == section or n.startswith(f"{section}.")]
        if not wanted:
            return {"found": False, "available_sections": list(self.sections)}
        return {
            "found": True,
            "sections": [
                {"section": n, "title": self.sections[n][0], "text": self.sections[n][1]}
                for n in wanted
            ],
        }
