#!/usr/bin/env python3
"""
카카오톡 텍스트 파일로 페르소나 추출 테스트
사용법: python run_persona_test.py [카톡파일경로]
"""

import sys
import os
import json
from pathlib import Path

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent / "persona-manager"))

# .env 또는 환경변수에서 API 키 로드
from dotenv import load_dotenv
load_dotenv()

# mcp_config.json에서 API 키 읽기 (백업)
config_path = Path(__file__).parent / "mcp_config.json"
if config_path.exists() and not os.getenv("ANTHROPIC_API_KEY"):
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
        api_key = config.get("mcpServers", {}).get("persona-manager", {}).get("env", {}).get("ANTHROPIC_API_KEY")
        if api_key:
            os.environ["ANTHROPIC_API_KEY"] = api_key

import anthropic
from datetime import datetime

# 데이터 저장 경로 (프로젝트 폴더)
DATA_DIR = Path(__file__).parent / "output" / "personas"
DATA_DIR.mkdir(parents=True, exist_ok=True)

def analyze_persona(client_name: str, organization: str, kakao_chat_log: str, category: str = "general"):
    """카카오톡 대화로 페르소나 분석"""
    
    print(f"\n🔍 {client_name}님의 페르소나 분석 중...")
    print(f"📁 소속: {organization}")
    print(f"📄 대화 길이: {len(kakao_chat_log)} 글자")
    print("-" * 50)
    
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    
    analysis_prompt = f"""
당신은 고객 페르소나 분석 전문가입니다.
아래 카카오톡 대화를 분석하여 광고주의 상세한 페르소나를 추출해주세요.

【광고주 정보】
이름: {client_name}
소속: {organization}
업종: {category}

【카카오톡 대화】
{kakao_chat_log[:5000]}

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
        
        # JSON 추출
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        
        persona_analysis = json.loads(response_text.strip())
        
    except Exception as e:
        print(f"❌ 페르소나 분석 실패: {e}")
        return None
    
    # 맞춤 프롬프트 생성
    formality = persona_analysis["formality_level"]["score"]
    
    if formality >= 8:
        tone = "매우 격식있고 공식적인"
        endings = "~입니다, ~습니다"
    elif formality >= 6:
        tone = "정중하되 부드러운"
        endings = "~합니다, ~해요"
    elif formality >= 4:
        tone = "친근하고 편안한"
        endings = "~해요, ~예요"
    else:
        tone = "매우 캐주얼하고 편한"
        endings = "~해, ~야"
    
    custom_prompt = f"""
【{client_name} 맞춤 글쓰기 가이드】

🎯 기본 톤앤매너
- {tone} 스타일로 작성
- 종결어미: {endings}
- 격식도: {formality}/10

📝 문장 구조
- 문장 길이: {persona_analysis['writing_characteristics']['sentence_length']}
- 존댓말: {persona_analysis['writing_characteristics']['honorifics_usage']}
- 이모지: {persona_analysis['writing_characteristics']['emoji_usage']}

✅ 반드시 사용할 표현들
{chr(10).join(f'- {flag}' for flag in persona_analysis.get('green_flags', [])[:5])}

❌ 절대 피해야 할 것들
{chr(10).join(f'- {flag}' for flag in persona_analysis.get('red_flags', [])[:5])}

🎨 콘텐츠 선호도
- 선호 톤: {persona_analysis['content_preferences']['preferred_tone']}
- 길이: {persona_analysis['content_preferences']['length_preference']}
"""
    
    # 저장 (파일명: 소속_이름)
    safe_org = organization.replace(' ', '_').replace('/', '_')
    safe_name = client_name.replace(' ', '_').replace('/', '_')
    client_id = f"{safe_org}_{safe_name}"
    
    persona_data = {
        "client_id": client_id,
        "client_name": client_name,
        "organization": organization,
        "category": category,
        "persona_analysis": persona_analysis,
        "custom_prompt": custom_prompt,
        "created_at": datetime.now().isoformat(),
        "version": 1
    }
    
    save_path = DATA_DIR / f"{client_id}.json"
    with open(save_path, 'w', encoding='utf-8') as f:
        json.dump(persona_data, f, ensure_ascii=False, indent=2)
    
    return persona_data, save_path


def main():
    print("=" * 60)
    print("🎯 카카오톡 페르소나 추출기")
    print("=" * 60)
    
    # 카톡 파일 경로 입력
    if len(sys.argv) > 1:
        kakao_file = sys.argv[1]
    else:
        print("\n📂 카카오톡 텍스트 파일 경로를 입력하세요")
        print("   (예: C:\\Users\\...\\KakaoTalk_대화.txt)")
        kakao_file = input("\n>>> ").strip().strip('"')
    
    if not os.path.exists(kakao_file):
        print(f"❌ 파일을 찾을 수 없습니다: {kakao_file}")
        return
    
    # 파일 읽기
    with open(kakao_file, 'r', encoding='utf-8') as f:
        kakao_chat = f.read()
    
    print(f"\n✅ 파일 로드 완료: {len(kakao_chat)} 글자")
    
    # 광고주 정보 입력
    print("\n📝 광고주 정보를 입력하세요:")
    client_name = input("담당자 이름 (예: 김철수 주무관): ").strip() or "테스트 담당자"
    organization = input("소속 기관 (예: 부산시청): ").strip() or "테스트 기관"
    category = input("업종 (government/fitness/cosmetics/general): ").strip() or "general"
    
    # 분석 실행
    result = analyze_persona(client_name, organization, kakao_chat, category)
    
    if result:
        persona_data, save_path = result
        
        print("\n" + "=" * 60)
        print("✅ 페르소나 분석 완료!")
        print("=" * 60)
        
        print(f"\n📊 분석 결과:")
        print(f"   - 격식도: {persona_data['persona_analysis']['formality_level']['score']}/10")
        print(f"   - 설명: {persona_data['persona_analysis']['formality_level']['description']}")
        
        print(f"\n💬 커뮤니케이션 스타일:")
        style = persona_data['persona_analysis']['communication_style']
        print(f"   - 직접성: {style['directness']}")
        print(f"   - 감정 톤: {style['emotional_tone']}")
        print(f"   - 의사결정: {style['decision_making']}")
        
        print(f"\n✍️ 글쓰기 특성:")
        writing = persona_data['persona_analysis']['writing_characteristics']
        print(f"   - 문장 길이: {writing['sentence_length']}")
        print(f"   - 존댓말: {writing['honorifics_usage']}")
        print(f"   - 이모지: {writing['emoji_usage']}")
        
        print(f"\n🎯 성격 특성:")
        traits = persona_data['persona_analysis']['personality_traits']
        print(f"   - 디테일 지향: {traits['detail_oriented']}/10")
        print(f"   - 급박함 정도: {traits['urgency_level']}/10")
        print(f"   - 완벽주의: {traits['perfectionism']}/10")
        
        print(f"\n✅ 적극 활용할 것들:")
        for flag in persona_data['persona_analysis'].get('green_flags', []):
            print(f"   • {flag}")
        
        print(f"\n❌ 피해야 할 것들:")
        for flag in persona_data['persona_analysis'].get('red_flags', []):
            print(f"   • {flag}")
        
        print(f"\n📁 맞춤 프롬프트:")
        print("-" * 40)
        print(persona_data['custom_prompt'])
        
        print(f"\n💾 저장 위치: {save_path}")
    else:
        print("❌ 분석에 실패했습니다.")


if __name__ == "__main__":
    main()
