#!/usr/bin/env python3
"""Re-enumerate mission entries in Valve missioncycle ``.res`` files.

Only the numeric keys of mission blocks and their category's ``count`` value
are changed. Comments, whitespace, line endings, and all other values are
preserved byte-for-byte.
"""

from __future__ import annotations

import argparse
import os
import stat
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


class MissioncycleError(ValueError):
    """Raised when a file is not a missioncycle document we can safely edit."""


@dataclass(frozen=True)
class Token:
    kind: str
    start: int
    end: int
    value: str = ""
    quoted: bool = False

    def replacement(self, value: str) -> str:
        return f'"{value}"' if self.quoted else value


@dataclass(frozen=True)
class KeyValue:
    key: Token
    value: Token | "KeyValuesObject"


@dataclass(frozen=True)
class KeyValuesObject:
    children: tuple[KeyValue, ...]


@dataclass(frozen=True)
class Edit:
    start: int
    end: int
    replacement: str


def _location(text: str, offset: int) -> str:
    line = text.count("\n", 0, offset) + 1
    previous_newline = text.rfind("\n", 0, offset)
    column = offset - previous_newline
    return f"line {line}, column {column}"


def _tokenize(text: str) -> list[Token]:
    tokens: list[Token] = []
    cursor = 0

    while cursor < len(text):
        character = text[cursor]

        if character.isspace():
            cursor += 1
            continue

        if text.startswith("//", cursor):
            newline = text.find("\n", cursor + 2)
            cursor = len(text) if newline == -1 else newline + 1
            continue

        if text.startswith("/*", cursor):
            comment_end = text.find("*/", cursor + 2)
            if comment_end == -1:
                raise MissioncycleError(
                    f"unterminated block comment at {_location(text, cursor)}"
                )
            cursor = comment_end + 2
            continue

        if character == '"':
            start = cursor
            cursor += 1
            value_start = cursor
            while cursor < len(text):
                if text[cursor] == "\\":
                    cursor += 2
                    continue
                if cursor < len(text) and text[cursor] == '"':
                    tokens.append(
                        Token(
                            "string",
                            start,
                            cursor + 1,
                            text[value_start:cursor],
                            quoted=True,
                        )
                    )
                    cursor += 1
                    break
                cursor += 1
            else:
                raise MissioncycleError(
                    f"unterminated quoted string at {_location(text, start)}"
                )
            continue

        if character in "{}":
            kind = "lbrace" if character == "{" else "rbrace"
            tokens.append(Token(kind, cursor, cursor + 1))
            cursor += 1
            continue

        start = cursor
        while (
            cursor < len(text)
            and not text[cursor].isspace()
            and text[cursor] not in "{}"
            and not text.startswith("//", cursor)
            and not text.startswith("/*", cursor)
        ):
            cursor += 1
        if cursor == start:
            raise MissioncycleError(
                f"unexpected character at {_location(text, cursor)}"
            )
        tokens.append(Token("string", start, cursor, text[start:cursor]))

    return tokens


class _Parser:
    def __init__(self, text: str, tokens: Sequence[Token]) -> None:
        self.text = text
        self.tokens = tokens
        self.cursor = 0

    def parse_document(self) -> KeyValue:
        root = self._parse_key_value()
        if self.cursor != len(self.tokens):
            token = self.tokens[self.cursor]
            raise MissioncycleError(
                f"unexpected content after root object at "
                f"{_location(self.text, token.start)}"
            )
        if not isinstance(root.value, KeyValuesObject):
            raise MissioncycleError("the document root must be an object")
        return root

    def _parse_key_value(self) -> KeyValue:
        key = self._take("string", "expected a key")
        if self.cursor >= len(self.tokens):
            raise MissioncycleError(
                f"missing value for key {key.value!r} at "
                f"{_location(self.text, key.start)}"
            )

        token = self.tokens[self.cursor]
        if token.kind == "string":
            self.cursor += 1
            return KeyValue(key, token)
        if token.kind == "lbrace":
            self.cursor += 1
            children: list[KeyValue] = []
            while True:
                if self.cursor >= len(self.tokens):
                    raise MissioncycleError(
                        f"unclosed object for key {key.value!r} at "
                        f"{_location(self.text, key.start)}"
                    )
                if self.tokens[self.cursor].kind == "rbrace":
                    self.cursor += 1
                    return KeyValue(key, KeyValuesObject(tuple(children)))
                children.append(self._parse_key_value())

        raise MissioncycleError(
            f"expected a value for key {key.value!r} at "
            f"{_location(self.text, token.start)}"
        )

    def _take(self, kind: str, message: str) -> Token:
        if self.cursor >= len(self.tokens):
            raise MissioncycleError(f"{message} at end of file")
        token = self.tokens[self.cursor]
        if token.kind != kind:
            raise MissioncycleError(
                f"{message} at {_location(self.text, token.start)}"
            )
        self.cursor += 1
        return token


def _one_scalar(
    children: Sequence[KeyValue], name: str, *, context: str
) -> Token:
    matches = [child for child in children if child.key.value.casefold() == name]
    if len(matches) != 1:
        raise MissioncycleError(
            f"{context} must contain exactly one scalar {name!r} key"
        )
    value = matches[0].value
    if isinstance(value, KeyValuesObject):
        raise MissioncycleError(f"{context} key {name!r} must have a scalar value")
    return value


def reenumerate(text: str) -> tuple[str, int, int]:
    """Return corrected text, number of categories, and number of missions."""

    tokens = _tokenize(text)
    if not tokens:
        raise MissioncycleError("file is empty")
    root = _Parser(text, tokens).parse_document()
    assert isinstance(root.value, KeyValuesObject)

    categories_value = _one_scalar(
        root.value.children, "categories", context="root object"
    )
    category_blocks = [
        child
        for child in root.value.children
        if child.key.value.isdecimal()
        and isinstance(child.value, KeyValuesObject)
    ]
    if not category_blocks:
        raise MissioncycleError("root object contains no numeric category blocks")
    if categories_value.value != str(len(category_blocks)):
        raise MissioncycleError(
            "the root 'categories' value does not match the number of category "
            "blocks; category restructuring must be corrected manually"
        )

    edits: list[Edit] = []
    mission_count = 0
    for category in category_blocks:
        assert isinstance(category.value, KeyValuesObject)
        context = f"category {category.key.value!r}"
        count_value = _one_scalar(category.value.children, "count", context=context)
        mission_blocks = [
            child
            for child in category.value.children
            if child.key.value.isdecimal()
            and isinstance(child.value, KeyValuesObject)
        ]

        numeric_scalars = [
            child.key.value
            for child in category.value.children
            if child.key.value.isdecimal()
            and not isinstance(child.value, KeyValuesObject)
        ]
        if numeric_scalars:
            raise MissioncycleError(
                f"{context} contains numeric scalar keys, which are ambiguous: "
                + ", ".join(numeric_scalars)
            )

        desired_count = str(len(mission_blocks))
        if count_value.value != desired_count:
            edits.append(
                Edit(
                    count_value.start,
                    count_value.end,
                    count_value.replacement(desired_count),
                )
            )

        for number, mission in enumerate(mission_blocks, start=1):
            desired_number = str(number)
            if mission.key.value != desired_number:
                edits.append(
                    Edit(
                        mission.key.start,
                        mission.key.end,
                        mission.key.replacement(desired_number),
                    )
                )
        mission_count += len(mission_blocks)

    for edit in sorted(edits, key=lambda item: item.start, reverse=True):
        text = text[: edit.start] + edit.replacement + text[edit.end :]
    return text, len(category_blocks), mission_count


def _atomic_write(path: Path, data: bytes) -> None:
    original_mode = stat.S_IMODE(path.stat().st_mode)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=path.parent, prefix=f".{path.name}.", delete=False
        ) as temporary:
            temporary_name = temporary.name
            temporary.write(data)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.chmod(temporary_name, original_mode)
        os.replace(temporary_name, path)
        temporary_name = None
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)


def _expand_paths(arguments: Sequence[str]) -> list[Path]:
    if not arguments:
        return sorted(Path.cwd().glob("*missioncycle*.res"))

    paths: list[Path] = []
    for argument in arguments:
        path = Path(argument)
        if path.is_dir():
            paths.extend(sorted(path.glob("*missioncycle*.res")))
        else:
            paths.append(path)
    return paths


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Renumber mission entries in each category and correct category counts "
            "without reformatting Valve KeyValues files."
        )
    )
    parser.add_argument(
        "paths",
        metavar="PATH",
        nargs="*",
        help=(
            "missioncycle file or directory; defaults to *missioncycle*.res in "
            "the current directory"
        ),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="report files that need changes without modifying them",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    paths = _expand_paths(args.paths)
    if not paths:
        print("error: no missioncycle .res files found", file=sys.stderr)
        return 2

    exit_code = 0
    for path in paths:
        try:
            original_bytes = path.read_bytes()
            original = original_bytes.decode("utf-8")
            corrected, category_count, mission_count = reenumerate(original)
        except (OSError, UnicodeError, MissioncycleError) as error:
            print(f"error: {path}: {error}", file=sys.stderr)
            exit_code = 2
            continue

        changed = corrected != original
        summary = (
            f"{category_count} categor{'y' if category_count == 1 else 'ies'}, "
            f"{mission_count} missions"
        )
        if args.check:
            status = "needs update" if changed else "ok"
            print(f"{path}: {status} ({summary})")
            if changed and exit_code == 0:
                exit_code = 1
        elif changed:
            try:
                _atomic_write(path, corrected.encode("utf-8"))
            except OSError as error:
                print(f"error: {path}: {error}", file=sys.stderr)
                exit_code = 2
                continue
            print(f"{path}: updated ({summary})")
        else:
            print(f"{path}: already correct ({summary})")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
