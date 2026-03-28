from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCAL_SECRET_SOURCES = (
    ROOT / ".env",
    ROOT / "config" / "sepolia.env",
    ROOT / "frontend" / ".env",
)
SECRET_KEY_MARKERS = (
    "private_key",
    "mnemonic",
    "seed",
    "seed_phrase",
    "api_key",
    "secret",
    "password",
    "passphrase",
    "rpc_url",
)
PLACEHOLDER_MARKERS = (
    "example",
    "placeholder",
    "changeme",
    "change-me",
    "replace",
    "your-",
    "your_",
    "<",
    ">",
    "{",
    "}",
    "dummy",
    "sample",
)
GENERIC_HISTORY_PATTERNS = {
    "private-key block": r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    "AWS access key": r"AKIA[0-9A-Z]{16}",
    "GitHub token": r"ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{20,}",
    "OpenAI-style key": r"sk-[A-Za-z0-9]{20,}",
    "Slack token": r"xox[baprs]-[A-Za-z0-9-]{10,}",
}
ASSIGNMENT_RE = re.compile(
    r"""(?ix)
    \b
    (?P<key>[A-Z0-9_.-]*(?:private[_-]?key|mnemonic|seed(?:[_-]?phrase)?|api[_-]?key|secret(?:[_-]?key)?|token|password|passphrase|rpc[_-]?url)[A-Z0-9_.-]*)
    \b
    [^:=\n]{0,20}
    (?P<sep>[:=])
    \s*
    ['"]?
    (?P<value>[^'"\s,#]+)
    """
)
TEXT_BINARY_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".bmp",
    ".pdf",
    ".xlsx",
    ".xls",
    ".xlsm",
    ".docx",
    ".pptx",
    ".zip",
    ".7z",
    ".gz",
    ".exe",
    ".dll",
    ".bin",
}


@dataclass(frozen=True)
class Finding:
    category: str
    location: str
    detail: str


def run_git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or f"git {' '.join(args)} failed")
    return completed.stdout


def split_nul_lines(payload: str) -> list[str]:
    return [entry for entry in payload.split("\x00") if entry]


def repo_paths() -> list[Path]:
    return [ROOT / rel for rel in split_nul_lines(run_git("ls-files", "-z", "--cached", "--others", "--exclude-standard"))]


def git_revisions() -> list[str]:
    return [entry for entry in run_git("rev-list", "--all").splitlines() if entry]


def is_text_file(path: Path) -> bool:
    if path.suffix.lower() in TEXT_BINARY_SUFFIXES:
        return False
    try:
        sample = path.read_bytes()[:4096]
    except OSError:
        return False
    if b"\x00" in sample:
        return False
    control_chars = sum(1 for byte in sample if byte < 9 or 13 < byte < 32)
    return control_chars < 24


def read_text(path: Path) -> str | None:
    if not path.exists() or not path.is_file() or not is_text_file(path):
        return None
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            return path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return None


def looks_like_placeholder(value: str) -> bool:
    lowered = value.strip().strip("'\"").lower()
    if lowered in {"", "none", "null"}:
        return True
    return any(marker in lowered for marker in PLACEHOLDER_MARKERS)


def looks_like_secret_value(key: str, value: str) -> bool:
    lowered_key = key.lower()
    trimmed = value.strip().strip("'\"")
    if not is_secret_key_name(key):
        return False
    if not trimmed or looks_like_placeholder(trimmed):
        return False
    if any(char in trimmed for char in "(){}[],"):
        return False

    if "private" in lowered_key:
        return re.fullmatch(r"(?:0x)?[0-9a-fA-F]{64}", trimmed) is not None
    if "rpc_url" in lowered_key:
        return trimmed.startswith(("http://", "https://", "wss://")) and "your-" not in trimmed.lower()
    if "mnemonic" in lowered_key or "seed" in lowered_key:
        return len(trimmed.split()) >= 12
    if any(
        marker in lowered_key
        for marker in ("api_token", "access_token", "auth_token", "bearer_token", "session_token", "api_key", "secret", "password", "passphrase")
    ):
        return len(trimmed) >= 16 and " " not in trimmed
    return False


def is_secret_key_name(key: str) -> bool:
    normalized = key.lower().replace("-", "_").replace(".", "_")
    if any(marker in normalized for marker in SECRET_KEY_MARKERS):
        return True
    return any(
        marker in normalized
        for marker in (
            "api_token",
            "access_token",
            "auth_token",
            "bearer_token",
            "session_token",
            "github_token",
            "slack_token",
            "bot_token",
        )
    )


def load_local_secret_values() -> dict[str, str]:
    values: dict[str, str] = {}
    for path in LOCAL_SECRET_SOURCES:
        if not path.exists():
            continue
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if not is_secret_key_name(key.strip()):
                continue
            if looks_like_secret_value(key.strip(), value):
                values[key.strip()] = value.strip()
    return values


def is_sensitive_path(path: Path) -> bool:
    rel = path.relative_to(ROOT).as_posix().lower()
    name = path.name.lower()
    if any(name.endswith(suffix) for suffix in (".example", ".sample", ".template")):
        return False
    if name == ".env":
        return True
    if name.endswith(".env") or ".env." in name:
        return True
    if name.endswith((".pem", ".key", ".p12", ".pfx", ".jks", ".keystore")):
        return True
    if "keystore/" in rel or rel.startswith("keystore/"):
        return True
    if "wallets/" in rel or rel.startswith("wallets/"):
        return True
    return name.endswith(".json") and "keystore" in name


def scan_worktree_paths(paths: list[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for path in paths:
        if is_sensitive_path(path):
            findings.append(
                Finding(
                    category="sensitive-path",
                    location=path.relative_to(ROOT).as_posix(),
                    detail="Non-ignored file name looks like a secret/env/keystore artifact.",
                )
            )
    return findings


def scan_worktree_content(paths: list[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for path in paths:
        text = read_text(path)
        if text is None:
            continue
        rel = path.relative_to(ROOT).as_posix()
        for line_number, raw_line in enumerate(text.splitlines(), start=1):
            match = ASSIGNMENT_RE.search(raw_line)
            if match is None:
                continue
            key = match.group("key")
            value = match.group("value")
            if looks_like_secret_value(key, value):
                findings.append(
                    Finding(
                        category="secret-assignment",
                        location=f"{rel}:{line_number}",
                        detail=f"Suspicious non-placeholder value assigned to {key}.",
                    )
                )
    return findings


def scan_exact_values(paths: list[Path], secrets: dict[str, str]) -> list[Finding]:
    findings: list[Finding] = []
    if not secrets:
        return findings
    text_cache: dict[Path, str | None] = {}
    for path in paths:
        text_cache[path] = read_text(path)
    for key, value in secrets.items():
        for path, text in text_cache.items():
            if text is None or value not in text:
                continue
            rel = path.relative_to(ROOT).as_posix()
            findings.append(
                Finding(
                    category="exact-secret-match",
                    location=rel,
                    detail=f"Exact value from local secret {key} appears in a repo file.",
                )
            )
    return findings


def scan_history_sensitive_paths() -> list[Finding]:
    findings: list[Finding] = []
    history_paths = run_git("log", "--all", "--name-only", "--pretty=format:").splitlines()
    seen: set[str] = set()
    for rel in history_paths:
        if not rel:
            continue
        path = ROOT / rel
        if not is_sensitive_path(path):
            continue
        key = rel.lower()
        if key in seen:
            continue
        seen.add(key)
        findings.append(
            Finding(
                category="history-sensitive-path",
                location=rel,
                detail="A sensitive-looking file path appears somewhere in git history.",
            )
        )
    return findings


def scan_history_generic_patterns(revisions: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    if not revisions:
        return findings
    for label, pattern in GENERIC_HISTORY_PATTERNS.items():
        completed = subprocess.run(
            ["git", "grep", "-I", "-l", "-E", "-e", pattern, *revisions],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode not in {0, 1}:
            raise RuntimeError(completed.stderr.strip() or f"git grep failed for pattern {label}")
        for entry in completed.stdout.splitlines():
            findings.append(
                Finding(
                    category="history-pattern-match",
                    location=entry,
                    detail=f"Git history matches the high-signal pattern: {label}.",
                )
            )
    return findings


def scan_history_exact_values(secrets: dict[str, str], revisions: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    if not revisions:
        return findings
    for key, value in secrets.items():
        completed = subprocess.run(
            ["git", "grep", "-F", "-l", "-e", value, *revisions],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode not in {0, 1}:
            raise RuntimeError(completed.stderr.strip() or f"git grep failed for exact secret {key}")
        for entry in completed.stdout.splitlines():
            findings.append(
                Finding(
                    category="history-exact-secret-match",
                    location=entry,
                    detail=f"Git history contains the exact value for local secret {key}.",
                )
            )
    return findings


def print_findings(findings: list[Finding], exact_secret_count: int) -> int:
    if not findings:
        print(
            f"Secret scan passed. Checked worktree and history with {exact_secret_count} local exact-value source(s)."
        )
        return 0

    print("Secret scan failed with the following findings:")
    for finding in findings:
        print(f"- [{finding.category}] {finding.location}: {finding.detail}")
    return 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scan the repository worktree and git history for secret leaks and sensitive file paths.",
    )
    parser.add_argument(
        "--skip-history",
        action="store_true",
        help="Only scan the current worktree and skip the git history pass.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    paths = repo_paths()
    secrets = load_local_secret_values()

    findings = []
    findings.extend(scan_worktree_paths(paths))
    findings.extend(scan_worktree_content(paths))
    findings.extend(scan_exact_values(paths, secrets))

    if not args.skip_history:
        revisions = git_revisions()
        findings.extend(scan_history_sensitive_paths())
        findings.extend(scan_history_generic_patterns(revisions))
        findings.extend(scan_history_exact_values(secrets, revisions))

    unique_findings = list(dict.fromkeys(findings))
    return print_findings(unique_findings, len(secrets))


if __name__ == "__main__":
    sys.exit(main())
