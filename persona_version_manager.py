#!/usr/bin/env python3
"""
페르소나 버전 관리 시스템
각 페르소나별로 독립적인 학습 및 업그레이드 관리
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple


PERSONA_DIR = Path(__file__).parent / "output" / "personas"
PERSONA_DIR.mkdir(parents=True, exist_ok=True)


def get_all_versions(client_id: str) -> List[Dict]:
    """특정 페르소나의 모든 버전 가져오기"""
    persona_files = list(PERSONA_DIR.glob(f"{client_id}*.json"))
    persona_files = [f for f in persona_files if not f.name.endswith("_feedback.json")]
    
    versions = []
    for file in persona_files:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                versions.append(data)
        except:
            continue
    
    # 버전 번호로 정렬
    versions.sort(key=lambda x: x.get("version", 1))
    return versions


def load_latest_persona(client_id: str) -> Optional[Dict]:
    """해당 페르소나의 최신 버전 자동 로드"""
    
    # 모든 버전 파일 찾기
    persona_files = list(PERSONA_DIR.glob(f"{client_id}*.json"))
    persona_files = [f for f in persona_files if not f.name.endswith("_feedback.json")]
    
    if not persona_files:
        return None
    
    # 버전 번호 추출 및 정렬
    versioned_files = []
    for file in persona_files:
        if "_v" in file.stem:
            try:
                version = int(file.stem.split("_v")[1])
            except:
                version = 1
        else:
            version = 1
        versioned_files.append((version, file))
    
    # 최신 버전 선택
    latest_version, latest_file = max(versioned_files, key=lambda x: x[0])
    
    with open(latest_file, 'r', encoding='utf-8') as f:
        persona_data = json.load(f)
    
    return persona_data, latest_version, latest_file


def get_feedback_history(client_id: str) -> Dict:
    """페르소나의 피드백 히스토리 로드"""
    feedback_file = PERSONA_DIR / f"{client_id}_feedback.json"
    
    if not feedback_file.exists():
        return {
            "client_id": client_id,
            "feedback_history": [],
            "learning_stats": {
                "total_blogs": 0,
                "average_rating": 0,
                "improvement_trend": 0,
                "common_issues": {}
            }
        }
    
    with open(feedback_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_feedback_history(client_id: str, feedback_data: Dict):
    """피드백 히스토리 저장"""
    feedback_file = PERSONA_DIR / f"{client_id}_feedback.json"
    
    with open(feedback_file, 'w', encoding='utf-8') as f:
        json.dump(feedback_data, f, ensure_ascii=False, indent=2)


def calculate_ratings(client_id: str, version: int) -> Dict:
    """버전별 평균 평점 계산"""
    feedback_data = get_feedback_history(client_id)
    history = feedback_data.get("feedback_history", [])
    
    # 현재 버전과 이전 버전의 평점 계산
    current_ratings = [h["rating"] for h in history if h.get("version") == version]
    prev_ratings = [h["rating"] for h in history if h.get("version") == version - 1]
    
    current_avg = sum(current_ratings) / len(current_ratings) if current_ratings else 0
    prev_avg = sum(prev_ratings) / len(prev_ratings) if prev_ratings else 0
    
    return {
        f"v{version-1}_average": round(prev_avg, 1) if prev_avg > 0 else "N/A",
        f"v{version}_average": round(current_avg, 1) if current_avg > 0 else "N/A",
        "improvement": f"{current_avg - prev_avg:+.1f}" if prev_avg > 0 and current_avg > 0 else "N/A"
    }


def create_upgraded_version(client_id: str, adjustments: Dict, feedback_reason: str) -> Dict:
    """피드백 기반으로 새 버전 생성"""
    
    # 현재 최신 버전 로드
    result = load_latest_persona(client_id)
    if not result:
        print(f"❌ 페르소나를 찾을 수 없습니다: {client_id}")
        return None
    
    current_persona, current_version, current_file = result
    new_version = current_version + 1
    
    # 새 버전 생성 (딥 카피)
    new_persona = json.loads(json.dumps(current_persona))
    new_persona["version"] = new_version
    new_persona["created_at"] = datetime.now().isoformat()
    new_persona["parent_version"] = current_version
    
    # blog_writing_config 조정
    if "blog_writing_config" not in new_persona:
        new_persona["blog_writing_config"] = generate_default_blog_config(new_persona)
    
    config = new_persona["blog_writing_config"]
    changes = []
    
    # adjustments 적용
    for path, value in adjustments.items():
        # 중첩된 경로 처리 (예: "formatting.emoji_positions")
        keys = path.split(".")
        target = config
        
        for key in keys[:-1]:
            if key not in target:
                target[key] = {}
            target = target[key]
        
        old_value = target.get(keys[-1], "N/A")
        target[keys[-1]] = value
        changes.append(f"{path}: {old_value} → {value}")
    
    new_persona["blog_writing_config"] = config
    
    # 버전 정보 업데이트
    new_persona["version_info"] = {
        "is_latest": True,
        "parent_version": current_version,
        "changes_from_parent": changes,
        "upgrade_reason": feedback_reason,
        "feedback_ratings": calculate_ratings(client_id, new_version)
    }
    
    # 이전 버전의 is_latest를 False로 변경
    if "version_info" not in current_persona:
        current_persona["version_info"] = {}
    current_persona["version_info"]["is_latest"] = False
    current_persona["version_info"]["next_version"] = new_version
    
    # 파일 저장
    if current_version == 1 and "_v" not in current_file.stem:
        # v1을 v1.json으로 리네임
        new_v1_file = PERSONA_DIR / f"{client_id}_v1.json"
        with open(new_v1_file, 'w', encoding='utf-8') as f:
            json.dump(current_persona, f, ensure_ascii=False, indent=2)
        # 원본 파일 삭제
        current_file.unlink()
    else:
        # 기존 파일 업데이트
        with open(current_file, 'w', encoding='utf-8') as f:
            json.dump(current_persona, f, ensure_ascii=False, indent=2)
    
    # 새 버전 파일 생성
    new_file = PERSONA_DIR / f"{client_id}_v{new_version}.json"
    with open(new_file, 'w', encoding='utf-8') as f:
        json.dump(new_persona, f, ensure_ascii=False, indent=2)
    
    print(f"\n🎉 {client_id} v{new_version} 생성 완료!")
    print(f"   변경사항:")
    for change in changes:
        print(f"   - {change}")
    
    return new_persona


def generate_default_blog_config(persona_data: Dict) -> Dict:
    """페르소나 분석 기반으로 기본 블로그 설정 생성"""
    
    persona_analysis = persona_data.get("persona_analysis", {})
    formality = persona_analysis.get("formality_level", {}).get("score", 5)
    writing_chars = persona_analysis.get("writing_characteristics", {})
    
    # 격식도에 따른 기본 설정
    if formality >= 8:
        config = {
            "structure": {
                "intro_style": "formal_statement",
                "body_sections": 4,
                "use_subsections": True,
                "outro_cta": "information"
            },
            "formatting": {
                "header_format": "bracket",
                "emphasis_markers": ["**bold**"],
                "use_dividers": True,
                "divider_style": "─" * 30,
                "image_placeholders": True,
                "emoji_positions": []
            },
            "tone_details": {
                "sentence_ending_examples": ["~습니다", "~입니다"],
                "prohibited_endings": ["~해", "~야", "~해요"],
                "punctuation_style": "formal",
                "emoji_examples": []
            },
                "examples_required": True,
                "statistics_format": "bold_highlight"
            },
            "humanization": {
                "narrative_flow": "structured",
                "personal_insight_ratio": 0.1,
                "human_catchphrases": [],
                "avoid_cliches": ["혁신적인", "다각도", "기대됩니다", "통해", "다양한"]
            }
        }
    elif formality >= 6:
        config = {
            "structure": {
                "intro_style": "polite_question",
                "body_sections": 3,
                "use_subsections": True,
                "outro_cta": "engagement"
            },
            "formatting": {
                "header_format": "bracket",
                "emphasis_markers": ["**bold**", "『quote』"],
                "use_dividers": True,
                "divider_style": "• • • • •",
                "image_placeholders": True,
                "emoji_positions": ["intro", "outro"]
            },
            "tone_details": {
                "sentence_ending_examples": ["~해요", "~이에요", "~네요"],
                "prohibited_endings": ["~한다", "~이다"],
                "punctuation_style": "friendly",
                "emoji_examples": ["^^", "😊", "~"]
            },
            "content_rules": {
                "min_length": 1500,
                "max_length": 2000,
                "paragraph_length": "short",
                "keyword_density": "natural",
                "technical_terms": "simplify",
                "examples_required": True,
                "statistics_format": "bold_highlight"
            },
            "humanization": {
                "narrative_flow": "flexible",
                "personal_insight_ratio": 0.3,
                "human_catchphrases": ["사실은 말이죠", "참 다행스럽게도"],
                "avoid_cliches": ["혁신적인", "다각도", "기대됩니다", "통해", "다양한"]
            }
        }
    elif formality >= 4:
        config = {
            "structure": {
                "intro_style": "casual_question",
                "body_sections": 3,
                "use_subsections": False,
                "outro_cta": "engagement"
            },
            "formatting": {
                "header_format": "markdown",
                "emphasis_markers": ["**bold**"],
                "use_dividers": False,
                "divider_style": "",
                "image_placeholders": True,
                "emoji_positions": ["intro", "body", "outro"]
            },
            "tone_details": {
                "sentence_ending_examples": ["~해요", "~거예요", "~네요"],
                "prohibited_endings": ["~습니다", "~입니다"],
                "punctuation_style": "friendly",
                "emoji_examples": ["😊", "👍", "✨", "~"]
            },
            "content_rules": {
                "min_length": 1200,
                "max_length": 1800,
                "paragraph_length": "short",
                "keyword_density": "natural",
                "technical_terms": "avoid",
                "examples_required": True,
                "statistics_format": "simple"
            },
            "humanization": {
                "narrative_flow": "storytelling",
                "personal_insight_ratio": 0.5,
                "human_catchphrases": ["그거 아세요?", "제 생각에는"],
                "avoid_cliches": ["혁신적인", "다각도", "기대됩니다", "통해", "다양한"]
            }
        }
    else:  # formality < 4
        config = {
            "structure": {
                "intro_style": "casual_statement",
                "body_sections": 2,
                "use_subsections": False,
                "outro_cta": "casual"
            },
            "formatting": {
                "header_format": "markdown",
                "emphasis_markers": ["**bold**"],
                "use_dividers": False,
                "divider_style": "",
                "image_placeholders": False,
                "emoji_positions": ["all"]
            },
            "tone_details": {
                "sentence_ending_examples": ["~해", "~야", "~거야"],
                "prohibited_endings": ["~습니다", "~입니다"],
                "punctuation_style": "casual",
                "emoji_examples": ["ㅋㅋ", "ㅎㅎ", "😄", "👌"]
            },
            "content_rules": {
                "min_length": 1000,
                "max_length": 1500,
                "paragraph_length": "short",
                "keyword_density": "minimal",
                "technical_terms": "avoid",
                "examples_required": False,
                "statistics_format": "simple"
            },
            "humanization": {
                "narrative_flow": "chatty",
                "personal_insight_ratio": 0.7,
                "human_catchphrases": ["대박", "진짜"],
                "avoid_cliches": ["혁신적인", "다각도", "기대됩니다", "통해", "다양한"]
            }
        }
    
    # SEO 설정 (공통)
    config["seo_preferences"] = {
        "title_format": "balanced",
        "title_max_length": 60,
        "meta_description_style": "summary",
        "tag_count": 5,
        "tag_style": "specific"
    }
    
    return config


def compare_versions(client_id: str):
    """페르소나의 모든 버전 비교 및 출력"""
    
    versions = get_all_versions(client_id)
    
    if not versions:
        print(f"❌ {client_id} 페르소나를 찾을 수 없습니다.")
        return
    
    client_name = versions[0].get("client_name", client_id)
    
    print(f"\n📊 {client_name} 버전 히스토리")
    print("=" * 80)
    
    for v in versions:
        version_num = v.get("version", 1)
        created = v.get("created_at", "N/A")[:10] if v.get("created_at") else "N/A"
        
        print(f"\n🔹 v{version_num} ({created})")
        
        if version_num == 1:
            print("   초기 버전 (AI 자동 생성)")
        else:
            info = v.get("version_info", {})
            print(f"   업그레이드 이유: {info.get('upgrade_reason', 'N/A')}")
            
            changes = info.get("changes_from_parent", [])
            if changes:
                print(f"   변경사항:")
                for change in changes:
                    print(f"     - {change}")
            
            ratings = info.get("feedback_ratings", {})
            if ratings:
                prev_key = f"v{version_num-1}_average"
                curr_key = f"v{version_num}_average"
                improvement = ratings.get("improvement", "N/A")
                print(f"   만족도: {ratings.get(prev_key, 'N/A')} → {ratings.get(curr_key, 'N/A')} ({improvement})")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    # 테스트
    print("페르소나 버전 관리 시스템")
    print("사용 가능한 기능:")
    print("1. load_latest_persona(client_id) - 최신 버전 로드")
    print("2. create_upgraded_version(client_id, adjustments, reason) - 새 버전 생성")
    print("3. compare_versions(client_id) - 버전 비교")
    print("4. get_feedback_history(client_id) - 피드백 히스토리 조회")
