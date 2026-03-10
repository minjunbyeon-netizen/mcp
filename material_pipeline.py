#!/usr/bin/env python3
"""
홍보자료/PDF/홍보물 입력 파이프라인.

- 여러 파일의 텍스트를 하나의 브리프(source bundle)로 통합
- 긴 원문을 프롬프트 친화적인 핵심 요약으로 압축
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Iterable

from utils import extract_text_from_file


IMPORTANT_KEYWORDS = [
    "모집", "신청", "접수", "일정", "기간", "대상", "지원", "혜택", "문의",
    "참여", "행사", "교육", "과정", "발표", "운영", "개최", "협약", "mou",
    "장소", "시간", "비용", "무료", "선정", "심사", "연락처",
]


def _normalize_text(text: str) -> str:
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_lines(text: str) -> list[str]:
    lines = []
    for line in _normalize_text(text).splitlines():
        clean = re.sub(r"\s+", " ", line).strip()
        if len(clean) >= 4:
            lines.append(clean)
    return lines


def _line_score(line: str) -> int:
    lower = line.lower()
    score = 0
    if 10 <= len(line) <= 120:
        score += 2
    if re.search(r"\d{4}|\d{1,2}[./월-]\d{1,2}", line):
        score += 3
    if re.search(r"\d{2,4}[-)\s]\d{2,4}[-)\s]\d{4}", line):
        score += 2
    if any(keyword in lower for keyword in IMPORTANT_KEYWORDS):
        score += 3
    if "http" in lower or "www." in lower:
        score += 1
    if line.count("•") or line.count("·") or line.count(":"):
        score += 1
    return score


def _dedupe_lines(lines: Iterable[str]) -> list[str]:
    seen = set()
    result = []
    for line in lines:
        key = re.sub(r"\s+", "", line).lower()
        if key and key not in seen:
            seen.add(key)
            result.append(line)
    return result


def _extract_key_lines(text: str, limit: int = 12) -> list[str]:
    scored = sorted(
        _extract_lines(text),
        key=lambda line: (_line_score(line), len(line)),
        reverse=True,
    )
    return _dedupe_lines(scored)[:limit]


def _extract_contact_lines(text: str) -> list[str]:
    lines = _extract_lines(text)
    picks = [
        line for line in lines
        if re.search(r"문의|연락처|전화|상담|홈페이지|접수|신청", line, re.IGNORECASE)
    ]
    return _dedupe_lines(picks)[:5]


def _extract_date_lines(text: str) -> list[str]:
    lines = _extract_lines(text)
    picks = [
        line for line in lines
        if re.search(r"\d{4}|\d{1,2}[./월-]\d{1,2}|까지|예정|오전|오후", line)
    ]
    return _dedupe_lines(picks)[:6]


def _extract_tag_candidates(text: str) -> list[str]:
    words = re.findall(r"[가-힣A-Za-z0-9]{2,}", text)
    stopwords = {
        "그리고", "하지만", "이번", "관련", "위한", "대한", "있습니다", "합니다",
        "하세요", "입니다", "문의", "모집", "신청", "접수", "안내", "자료", "홍보",
    }
    counts = Counter(
        word for word in words
        if word not in stopwords and not word.isdigit()
    )
    return [word for word, _ in counts.most_common(10)]


def infer_topic(text: str) -> str:
    lowered = text.lower()
    if any(keyword in lowered for keyword in ["모집", "선발", "원서접수", "교육생"]):
        return "recruitment"
    if any(keyword in lowered for keyword in ["행사", "축제", "공연", "개최"]):
        return "event"
    if any(keyword in lowered for keyword in ["협약", "mou", "업무협약"]):
        return "partnership"
    if any(keyword in lowered for keyword in ["지원", "혜택", "사업", "참여"]):
        return "program"
    return "announcement"


def build_material_bundle(
    sources: list[dict[str, str]] | None = None,
    direct_text: str = "",
    max_excerpt_chars: int = 7000,
) -> dict:
    """여러 자료를 블로그 작성용 브리프 구조로 통합."""
    material_sources = []
    warnings = []

    for source in sources or []:
        text = _normalize_text(source.get("text", ""))
        if not text:
            warnings.append(f"텍스트 추출 실패: {source.get('name', '이름 없는 자료')}")
            continue
        material_sources.append({
            "name": source.get("name", "자료"),
            "kind": source.get("kind", "file"),
            "text": text,
            "char_count": len(text),
        })

    if direct_text.strip():
        normalized = _normalize_text(direct_text)
        material_sources.append({
            "name": "직접 입력",
            "kind": "text",
            "text": normalized,
            "char_count": len(normalized),
        })

    combined_text = "\n\n".join(
        f"===== {item['name']} =====\n{item['text']}"
        for item in material_sources
    ).strip()

    fact_lines = _extract_key_lines(combined_text)
    contact_lines = _extract_contact_lines(combined_text)
    date_lines = _extract_date_lines(combined_text)
    tag_candidates = _extract_tag_candidates(combined_text)
    topic = infer_topic(combined_text)
    excerpt = combined_text[:max_excerpt_chars].strip()

    source_summary = ", ".join(
        f"{item['name']}({item['char_count']:,}자)"
        for item in material_sources
    ) or "입력 자료 없음"

    briefing_lines = [
        "[자료 구성]",
        source_summary,
        "",
        "[핵심 포인트]",
    ]
    briefing_lines.extend(f"- {line}" for line in fact_lines[:8])

    if date_lines:
        briefing_lines.extend(["", "[주요 일정/숫자]"])
        briefing_lines.extend(f"- {line}" for line in date_lines[:5])

    if contact_lines:
        briefing_lines.extend(["", "[문의/행동 유도]"])
        briefing_lines.extend(f"- {line}" for line in contact_lines[:4])

    if excerpt:
        briefing_lines.extend(["", "[원문 발췌]", excerpt])

    return {
        "sources": [
            {
                "name": item["name"],
                "kind": item["kind"],
                "char_count": item["char_count"],
            }
            for item in material_sources
        ],
        "raw_char_count": sum(item["char_count"] for item in material_sources),
        "combined_text": combined_text,
        "briefing": "\n".join(briefing_lines).strip(),
        "fact_lines": fact_lines,
        "contact_lines": contact_lines,
        "date_lines": date_lines,
        "tag_candidates": tag_candidates,
        "topic": topic,
        "warnings": warnings,
    }


def build_material_bundle_from_paths(file_paths: Iterable[Path], direct_text: str = "") -> dict:
    """파일 경로 목록으로부터 자료 번들 생성."""
    sources = []
    for file_path in file_paths:
        path = Path(file_path)
        sources.append({
            "name": path.name,
            "kind": path.suffix.lower().lstrip(".") or "file",
            "text": extract_text_from_file(path),
        })
    return build_material_bundle(sources=sources, direct_text=direct_text)
