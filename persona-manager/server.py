#!/usr/bin/env python3
"""
persona-manager MCP Server
광고주 텍스트 페르소나 관리
"""

from mcp.server.fastmcp import FastMCP
from google import genai
import os
import json
import re
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv


def extract_json_from_response(text: str) -> dict:
    """AI 응답에서 JSON 추출 및 파싱"""
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        text = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', text)
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
        return json.loads(text)

# .env 파일 로드
load_dotenv()

# MCP 서버 초기화
mcp = FastMCP("persona-manager")

# 데이터 저장 경로
DATA_DIR = Path.home() / "mcp-data" / "personas"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Gemini API 설정
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    client = genai.Client(api_key=api_key)
else:
    print("⚠️ GEMINI_API_KEY가 설정되지 않았습니다.")
    client = None


@mcp.tool()
def onboard_new_client(
    client_name: str,
    organization: str,
    kakao_chat_log: str,
    category: str = "general"
) -> dict:
    """
    신규 광고주 온보딩 - 카톡으로 페르소나 자동 생성
    
    Args:
        client_name: 광고주 담당자 이름 (예: "김철수 주무관")
        organization: 소속 기관 (예: "부산항만공사")
        kakao_chat_log: 카톡 대화 전체 복사 붙여넣기
        category: 업종 (government/fitness/cosmetics/general)
    
    Returns:
        생성된 페르소나 정보
    """
    
    print(f"\n🔍 {client_name}님의 페르소나 분석 중...")
    
    # Claude로 페르소나 분석
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
        if not client:
            raise ValueError("Gemini API가 구성되지 않았습니다.")
            
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=analysis_prompt
        )
        persona_analysis = extract_json_from_response(response.text)
        
    except Exception as e:
        print(f"❌ 페르소나 분석 실패: {e}")
        persona_analysis = {
            "formality_level": {"score": 7, "description": "정중한 스타일"},
            "writing_characteristics": {
                "sentence_length": "medium",
                "honorifics_usage": "moderate",
                "emoji_usage": "none"
            },
            "red_flags": ["분석 실패로 기본값 사용"],
            "green_flags": []
        }
    
    custom_prompt = generate_custom_prompt(persona_analysis, client_name)
    
    client_id = f"CLI_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
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
    
    print(f"✅ 페르소나 생성 완료: {client_id}")
    print(f"💾 저장 위치: {save_path}")
    
    return {
        "client_id": client_id,
        "client_name": client_name,
        "organization": organization,
        "formality_score": persona_analysis["formality_level"]["score"],
        "custom_prompt": custom_prompt,
        "save_path": str(save_path)
    }


def generate_custom_prompt(persona: dict, client_name: str) -> str:
    """페르소나 기반 맞춤 프롬프트 생성"""
    
    formality = persona["formality_level"]["score"]
    
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
    
    prompt = f"""
【{client_name} 맞춤 글쓰기 가이드】

🎯 기본 톤앤매너
- {tone} 스타일로 작성
- 종결어미: {endings}
- 격식도: {formality}/10

📝 문장 구조
- 문장 길이: {persona['writing_characteristics']['sentence_length']}
- 존댓말: {persona['writing_characteristics']['honorifics_usage']}
- 이모지: {persona['writing_characteristics']['emoji_usage']}

✅ 반드시 사용할 표현들
{chr(10).join(f'- {flag}' for flag in persona.get('green_flags', [])[:5])}

❌ 절대 피해야 할 것들
{chr(10).join(f'- {flag}' for flag in persona.get('red_flags', [])[:5])}

🎨 콘텐츠 선호도
- 선호 톤: {persona['content_preferences']['preferred_tone']}
- 길이: {persona['content_preferences']['length_preference']}
"""
    
    return prompt


@mcp.tool()
def list_all_clients() -> dict:
    """저장된 모든 광고주 목록"""
    
    clients = []
    for file_path in DATA_DIR.glob("CLI_*.json"):
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            clients.append({
                "client_id": data["client_id"],
                "client_name": data["client_name"],
                "organization": data["organization"],
                "formality_score": data["persona_analysis"]["formality_level"]["score"],
                "created_at": data["created_at"]
            })
    
    return {
        "total": len(clients),
        "clients": clients
    }


@mcp.tool()
def get_client_persona(client_id: str) -> dict:
    """특정 광고주 페르소나 조회"""
    
    file_path = DATA_DIR / f"{client_id}.json"
    
    if not file_path.exists():
        return {"error": f"Client {client_id} not found"}
    
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


if __name__ == "__main__":
    mcp.run()