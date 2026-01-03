#!/usr/bin/env python3
"""
MCP 서버 기능 테스트 - persona-manager의 onboard_new_client 테스트
"""

import sys
import os

# 프로젝트 경로 설정
PROJECT_ROOT = os.path.dirname(__file__)
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "persona-manager"))

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, "persona-manager", ".env"))

print("=" * 60)
print("MCP persona-manager 기능 테스트")
print("=" * 60)

# 샘플 카톡 대화 (실제 테스트용)
SAMPLE_KAKAO_CHAT = """
[김철수 주무관] 안녕하세요, 하이브미디어 담당자님
[나] 안녕하세요! 무엇을 도와드릴까요?
[김철수 주무관] 이번에 부산항만공사 홍보 캠페인 진행하려고 합니다
[김철수 주무관] 네이버 블로그랑 인스타그램 카드뉴스 작업이 필요해요
[나] 네, 어떤 톤앤매너를 원하시나요?
[김철수 주무관] 공공기관이다보니 너무 가벼운 건 안되고요
[김철수 주무관] 그래도 딱딱하지 않게 해주시면 좋겠습니다
[김철수 주무관] 아, 그리고 이모지는 최소화해주세요
[나] 알겠습니다!
[김철수 주무관] 감사합니다. 보도자료 보내드릴게요
"""

# 테스트 실행
from pathlib import Path
import json
import anthropic

DATA_DIR = Path.home() / "mcp-data" / "personas"
DATA_DIR.mkdir(parents=True, exist_ok=True)

api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    print("ERROR: API 키가 없습니다!")
    sys.exit(1)

client = anthropic.Anthropic(api_key=api_key)

print("\n[1] 카톡 대화 분석 중...")

# 분석 프롬프트 (server.py와 동일)
analysis_prompt = f"""
당신은 고객 페르소나 분석 전문가입니다.
아래 카카오톡 대화를 분석하여 광고주의 상세한 페르소나를 추출해주세요.

【광고주 정보】
이름: 김철수 주무관
소속: 부산항만공사
업종: government

【카카오톡 대화】
{SAMPLE_KAKAO_CHAT}

【분석 항목】
다음 JSON 형식으로 분석해주세요:

{{
    "formality_level": {{
        "score": 1-10,
        "description": "구체적 설명"
    }},
    "communication_style": {{
        "directness": "direct/indirect",
        "emotional_tone": "formal/warm/friendly/businesslike",
        "decision_making": "decisive/consultative/hesitant"
    }},
    "writing_characteristics": {{
        "sentence_length": "short/medium/long",
        "honorifics_usage": "none/moderate/heavy",
        "emoji_usage": "none/rare/moderate/frequent"
    }},
    "personality_traits": {{
        "detail_oriented": 1-10,
        "urgency_level": 1-10,
        "perfectionism": 1-10
    }},
    "content_preferences": {{
        "preferred_tone": "professional/friendly/authoritative/casual",
        "length_preference": "concise/moderate/detailed"
    }},
    "red_flags": [
        "절대 하지 말아야 할 것들"
    ],
    "green_flags": [
        "적극 활용할 것들"
    ]
}}
"""

try:
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": analysis_prompt}]
    )
    
    response_text = response.content[0].text
    
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0]
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0]
    
    persona_analysis = json.loads(response_text.strip())
    
    print("[OK] 페르소나 분석 완료!")
    print(f"\n--- 분석 결과 ---")
    print(f"격식도: {persona_analysis['formality_level']['score']}/10")
    print(f"설명: {persona_analysis['formality_level']['description']}")
    print(f"이모지 사용: {persona_analysis['writing_characteristics']['emoji_usage']}")
    print(f"레드 플래그: {persona_analysis.get('red_flags', [])}")
    print(f"그린 플래그: {persona_analysis.get('green_flags', [])}")
    
except Exception as e:
    print(f"[ERROR] 분석 실패: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("테스트 성공!")
print("=" * 60)
