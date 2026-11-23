"""架構檢查：`src/lecture_quiz/core/` 只能是純函式（技術限制 4，NON-NEGOTIABLE）。

以 `ast` 靜態掃描核心層每個 .py 檔：
- 不得匯入 fastapi、starlette、asyncio、socket、time、
  lecture_quiz.app、lecture_quiz.adapters
  （包含相對匯入解析後指向 app／adapters 的情況）。
- 不得呼叫 datetime.now、datetime.utcnow、date.today（含別名，時間由呼叫端傳入）。
- 不得使用萬用匯入（`from x import *`），否則無法追蹤呼叫來源。

相依方向只能是 adapters → app → core。依據：研究 R4。
"""

import ast
from pathlib import Path

import pytest

SRC_ROOT = Path(__file__).resolve().parents[2] / "src"
CORE_DIR = SRC_ROOT / "lecture_quiz" / "core"

FORBIDDEN_MODULES = (
    "fastapi",
    "starlette",
    "asyncio",
    "socket",
    "time",
    "lecture_quiz.app",
    "lecture_quiz.adapters",
)
FORBIDDEN_CLOCK_CALLS = {
    ("datetime", "now"),
    ("datetime", "utcnow"),
    ("date", "today"),
}


def _module_package(path: Path, src_root: Path) -> list[str]:
    """回傳檔案所在套件的名稱片段，用來解析相對匯入。"""
    parts = list(path.relative_to(src_root).with_suffix("").parts)
    if parts[-1] == "__init__":
        return parts[:-1]
    return parts[:-1]


def _is_forbidden(module: str) -> bool:
    return any(module == m or module.startswith(m + ".") for m in FORBIDDEN_MODULES)


def _imported_modules(node: ast.AST, package: list[str]) -> list[str]:
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if isinstance(node, ast.ImportFrom):
        if node.level == 0:
            base = node.module or ""
        else:
            anchor = package[: len(package) - (node.level - 1)]
            base = ".".join([*anchor, *([node.module] if node.module else [])])
        if node.module is None:
            return [f"{base}.{alias.name}" for alias in node.names]
        return [base]
    return []


def _datetime_aliases(tree: ast.AST) -> dict[str, str]:
    """收集 `from datetime import datetime as dt` 這類別名，對應回原名。"""
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "datetime":
            for alias in node.names:
                if alias.name in {"datetime", "date"}:
                    aliases[alias.asname or alias.name] = alias.name
    return aliases


def _clock_call(node: ast.AST, aliases: dict[str, str]) -> str | None:
    if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
        return None
    owner = node.func.value
    owner_name = (
        aliases.get(owner.id, owner.id)
        if isinstance(owner, ast.Name)
        else owner.attr
        if isinstance(owner, ast.Attribute)
        else None
    )
    if (owner_name, node.func.attr) in FORBIDDEN_CLOCK_CALLS:
        return f"{owner_name}.{node.func.attr}"
    return None


def find_violations(path: Path, src_root: Path = SRC_ROOT) -> list[str]:
    """回傳單一檔案中違反核心純函式規則的描述；空清單表示通過。"""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    package = _module_package(path, src_root)
    aliases = _datetime_aliases(tree)
    violations: list[str] = []
    for node in ast.walk(tree):
        for module in _imported_modules(node, package):
            if _is_forbidden(module):
                violations.append(f"{path.name}:{node.lineno} 匯入 {module}")
        if isinstance(node, ast.ImportFrom) and any(a.name == "*" for a in node.names):
            # 萬用匯入會讓呼叫來源無法追蹤，核心一律禁止
            violations.append(f"{path.name}:{node.lineno} 萬用匯入 {node.module}")
        call = _clock_call(node, aliases)
        if call is not None:
            violations.append(f"{path.name}:{node.lineno} 呼叫 {call}()")
    return violations


def test_core_directory_exists():
    assert CORE_DIR.is_dir()


def test_core_is_pure():
    violations = [v for f in sorted(CORE_DIR.rglob("*.py")) for v in find_violations(f)]
    assert violations == [], "核心層違反純函式限制：\n" + "\n".join(violations)


# ── 檢查器自我測試：確認真的抓得到違規，避免核心是空的時候測試形同虛設 ──


def _write_core_module(tmp_path: Path, source: str) -> tuple[Path, Path]:
    module_dir = tmp_path / "lecture_quiz" / "core" / "sample"
    module_dir.mkdir(parents=True)
    path = module_dir / "module.py"
    path.write_text(source, encoding="utf-8")
    return path, tmp_path


@pytest.mark.parametrize(
    "source",
    [
        "import fastapi\n",
        "from starlette.requests import Request\n",
        "import asyncio\n",
        "import socket\n",
        "import time\n",
        "from time import monotonic\n",
        "from lecture_quiz.app.activity import service\n",
        "import lecture_quiz.adapters.clock\n",
        "from ...app import activity\n",
        "from ... import adapters\n",
        "from datetime import datetime\nx = datetime.now()\n",
        "import datetime\nx = datetime.datetime.utcnow()\n",
        "from datetime import date\nx = date.today()\n",
        # 別名與萬用匯入（PR #14 審查建議第 4 項）
        "from datetime import datetime as dt\nx = dt.now()\n",
        "from datetime import date as d\nx = d.today()\n",
        "import datetime as dtm\nx = dtm.datetime.now()\n",
        "from datetime import *\n",
        "import time as t\n",
        "from asyncio import sleep as s\n",
    ],
)
def test_checker_detects_violation(tmp_path, source):
    path, root = _write_core_module(tmp_path, source)
    assert find_violations(path, root) != []


@pytest.mark.parametrize(
    "source",
    [
        "from dataclasses import dataclass\n",
        "from datetime import datetime, timedelta\n"
        "def f(now: datetime) -> datetime:\n    return now + timedelta(seconds=1)\n",
        "from ..other import models\n",
        "from lecture_quiz.core.other import models\n",
        "import datetime_helpers\n",
        "from datetime import datetime as dt\ndef f(now: dt) -> dt:\n    return now\n",
        "from datetime import timezone\nx = timezone.utc\n",
    ],
)
def test_checker_allows_pure_code(tmp_path, source):
    path, root = _write_core_module(tmp_path, source)
    assert find_violations(path, root) == []
