#!/usr/bin/env python3
"""
폴더 기반 페르소나 생성기
input/kakao/ 폴더의 txt 파일들을 읽어서 output/personas/에 저장
"""

import sys
import os
import json
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / "persona-manager" / ".env")

import anthropic

# 폴더 설정
INPUT_DIR = PROJECT_ROOT / "input" / "kakao"
OUTPUT_DIR = PROJECT_ROOT / "output" / "personas"
INPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 60)
print("폴더 기반 페르소나 생성기")
print("=" * 60)
print(f"\n입력 폴더: {INPUT_DIR}")
print(f"출력 폴더: {OUTPUT_DIR}")

# 입력 파일 확인 (README 제외)
txt_files = [f for f in INPUT_DIR.glob("*.txt") if f.name.lower() != "readme.txt"]

if not txt_files:
    print(f"\n[!] input/kakao/ 폴더에 txt 파일이 없습니다!")
    print(f"\n사용법:")
    print(f"1. {INPUT_DIR} 폴더에 카톡 대화 txt 파일 저장")
    print(f"   파일명 예시: 부산항만공사_김철수.txt")
    print(f"2. 이 스크립트 다시 실행")
    sys.exit(0)

print(f"\n발견된 파일: {len(txt_files)}개")
for i, f in enumerate(txt_files, 1):
    print(f"  {i}. {f.name}")

# API 클라이언트
api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    print("\n[ERROR] API 키가 없습니다!")
    sys.exit(1)

client = anthropic.Anthropic(api_key=api_key)

# 각 파일 처리
for txt_file in txt_files:
    print(f"\n{'='*60}")
    print(f"처리 중: {txt_file.name}")
    print("=" * 60)
    
    # 파일명에서 정보 추출 (조직_담당자.txt 형식)
    base_name = txt_file.stem
    if "_" in base_name:
        parts = base_name.split("_", 1)
        organization = parts[0]
        client_name = parts[1] if len(parts) > 1 else "담당자"
    else:
        organization = base_name
        client_name = "담당자"
    
    # 대화 로드
    with open(txt_file, 'r', encoding='utf-8') as f:
        kakao_chat = f.read()
    
    print(f"광고주: {client_name} ({organization})")
    print(f"대화 길이: {len(kakao_chat)}자")
    
    # 분석 프롬프트
    analysis_prompt = f"""
당신은 고객 페르소나 분석 전문가입니다.
아래 카카오톡 대화를 분석하여 광고주의 상세한 페르소나를 추출해주세요.

【광고주 정보】
이름: {client_name}
소속: {organization}

【카카오톡 대화】
{kakao_chat[:5000]}

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
    "content_preferences": {{
        "preferred_tone": "professional/friendly/authoritative/casual",
        "length_preference": "concise/moderate/detailed"
    }},
    "red_flags": ["절대 하지 말아야 할 것들"],
    "green_flags": ["적극 활용할 것들"]
}}
"""
    
    print("Claude API 분석 중...")
    
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
        
        persona = json.loads(response_text.strip())
        
        # 결과 출력
        print(f"\n격식도: {persona['formality_level']['score']}/10")
        print(f"톤: {persona['content_preferences']['preferred_tone']}")
        
        # 저장
        client_id = f"CLI_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        persona_data = {
            "client_id": client_id,
            "client_name": client_name,
            "organization": organization,
            "source_file": txt_file.name,
            "persona_analysis": persona,
            "created_at": datetime.now().isoformat()
        }
        
        output_file = OUTPUT_DIR / f"{base_name}_persona.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(persona_data, f, ensure_ascii=False, indent=2)
        
        print(f"[OK] 저장됨: {output_file.name}")
        
    except Exception as e:
        print(f"[ERROR] 실패: {e}")

print(f"\n{'='*60}")
print("완료!")
print(f"결과 확인: {OUTPUT_DIR}")
print("=" * 60)
