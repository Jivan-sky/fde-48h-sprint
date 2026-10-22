#!/usr/bin/env python3
"""Static checks for the Markdown-only skill repository.

Dev/CI only. The skill itself has no runtime dependency on Python.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote


ROOT = (
    Path(sys.argv[1]).resolve()
    if len(sys.argv) > 1
    else Path(__file__).resolve().parents[1]
)
SKIP_DIRS = {".git", "__pycache__", "node_modules"}
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
DRIVE_PATH_RE = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]")
HOME_PATH_RE = re.compile(r"/(?:Users|home)/[^/\s]+/")
ALLOWED_SCHEMES = ("http://", "https://", "mailto:", "tel:", "#")


def markdown_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*.md"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        files.append(path)
    return sorted(files)


def split_cells(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in re.split(r"(?<!\\)\|", stripped)]


def is_separator(line: str) -> bool:
    cells = split_cells(line)
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)


def check_table(path: Path, lines: list[str], in_fence: list[bool]) -> list[str]:
    errors: list[str] = []
    index = 0
    while index < len(lines) - 1:
        if (
            not in_fence[index]
            and "|" in lines[index]
            and is_separator(lines[index + 1])
        ):
            header = split_cells(lines[index])
            separator = split_cells(lines[index + 1])
            if len(header) != len(separator):
                errors.append(
                    f"{path}:{index + 1}: 表头 {len(header)} 列，分隔行 {len(separator)} 列"
                )
            index += 2
            while index < len(lines) and not in_fence[index] and lines[index].strip().startswith("|"):
                cells = split_cells(lines[index])
                if len(cells) != len(header):
                    errors.append(
                        f"{path}:{index + 1}: 表格行 {len(cells)} 列，表头 {len(header)} 列"
                    )
                index += 1
            continue
        index += 1
    return errors


def check_links(path: Path, lines: list[str], in_fence: list[bool]) -> list[str]:
    errors: list[str] = []
    for line_number, (line, fenced) in enumerate(zip(lines, in_fence), start=1):
        if fenced:
            continue
        for raw_target in LINK_RE.findall(line):
            target = raw_target.strip()
            if target.startswith(ALLOWED_SCHEMES):
                continue
            target = unquote(target.split("#", 1)[0].split("?", 1)[0])
            if not target:
                continue
            resolved = (path.parent / target).resolve()
            try:
                resolved.relative_to(ROOT)
            except ValueError:
                errors.append(f"{path}:{line_number}: 链接越出仓库：{raw_target}")
                continue
            if not resolved.exists():
                errors.append(f"{path}:{line_number}: 链接目标不存在：{raw_target}")
    return errors


def check_file(path: Path) -> tuple[list[str], int]:
    errors: list[str] = []
    try:
        text = path.read_bytes().decode("utf-8")
    except UnicodeDecodeError as exc:
        return [f"{path}: 不是合法 UTF-8：{exc}"], 0

    lines = text.splitlines()
    fence_markers = 0
    in_fence: list[bool] = []
    current = False
    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            fence_markers += 1
            current = not current
            in_fence.append(True)
            continue
        in_fence.append(current)
        if not current:
            if DRIVE_PATH_RE.search(line):
                errors.append(f"{path}:{line_number}: 出现本机绝对路径（盘符）")
            if HOME_PATH_RE.search(line):
                errors.append(f"{path}:{line_number}: 出现本机用户目录")

    if fence_markers % 2 != 0:
        errors.append(f"{path}: 代码围栏未闭合（标记数 {fence_markers}）")

    errors.extend(check_table(path, lines, in_fence))
    errors.extend(check_links(path, lines, in_fence))
    return errors, len(lines)


def main() -> int:
    files = markdown_files()
    errors: list[str] = []
    total_lines = 0
    for path in files:
        file_errors, line_count = check_file(path)
        errors.extend(file_errors)
        total_lines += line_count

    if errors:
        print(f"FAIL: {len(errors)} issue(s) across {len(files)} Markdown file(s)")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"OK: {len(files)} Markdown files, {total_lines} lines; UTF-8, fences, links, tables, local paths")
    return 0


if __name__ == "__main__":
    sys.exit(main())
