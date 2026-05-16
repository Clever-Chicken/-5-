from __future__ import annotations

import re

_PUNCTUATION_RE = re.compile(r"[\s,，.。·\-_/（）()【】\[\]{}]+")
_SUFFIX_WORDS = ("基金会", "基金")


def normalize_donor_name(name: str) -> str:
    normalized = _PUNCTUATION_RE.sub("", name.strip())
    for suffix in _SUFFIX_WORDS:
        if normalized.endswith(suffix):
            normalized = normalized[: -len(suffix)]
            break
    return normalized


def group_donor_names(names: list[str]) -> dict[str, str]:
    unique_names = [name for name in dict.fromkeys(names) if name]
    normalized = {name: normalize_donor_name(name) for name in unique_names}
    merge_names = [
        name for name in unique_names if _is_foundation_name(name) and normalized[name]
    ]
    groups = {name: name for name in unique_names}

    key_to_names: dict[str, list[str]] = {}
    for name in merge_names:
        key_to_names.setdefault(normalized[name], []).append(name)

    automaton = _PatternAutomaton(list(key_to_names))
    for candidate in merge_names:
        candidate_key = normalized[candidate]
        for pattern_key in automaton.find(candidate_key):
            for contained_name in key_to_names[pattern_key]:
                groups[contained_name] = _prefer_display_name(groups[contained_name], candidate)

    return groups


def _is_foundation_name(name: str) -> bool:
    return any(suffix in name for suffix in _SUFFIX_WORDS)


def _prefer_display_name(left: str, right: str) -> str:
    if len(right) > len(left):
        return right
    if len(right) == len(left):
        return min(left, right)
    return left


class _PatternAutomaton:
    def __init__(self, patterns: list[str]) -> None:
        self._next: list[dict[str, int]] = [{}]
        self._fail: list[int] = [0]
        self._outputs: list[list[str]] = [[]]
        for pattern in patterns:
            self._add(pattern)
        self._build_failures()

    def find(self, text: str) -> list[str]:
        state = 0
        matches: list[str] = []
        for char in text:
            while state and char not in self._next[state]:
                state = self._fail[state]
            state = self._next[state].get(char, 0)
            matches.extend(self._outputs[state])
        return matches

    def _add(self, pattern: str) -> None:
        state = 0
        for char in pattern:
            next_state = self._next[state].get(char)
            if next_state is None:
                next_state = len(self._next)
                self._next[state][char] = next_state
                self._next.append({})
                self._fail.append(0)
                self._outputs.append([])
            state = next_state
        self._outputs[state].append(pattern)

    def _build_failures(self) -> None:
        queue = list(self._next[0].values())
        for state in queue:
            self._fail[state] = 0

        index = 0
        while index < len(queue):
            state = queue[index]
            index += 1
            for char, next_state in self._next[state].items():
                fail_state = self._fail[state]
                while fail_state and char not in self._next[fail_state]:
                    fail_state = self._fail[fail_state]
                self._fail[next_state] = self._next[fail_state].get(char, 0)
                self._outputs[next_state].extend(self._outputs[self._fail[next_state]])
                queue.append(next_state)
