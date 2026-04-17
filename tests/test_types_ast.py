"""§F5 — AST walker asserts no unjustified Any in new module public API.

Catches Any in generics (list[Any], dict[str, Any]) that regex-based
checks miss. Asserts files_scanned>0 to prevent vacuous pass on a path typo.
"""
from __future__ import annotations
import ast
import pathlib
import unittest

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_TARGETS = [
    "src/bp_writeback",
    "src/bp_temporal",
    "src/bp_analytics",
    "src/bp_research",
    "src/bp_routing.py",
]
_JUSTIFY_TAG = "# type-ok:"


def _walk():
    offenses: list[str] = []
    files_scanned = 0
    for target in _TARGETS:
        p = _ROOT / target
        paths = [p] if p.is_file() else list(p.rglob("*.py"))
        for fp in paths:
            if "__pycache__" in fp.parts:
                continue
            if not fp.exists():
                continue
            files_scanned += 1
            try:
                src = fp.read_text(encoding="utf-8")
                tree = ast.parse(src, filename=str(fp))
            except (SyntaxError, UnicodeDecodeError):
                continue
            src_lines = src.splitlines()
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and node.id == "Any":
                    # Skip imports: `from typing import Any` creates `alias`, not `Name`
                    line = src_lines[node.lineno - 1] if node.lineno <= len(src_lines) else ""
                    if _JUSTIFY_TAG in line:
                        continue
                    offenses.append(f"{fp.relative_to(_ROOT)}:{node.lineno}  {line.strip()}")
    return offenses, files_scanned


class AstTypeWalkerTest(unittest.TestCase):
    def test_no_unjustified_any(self):
        offenses, files_scanned = _walk()
        self.assertGreater(files_scanned, 0,
                            "AST walker found no files — target paths misconfigured")
        self.assertEqual(
            offenses, [],
            "Unjustified `Any` usage (add `# type-ok: <reason>` if intentional):\n"
            + "\n".join(offenses),
        )


if __name__ == "__main__":
    unittest.main()
