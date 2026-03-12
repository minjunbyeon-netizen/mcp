#!/usr/bin/env python3
"""
블로그 결과물 저장/정규화 유틸리티.

- 단일 버전(content) / 다중 버전(versions) 포맷을 모두 지원
- 웹/CLI/MCP 서버가 동일한 JSON 스키마를 사용하도록 통합
"""

from __future__ import annotations

import copy
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from utils import is_meaningful_text_line, sanitize_text_for_display


DEFAULT_VERSION_ORDER = ["formal", "balanced", "casual"]
DEFAULT_VERSION_LABELS = {
    "formal": "포멀",
    "balanced": "밸런스",
    "casual": "캐주얼",
    "primary": "메인",
}


def sanitize_filename_component(text: str, limit: int = 40) -> str:
    """파일명에 안전한 문자열로 정리."""
    text = re.sub(r"[\\/:*?\"<>|]+", "_", (text or "").strip())
    text = re.sub(r"\s+", " ", text).strip(" ._")
    if not text:
        return "untitled"
    return text[:limit].strip()


def _dedupe_lines(lines: list[str], limit: int | None = None) -> list[str]:
    seen = set()
    result = []
    for line in lines:
        key = re.sub(r"\s+", "", line).lower()
        if key and key not in seen:
            seen.add(key)
            result.append(line)
            if limit and len(result) >= limit:
                break
    return result


def _sanitize_line_list(items: list[Any], limit: int) -> list[str]:
    cleaned = []
    for item in items or []:
        text = sanitize_text_for_display(str(item), allow_cjk=False)
        text = re.sub(r"^[A-Za-z]{4,}(?=[가-힣])", "", text)
        text = re.sub(r"\s+", " ", text).strip(" -|\t")
        if is_meaningful_text_line(text):
            cleaned.append(text)
    return _dedupe_lines(cleaned, limit=limit)


def _sanitize_tag_candidates(items: list[Any], limit: int = 10) -> list[str]:
    cleaned = []
    for item in items or []:
        text = sanitize_text_for_display(str(item), allow_cjk=False)
        text = re.sub(r"[^A-Za-z0-9가-힣]", "", text)
        if len(text) >= 2:
            cleaned.append(text[:40])
    return _dedupe_lines(cleaned, limit=limit)


def _sanitize_source_bundle(bundle: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(bundle, dict):
        return {}

    source_items = []
    for source in bundle.get("sources", []) or []:
        name = sanitize_text_for_display(str((source or {}).get("name", "")), allow_cjk=False)
        name = re.sub(r"^[A-Za-z]{4,}(?=[가-힣])", "", name).strip() or "자료"
        source_items.append({
            "name": name,
            "kind": str((source or {}).get("kind", "file")).strip() or "file",
            "char_count": int((source or {}).get("char_count", 0) or 0),
        })

    combined_text = sanitize_text_for_display(str(bundle.get("combined_text", "")), allow_cjk=False)
    combined_lines = []
    for raw_line in combined_text.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        line = re.sub(r"^[A-Za-z]{4,}(?=[가-힣])", "", line)
        if is_meaningful_text_line(line):
            combined_lines.append(line)
    combined_lines = _dedupe_lines(combined_lines, limit=400)
    combined_text = "\n".join(combined_lines)

    fact_lines = _sanitize_line_list(bundle.get("fact_lines", []), limit=12)
    if not fact_lines:
        fact_lines = combined_lines[:12]

    date_lines = _sanitize_line_list(bundle.get("date_lines", []), limit=6)
    if not date_lines:
        date_lines = [line for line in combined_lines if re.search(r"\d{4}|\d{1,2}[./월-]\d{1,2}|까지|예정|오전|오후", line)][:6]

    contact_lines = _sanitize_line_list(bundle.get("contact_lines", []), limit=5)
    if not contact_lines:
        contact_lines = [line for line in combined_lines if re.search(r"문의|연락처|전화|상담|홈페이지|접수|신청", line, re.IGNORECASE)][:5]

    tag_candidates = _sanitize_tag_candidates(bundle.get("tag_candidates", []), limit=10)
    warnings = _sanitize_line_list(bundle.get("warnings", []), limit=6)
    topic = re.sub(r"[^a-z_]", "", str(bundle.get("topic", "announcement")).lower()) or "announcement"

    source_summary = ", ".join(
        f"{item['name']}({item['char_count']:,}자)"
        for item in source_items
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

    if combined_text:
        briefing_lines.extend(["", "[원문 발췌]", combined_text[:4000]])

    return {
        "sources": source_items,
        "raw_char_count": int(bundle.get("raw_char_count", 0) or 0),
        "combined_text": combined_text,
        "briefing": "\n".join(briefing_lines).strip(),
        "fact_lines": fact_lines,
        "contact_lines": contact_lines,
        "date_lines": date_lines,
        "tag_candidates": tag_candidates,
        "topic": topic,
        "warnings": warnings,
    }


def normalize_blog_version(version: dict[str, Any], index: int = 0) -> dict[str, Any]:
    """개별 버전 dict를 공통 스키마로 정규화."""
    data = copy.deepcopy(version or {})
    version_type = data.get("version_type") or (
        DEFAULT_VERSION_ORDER[index] if index < len(DEFAULT_VERSION_ORDER) else f"variant_{index + 1}"
    )
    version_label = data.get("version_label") or DEFAULT_VERSION_LABELS.get(version_type, f"버전 {index + 1}")
    title = (data.get("title") or "").strip()
    content = (data.get("content") or "").strip()
    tags = [str(tag).strip().lstrip("#") for tag in data.get("tags", []) if str(tag).strip()]

    return {
        "version_type": version_type,
        "version_label": version_label,
        "title": title,
        "content": content,
        "tags": tags,
        "meta_description": (data.get("meta_description") or "").strip(),
        "is_edited": bool(data.get("is_edited", False)),
        "edited_at": data.get("edited_at", ""),
    }


def ensure_blog_package_shape(data: dict[str, Any] | None) -> dict[str, Any]:
    """레거시 단일 버전 포맷을 포함해 블로그 패키지를 공통 스키마로 변환."""
    package = copy.deepcopy(data or {})
    versions = package.get("versions")

    if not isinstance(versions, list) or not versions:
        legacy_content = package.get("content", {})
        if isinstance(legacy_content, dict) and legacy_content.get("title"):
            versions = [
                {
                    "version_type": "primary",
                    "version_label": "메인",
                    "title": legacy_content.get("title", ""),
                    "content": legacy_content.get("content", ""),
                    "tags": legacy_content.get("tags", []),
                    "meta_description": legacy_content.get("meta_description", ""),
                }
            ]
        else:
            versions = []

    normalized_versions = [normalize_blog_version(version, index) for index, version in enumerate(versions)]
    primary = normalized_versions[0] if normalized_versions else {
        "version_type": "primary",
        "version_label": "메인",
        "title": "",
        "content": "",
        "tags": [],
        "meta_description": "",
        "is_edited": False,
        "edited_at": "",
    }

    package["versions"] = normalized_versions
    package["title"] = package.get("title") or primary["title"]
    package["content"] = package.get("content") if isinstance(package.get("content"), dict) else {
        "title": primary["title"],
        "content": primary["content"],
        "tags": primary["tags"],
        "meta_description": primary["meta_description"],
    }
    package["title_variants"] = [
        version["title"] for version in normalized_versions[:3] if version.get("title")
    ] or package.get("title_variants", [])
    package["type"] = package.get("type", "blog")
    package["source_bundle"] = _sanitize_source_bundle(package.get("source_bundle"))
    package.setdefault("created_at", datetime.now().isoformat())
    return package


def build_blog_package(
    output_id: str,
    client_id: str,
    client_name: str,
    versions: list[dict[str, Any]],
    source_bundle: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """공통 블로그 패키지 생성."""
    package = {
        "output_id": output_id,
        "client_id": client_id,
        "client_name": client_name,
        "type": "blog",
        "versions": versions,
        "source_bundle": source_bundle or {},
        "created_at": datetime.now().isoformat(),
    }
    if extra:
        package.update(extra)
    return ensure_blog_package_shape(package)


def _write_markdown(path: Path, version: dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# {version.get('title', '')}\n\n")
        f.write(f"{version.get('content', '')}\n\n")
        tags = version.get("tags", [])
        if tags:
            f.write(f"태그: {', '.join(tags)}\n")


def save_blog_package(package: dict[str, Any], output_dir: Path) -> tuple[Path, dict[str, Path]]:
    """JSON과 마크다운 파일 저장."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    normalized = ensure_blog_package_shape(package)
    output_id = normalized["output_id"]

    json_path = output_dir / f"{output_id}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(normalized, f, ensure_ascii=False, indent=2)

    markdown_paths: dict[str, Path] = {}
    versions = normalized.get("versions", [])
    if versions:
        primary = versions[0]
        primary_md = output_dir / f"{output_id}.md"
        _write_markdown(primary_md, primary)
        markdown_paths["primary"] = primary_md

        for version in versions:
            version_type = version.get("version_type", "primary")
            md_path = output_dir / f"{output_id}_{version_type}.md"
            _write_markdown(md_path, version)
            markdown_paths[version_type] = md_path

    return json_path, markdown_paths


def load_blog_package(json_path: Path) -> dict[str, Any]:
    """JSON 파일을 읽고 공통 스키마로 반환."""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return ensure_blog_package_shape(data)


def update_blog_package_version(
    output_dir: Path,
    output_id: str,
    version_type: str,
    updated_fields: dict[str, Any],
) -> tuple[dict[str, Any], Path]:
    """기존 블로그 패키지의 특정 버전을 갱신."""
    json_path = Path(output_dir) / f"{output_id}.json"
    package = load_blog_package(json_path)
    versions = package.get("versions", [])

    target = None
    for version in versions:
        if version.get("version_type") == version_type:
            target = version
            break

    if target is None:
        target = normalize_blog_version({
            "version_type": version_type,
            "version_label": DEFAULT_VERSION_LABELS.get(version_type, version_type),
        }, len(versions))
        versions.append(target)

    target.update({
        "title": (updated_fields.get("title") or target.get("title") or "").strip(),
        "content": (updated_fields.get("content") or target.get("content") or "").strip(),
        "tags": updated_fields.get("tags", target.get("tags", [])),
        "meta_description": (updated_fields.get("meta_description") or target.get("meta_description") or "").strip(),
        "is_edited": True,
        "edited_at": datetime.now().isoformat(),
    })

    package["versions"] = [normalize_blog_version(version, index) for index, version in enumerate(versions)]
    package["updated_at"] = datetime.now().isoformat()
    package = ensure_blog_package_shape(package)
    save_blog_package(package, output_dir)
    return package, json_path
