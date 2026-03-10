#!/usr/bin/env python3
"""
API 키가 없거나 AI 호출이 실패할 때 사용하는 오프라인 보조 엔진.

- 페르소나 분석: 규칙 기반 휴리스틱
- 블로그 생성: 자료 브리프 기반 3버전 초안 생성
"""

from __future__ import annotations

import re
from typing import Any


def _clamp(value: float, low: int = 1, high: int = 10) -> int:
    return max(low, min(high, int(round(value))))


def _pick_examples(lines: list[str], keywords: list[str], limit: int = 3) -> list[str]:
    matches = []
    for line in lines:
        lower = line.lower()
        if any(keyword.lower() in lower for keyword in keywords):
            matches.append(line)
    return matches[:limit] or lines[:limit]


def analyze_persona_offline(
    client_name: str,
    organization: str,
    kakao_chat_log: str,
    category: str = "general",
) -> dict[str, Any]:
    """카카오톡 대화를 휴리스틱으로 분석해 페르소나 스키마 생성."""
    text = (kakao_chat_log or "").replace("\r", "\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    joined = "\n".join(lines)

    formal_hits = len(re.findall(r"드립니다|부탁드립니다|안녕하세요|감사합니다|입니다|습니다", joined))
    polite_hits = len(re.findall(r"해요|예요|주세요|가능하실까요|괜찮을까요", joined))
    casual_hits = len(re.findall(r"\b해\b|야\b|ㅋㅋ|ㅎㅎ|\^\^|~", joined))
    urgency_hits = len(re.findall(r"급|빠르게|빨리|오늘|내일|마감|즉시|바로", joined))
    detail_hits = len(re.findall(r"확인|수정|일정|내용|세부|첨부|파일|링크|정리|안내", joined))
    decision_hits = len(re.findall(r"진행|확정|결정|부탁|부탁드려요|해주세요", joined))
    emoji_hits = len(re.findall(r"[😀-🙏🚀-🧠]|ㅋ|ㅎ|\^\^|ㅠ|ㅜ", joined))
    question_hits = joined.count("?")
    exclamation_hits = joined.count("!")
    gratitude_hits = len(re.findall(r"감사|고맙", joined))

    sentence_lengths = [len(line) for line in lines if len(line) >= 4]
    avg_length = sum(sentence_lengths) / len(sentence_lengths) if sentence_lengths else 30

    formality_score = _clamp(5 + formal_hits * 0.25 + polite_hits * 0.1 - casual_hits * 0.2 - emoji_hits * 0.1)
    detail_score = _clamp(4 + detail_hits * 0.25 + avg_length / 80)
    urgency_score = _clamp(3 + urgency_hits * 0.6)
    perfectionism_score = _clamp((detail_score * 0.7) + (urgency_score * 0.3))
    flexibility_score = _clamp(7 - (urgency_score * 0.3) - (perfectionism_score * 0.2))
    directness_score = _clamp(4 + decision_hits * 0.2 + question_hits * 0.05 - polite_hits * 0.05)
    emotional_score = _clamp(3 + exclamation_hits * 0.15 + emoji_hits * 0.3 + gratitude_hits * 0.15)
    jargon_score = _clamp(3 + len(re.findall(r"기관|공고|사업|운영|프로그램|과정|신청", joined)) * 0.25)
    image_importance = _clamp(3 + len(re.findall(r"이미지|사진|배너|카드뉴스|포스터|홍보물", joined)) * 0.5)

    if avg_length < 18:
        sentence_style = "short"
    elif avg_length < 38:
        sentence_style = "medium"
    else:
        sentence_style = "long"

    if directness_score >= 7:
        directness_style = "direct"
    elif directness_score <= 4:
        directness_style = "indirect"
    else:
        directness_style = "diplomatic"

    if urgency_score >= 7:
        response_pattern = "즉시응답요구"
    elif urgency_score <= 4:
        response_pattern = "여유있음"
    else:
        response_pattern = "유연함"

    if detail_score >= 7:
        feedback_type = "상세"
    elif detail_score <= 4:
        feedback_type = "간결"
    else:
        feedback_type = "균형"

    if decision_hits >= 5:
        decision_type = "즉결형"
    elif question_hits >= 4:
        decision_type = "합의형"
    else:
        decision_type = "숙고형"

    if emotional_score >= 7:
        emotional_level = "표현적"
    elif emotional_score <= 4:
        emotional_level = "억제적"
    else:
        emotional_level = "중립"

    if jargon_score >= 7:
        vocab_style = "전문용어다수"
    elif jargon_score <= 4:
        vocab_style = "일상어중심"
    else:
        vocab_style = "혼용"

    if formality_score >= 8:
        persona_type = "격식을 중시하고 디테일 확인을 선호하는 실무형 담당자"
        tone_primary = "professional"
        avoid_tone = "casual"
    elif formality_score >= 6:
        persona_type = "정중하지만 지나치게 딱딱하지 않은 균형형 담당자"
        tone_primary = "warm"
        avoid_tone = "flippant"
    else:
        persona_type = "친근한 대화를 선호하지만 핵심 정리는 챙기는 소통형 담당자"
        tone_primary = "friendly"
        avoid_tone = "overly_formal"

    key_characteristics = [
        "일정과 세부 내용을 빠뜨리지 않길 원함" if detail_score >= 6 else "핵심만 빠르게 파악하길 원함",
        "답변 속도에 민감한 편" if urgency_score >= 6 else "답변 속도는 비교적 유연한 편",
        "말투의 톤 차이에 민감함" if formality_score >= 6 else "톤은 부드럽고 친근한 편을 선호함",
        "수정 요청 시 구체적인 반영을 기대함" if feedback_type == "상세" else "수정 요청은 핵심만 간단히 전달하는 편",
        f"{organization} 톤에 맞는 안정감 있는 커뮤니케이션을 선호함",
    ]

    favorite_expressions = _pick_examples(lines, ["감사", "부탁", "확인", "안녕하세요", "좋습니다"], 3)
    if not favorite_expressions:
        favorite_expressions = ["핵심 정보가 한눈에 들어오게 정리해 주세요."]

    dont_expressions = []
    if re.search(r"이모지|이모티콘", joined, re.IGNORECASE):
        dont_expressions.append("과도한 이모지 사용")
    if formality_score >= 7:
        dont_expressions.append("너무 가벼운 반말 톤")
    if detail_score >= 7:
        dont_expressions.append("핵심 일정이나 수치 누락")
    if not dont_expressions:
        dont_expressions.append("근거 없는 과장 표현")

    return {
        "overall_summary": {
            "persona_type": persona_type,
            "key_characteristics": key_characteristics,
            "content_creation_difficulty": _clamp((detail_score + urgency_score + perfectionism_score) / 3),
            "primary_caution": "핵심 수치·일정·문의 정보를 누락하지 않고, 조직 톤에 맞게 정리해야 합니다.",
        },
        "formality_analysis": {
            "overall_score": formality_score,
            "formal_language_usage": {
                "score": formality_score,
                "examples": _pick_examples(lines, ["안녕하세요", "드립니다", "감사", "부탁"], 3),
            },
            "honorifics_level": {
                "score": formality_score,
                "preferred_endings": ["~습니다", "~해주세요"] if formality_score >= 7 else ["~해요", "~해주세요"],
                "avoided_expressions": ["과한 반말", "지나친 농담"],
            },
            "business_formality": {
                "score": _clamp((formality_score + detail_score) / 2),
                "description": "업무 커뮤니케이션에서는 정리된 톤과 정확한 전달을 우선합니다.",
            },
        },
        "communication_style": {
            "directness": {
                "score": directness_score,
                "style": directness_style,
                "evidence": _pick_examples(lines, ["부탁", "진행", "확인", "가능"], 3),
            },
            "response_speed_expectation": {
                "score": urgency_score,
                "pattern": response_pattern,
            },
            "feedback_style": {
                "score": detail_score,
                "type": feedback_type,
                "evidence": _pick_examples(lines, ["수정", "정리", "확인", "일정"], 3),
            },
            "decision_making": {
                "score": _clamp((decision_hits * 0.4) + 4),
                "type": decision_type,
                "evidence": _pick_examples(lines, ["진행", "확정", "결정", "부탁"], 3),
            },
            "emotional_expression": {
                "score": emotional_score,
                "level": emotional_level,
                "emoji_usage": _clamp(1 + emoji_hits * 0.5),
                "common_expressions": _pick_examples(lines, ["감사", "좋", "부탁", "확인"], 3),
            },
        },
        "writing_dna": {
            "sentence_structure": {
                "avg_length": sentence_style,
                "complexity_score": _clamp(4 + avg_length / 18),
                "preferred_patterns": ["핵심 먼저 제시 후 상세 설명", "일정/대상/혜택 순 정리"],
            },
            "vocabulary_level": {
                "score": jargon_score,
                "style": vocab_style,
                "industry_jargon_frequency": jargon_score,
            },
            "punctuation_habits": {
                "exclamation_frequency": _clamp(1 + exclamation_hits * 0.5),
                "question_frequency": _clamp(1 + question_hits * 0.5),
                "ellipsis_usage": _clamp(1 + joined.count("...") * 0.7),
                "special_patterns": ["짧은 확인 문장 선호", "핵심 문장 위주 전달"],
            },
            "paragraph_style": {
                "brevity_score": _clamp(8 - avg_length / 10),
                "list_preference": _clamp(4 + detail_score * 0.4),
                "structure_preference": "나열형" if detail_score >= 6 else "혼합형",
            },
        },
        "personality_metrics": {
            "perfectionism": {
                "score": perfectionism_score,
                "triggers": ["일정 누락", "표현 톤 불일치", "세부 정보 부족"],
                "evidence": _pick_examples(lines, ["확인", "수정", "정리"], 3),
            },
            "detail_orientation": {
                "score": detail_score,
                "focus_areas": ["일정", "세부 내용", "문의 정보"],
                "evidence": _pick_examples(lines, ["일정", "세부", "내용", "파일"], 3),
            },
            "urgency_sensitivity": {
                "score": urgency_score,
                "patterns": ["빠른 확인 요청", "마감/기한 언급 빈도"],
            },
            "flexibility": {
                "score": flexibility_score,
                "description": "필요 시 수정은 수용하지만 핵심 정보의 정확성은 놓치지 않길 원합니다.",
            },
            "risk_tolerance": {
                "score": _clamp(6 - formality_score * 0.2),
                "preference": "안전선호" if formality_score >= 6 else "중립",
            },
            "autonomy_preference": {
                "score": _clamp(5 + decision_hits * 0.15 - detail_hits * 0.1),
                "description": "초안은 맡기되 중요한 표현과 정보는 보고받길 기대합니다.",
            },
        },
        "content_preferences": {
            "tone_preference": {
                "primary": tone_primary,
                "secondary": "authoritative" if category == "government" else "friendly",
                "avoid": avoid_tone,
            },
            "length_preference": {
                "ideal": "moderate" if detail_score >= 5 else "concise",
                "tolerance_for_long": _clamp(4 + detail_score * 0.4),
            },
            "visual_preference": {
                "image_importance": image_importance,
                "infographic_preference": _clamp(3 + image_importance * 0.4),
                "style_keywords": ["정돈된 정보형", "가독성 높은 구성", "핵심 강조"],
            },
            "structure_preference": {
                "bullet_points": _clamp(4 + detail_score * 0.3),
                "numbered_lists": _clamp(4 + detail_score * 0.25),
                "headers_importance": _clamp(5 + detail_score * 0.3),
                "whitespace_preference": _clamp(4 + (10 - avg_length / 10)),
            },
        },
        "sensitive_areas": {
            "absolute_dont": {
                "expressions": dont_expressions,
                "topics": ["근거 없는 과장", "확정되지 않은 내용의 단정"],
                "styles": ["지나치게 가벼운 SNS 말투", "핵심 정보 없는 감성 위주 글"],
            },
            "careful_handling": {
                "topics": ["민감한 일정", "지원 조건", "기관 신뢰와 연결되는 표현"],
                "reasons": ["실무 정확성과 기관 신뢰도에 직접 영향을 줄 수 있음"],
            },
            "past_issues": ["톤이 너무 가볍거나 핵심 정보가 빠진 초안은 만족도가 낮을 수 있음"],
        },
        "positive_triggers": {
            "favorite_expressions": favorite_expressions,
            "appreciated_approaches": [
                "핵심 일정과 혜택을 먼저 요약해주는 방식",
                "읽는 사람이 바로 행동할 수 있게 안내하는 방식",
                "기관 톤을 해치지 않으면서 부드럽게 풀어주는 방식",
            ],
            "success_patterns": ["한눈에 보이는 구조", "정확한 수치/일정 반영", "과하지 않은 친근함"],
            "value_keywords": ["정확성", "신뢰", "정리력", "가독성"],
        },
        "practical_guidelines": {
            "opening_recommendations": [
                "이번 소식에서 독자가 가장 먼저 알아야 할 핵심을 첫 문단에 배치하기",
                "독자의 상황을 짚는 짧은 공감 문장으로 시작하기",
            ],
            "closing_recommendations": [
                "신청/문의 방법을 다시 한 번 또렷하게 정리하기",
                "놓치기 쉬운 일정이나 준비사항을 마지막에 상기시키기",
            ],
            "reporting_format": "핵심 요약 + 일정/대상/혜택 정리형",
            "revision_handling": "수정 요청 시 변경 전후가 드러나게 반영",
            "timeline_sensitivity": urgency_score,
        },
        "brand_alignment": {
            "organization_voice_match": _clamp((formality_score + detail_score) / 2),
            "industry_conventions": ["공신력 있는 표현 유지", "일정/대상/혜택의 명확한 분리"],
            "target_audience_consideration": "처음 접하는 독자도 바로 이해할 수 있게 맥락을 붙여 설명해야 합니다.",
        },
    }


def _build_tags(material_bundle: dict[str, Any], keywords: list[str] | None, target_audience: str) -> list[str]:
    tags = []
    for item in keywords or []:
        clean = str(item).strip().lstrip("#")
        if clean and clean not in tags:
            tags.append(clean)
    for item in material_bundle.get("tag_candidates", []):
        if item not in tags:
            tags.append(item)
        if len(tags) >= 4:
            break
    audience_tag = target_audience.replace("/", " ").split()[0]
    if audience_tag and audience_tag not in tags:
        tags.append(audience_tag)
    return tags[:5]


def _select_facts(material_bundle: dict[str, Any]) -> list[str]:
    facts = material_bundle.get("fact_lines", [])[:6]
    if not facts and material_bundle.get("combined_text"):
        sentences = re.split(r"(?<=[.!?다요])\s+", material_bundle["combined_text"])
        facts = [sentence.strip() for sentence in sentences if len(sentence.strip()) >= 18][:6]
    return facts


def _build_title(base_topic: str, target_audience: str, style: str, keywords: list[str]) -> str:
    keyword = keywords[0] if keywords else ""
    audience_suffix = f"{target_audience}을 위한 " if target_audience and target_audience != "일반 시민" else ""
    if base_topic == "recruitment":
        templates = {
            "formal": f"{audience_suffix}{keyword or '모집'} 소식, 꼭 확인해야 할 핵심 안내",
            "balanced": f"{audience_suffix}{keyword or '모집'} 정보를 한눈에 정리해봤어요",
            "casual": f"{audience_suffix}{keyword or '모집'} 소식, 지금 챙겨보면 좋아요",
        }
    elif base_topic == "partnership":
        templates = {
            "formal": f"{keyword or '업무협약'} 체결 소식과 기대 효과 정리",
            "balanced": f"{keyword or '협력 소식'}이 가져올 변화를 쉽게 풀어봤어요",
            "casual": f"{keyword or '협력 소식'}이 왜 반가운지 같이 볼까요",
        }
    else:
        templates = {
            "formal": f"{keyword or '이번 소식'} 핵심 내용과 참여 포인트 안내",
            "balanced": f"{keyword or '이번 소식'}을 이해하기 쉽게 정리했어요",
            "casual": f"{keyword or '이번 소식'}, 놓치면 아쉬운 포인트만 모았어요",
        }
    return templates.get(style, templates["balanced"]).strip()


def _join_paragraphs(paragraphs: list[str]) -> str:
    return "\n\n".join(paragraph.strip() for paragraph in paragraphs if paragraph.strip())


def _render_blog_version(
    style: str,
    persona_data: dict[str, Any],
    material_bundle: dict[str, Any],
    keywords: list[str] | None,
    target_audience: str,
    content_angle: str,
) -> dict[str, Any]:
    facts = _select_facts(material_bundle)
    contacts = material_bundle.get("contact_lines", [])[:3]
    dates = material_bundle.get("date_lines", [])[:3]
    tags = _build_tags(material_bundle, keywords, target_audience)
    topic = material_bundle.get("topic", "announcement")

    style_map = {
        "formal": {
            "label": "포멀",
            "opening": "이번 자료를 살펴보면 독자가 가장 먼저 챙겨야 할 핵심이 또렷하게 보입니다.",
            "bridge": "무엇보다 중요한 포인트는 다음과 같습니다.",
            "closing": "관심 있는 분들은 아래 일정과 문의 정보를 꼭 확인하시기 바랍니다.",
        },
        "balanced": {
            "label": "밸런스",
            "opening": "이번 소식은 필요한 분들에게 꽤 실질적인 도움이 될 만한 내용으로 채워져 있어요.",
            "bridge": "복잡해 보일 수 있지만, 핵심만 먼저 정리하면 훨씬 이해가 쉬워집니다.",
            "closing": "끝까지 읽으셨다면 일정과 문의처를 저장해두고 바로 움직여보셔도 좋겠습니다.",
        },
        "casual": {
            "label": "캐주얼",
            "opening": "이번 내용은 그냥 지나치기보다 한 번 제대로 챙겨보면 좋겠다는 생각이 드는 소식이에요.",
            "bridge": "딱 필요한 부분만 골라서 보면 훨씬 부담이 덜합니다.",
            "closing": "필요한 분이라면 일정 놓치지 말고 바로 확인해보세요.",
        },
    }
    tone = style_map[style]

    audience_line = f"{target_audience} 입장에서 보면 특히 눈에 들어오는 지점이 분명합니다."
    angle_line = {
        "정보전달형": "핵심 정보와 일정, 대상, 혜택을 순서대로 짚어보겠습니다.",
        "스토리텔링형": "독자의 상황에 바로 연결될 만한 장면부터 떠올리며 차근차근 풀어보겠습니다.",
        "Q&A형": "궁금해할 만한 질문을 기준으로 정리해보겠습니다.",
        "체험기형": "실제로 현장을 살펴보는 듯한 흐름으로 정리해보겠습니다.",
        "체크리스트형": "바로 활용할 수 있도록 체크리스트처럼 정리해보겠습니다.",
    }.get(content_angle, "핵심 정보부터 차근차근 정리해보겠습니다.")

    fact_paragraph = " ".join(facts[:3]) if facts else "자료 전반에서 반복적으로 강조되는 메시지는 참여 조건과 일정, 그리고 실제 혜택을 분명하게 전달하는 데 있습니다."
    detail_paragraph = " ".join(facts[3:6]) if len(facts) > 3 else "세부 내용을 보면 대상과 절차, 참고해야 할 포인트가 분명히 구분되어 있어 초안에도 같은 구조를 유지하는 것이 좋습니다."
    date_paragraph = " ".join(dates) if dates else "자료에 포함된 일정과 마감 정보는 실제 행동으로 이어지게 만드는 가장 중요한 요소입니다."
    contact_paragraph = " ".join(contacts) if contacts else "마지막에는 문의처와 신청 방법을 다시 한 번 정리해 독자가 망설이지 않게 해주는 구성이 좋습니다."

    positive = persona_data.get("persona_analysis", {}).get("positive_triggers", {}).get("favorite_expressions", [])
    positive_line = positive[0] if positive else "핵심이 한눈에 보이게 정리하는 방식"

    paragraphs = [
        tone["opening"],
        audience_line,
        angle_line,
        tone["bridge"],
        fact_paragraph,
        detail_paragraph,
        f"특히 초안에서는 '{positive_line}' 같은 감각으로 중요한 내용을 앞쪽에 배치하면 전달력이 더 좋아집니다.",
        date_paragraph,
        contact_paragraph,
        tone["closing"],
    ]

    title = _build_title(topic, target_audience, style, tags)
    content = _join_paragraphs(paragraphs)
    meta_description = re.sub(r"\s+", " ", content)[:150].strip()
    return {
        "version_type": style,
        "version_label": tone["label"],
        "title": title,
        "content": content,
        "tags": tags,
        "meta_description": meta_description,
    }


def generate_blog_versions_offline(
    persona_data: dict[str, Any],
    material_bundle: dict[str, Any],
    keywords: list[str] | None = None,
    target_audience: str = "일반 시민",
    content_angle: str = "정보전달형",
) -> list[dict[str, Any]]:
    """자료 브리프 기반으로 3가지 블로그 초안 생성."""
    keywords = [str(keyword).strip() for keyword in (keywords or []) if str(keyword).strip()]
    return [
        _render_blog_version("formal", persona_data, material_bundle, keywords, target_audience, content_angle),
        _render_blog_version("balanced", persona_data, material_bundle, keywords, target_audience, content_angle),
        _render_blog_version("casual", persona_data, material_bundle, keywords, target_audience, content_angle),
    ]


def generate_single_blog_offline(
    persona_data: dict[str, Any],
    material_bundle: dict[str, Any],
    keywords: list[str] | None = None,
) -> dict[str, Any]:
    """CLI용 단일 초안 생성. 밸런스 버전을 메인으로 사용."""
    versions = generate_blog_versions_offline(
        persona_data=persona_data,
        material_bundle=material_bundle,
        keywords=keywords,
        target_audience="일반 시민",
        content_angle="정보전달형",
    )
    primary = next(version for version in versions if version["version_type"] == "balanced")
    primary["title_variants"] = [version["title"] for version in versions]
    return primary
