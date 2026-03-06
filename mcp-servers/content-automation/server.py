#!/usr/bin/env python3
"""
content-automation MCP Server  
블로그 + 카드뉴스 자동 생성
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
mcp = FastMCP("content-automation")

# 데이터 경로
PERSONA_DIR = Path.home() / "mcp-data" / "personas"
VISUAL_DIR = Path.home() / "mcp-data" / "visual-personas"
OUTPUT_DIR = Path.home() / "mcp-data" / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Gemini API 설정
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    client = genai.Client(api_key=api_key)
else:
    print("⚠️ GEMINI_API_KEY가 설정되지 않았습니다.")
    client = None


@mcp.tool()
def generate_blog_post(
    client_id: str,
    press_release: str,
    target_keywords: list[str] = None
) -> dict:
    """
    블로그 글 자동 생성 (페르소나 기반)
    
    Args:
        client_id: 광고주 ID
        press_release: 보도자료 원문
        target_keywords: SEO 키워드 (선택)
    
    Returns:
        생성된 블로그 글
    """
    
    print(f"\n📝 {client_id} 블로그 글 생성 중...")
    
    # 페르소나 로드
    persona_path = PERSONA_DIR / f"{client_id}.json"
    if not persona_path.exists():
        return {"error": f"페르소나를 찾을 수 없습니다: {client_id}"}
    
    with open(persona_path, 'r', encoding='utf-8') as f:
        persona_data = json.load(f)
    
    custom_prompt = persona_data["custom_prompt"]
    client_name = persona_data["client_name"]
    
    # Claude로 블로그 글 생성
    blog_prompt = f"""
{custom_prompt}

【작업】
아래 보도자료를 네이버 블로그 글로 변환해주세요.

【보도자료】
{press_release}

【요구사항】
- 제목: 60자 이내, SEO 최적화
- 본문: 1,500-2,000자
- 위 페르소나 가이드 철저히 준수
{f'- 키워드 자연스럽게 포함: {", ".join(target_keywords)}' if target_keywords else ''}

【출력 형식】
JSON으로 반환:
{{
    "title": "블로그 제목",
    "content": "본문 내용",
    "tags": ["태그1", "태그2", "태그3", "태그4", "태그5"],
    "meta_description": "155자 이내 설명"
}}
"""
    
    try:
        if not client:
            raise ValueError("Gemini API가 구성되지 않았습니다.")
            
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=blog_prompt
        )
        blog_content = extract_json_from_response(response.text)

    except Exception as e:
        print(f"❌ 블로그 생성 실패: {e}")
        return {"error": str(e)}
    
    # 저장
    output_id = f"BLOG_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    blog_data = {
        "output_id": output_id,
        "client_id": client_id,
        "client_name": client_name,
        "type": "blog",
        "content": blog_content,
        "created_at": datetime.now().isoformat()
    }
    
    save_path = OUTPUT_DIR / f"{output_id}.json"
    with open(save_path, 'w', encoding='utf-8') as f:
        json.dump(blog_data, f, ensure_ascii=False, indent=2)
    
    # 마크다운 파일도 생성
    md_path = OUTPUT_DIR / f"{output_id}.md"
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(f"# {blog_content['title']}\n\n")
        f.write(f"{blog_content['content']}\n\n")
        f.write(f"**태그:** {', '.join(blog_content['tags'])}\n")
    
    print(f"✅ 블로그 생성 완료")
    print(f"💾 저장: {md_path}")
    
    return {
        "output_id": output_id,
        "client_name": client_name,
        "blog": blog_content,
        "markdown_path": str(md_path)
    }


@mcp.tool()
def generate_cardnews_script(
    client_id: str,
    press_release: str,
    slide_count: int = 6
) -> dict:
    """
    카드뉴스 스크립트 생성 (텍스트만)
    
    Args:
        client_id: 광고주 ID
        press_release: 보도자료
        slide_count: 슬라이드 개수
    
    Returns:
        슬라이드별 텍스트 스크립트
    """
    
    print(f"\n🎨 {client_id} 카드뉴스 스크립트 생성 중...")
    
    # 페르소나 로드
    persona_path = PERSONA_DIR / f"{client_id}.json"
    visual_path = VISUAL_DIR / f"{client_id}_visual.json"
    
    if not persona_path.exists():
        return {"error": f"페르소나를 찾을 수 없습니다: {client_id}"}
    
    with open(persona_path, 'r', encoding='utf-8') as f:
        persona_data = json.load(f)
    
    # 시각 페르소나 있으면 로드
    visual_info = ""
    if visual_path.exists():
        with open(visual_path, 'r', encoding='utf-8') as f:
            visual_data = json.load(f)
            visual_info = f"\n시각 스타일: {visual_data['visual_dna'].get('mood', 'professional')}"
    
    custom_prompt = persona_data["custom_prompt"]
    
    # Claude로 카드뉴스 스크립트 생성
    script_prompt = f"""
{custom_prompt}{visual_info}

【작업】
아래 보도자료를 Instagram 카드뉴스 {slide_count}장으로 변환해주세요.

【보도자료】
{press_release}

【요구사항】
- 슬라이드 {slide_count}장 구성
- 각 슬라이드: 10-30자 내외 (간결하게)
- 1번: 커버 (제목 + 후킹)
- 마지막: CTA (행동 유도 + 연락처)
- 페르소나 톤앤매너 준수

【출력 형식】
JSON으로:
{{
    "slides": [
        {{
            "slide_number": 1,
            "type": "cover",
            "main_text": "메인 제목",
            "sub_text": "부제목"
        }},
        ...
    ]
}}
"""
    
    try:
        if not client:
            raise ValueError("Gemini API가 구성되지 않았습니다.")
            
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=script_prompt
        )
        script = extract_json_from_response(response.text)

    except Exception as e:
        print(f"❌ 스크립트 생성 실패: {e}")
        return {"error": str(e)}
    
    # 저장
    output_id = f"CARDNEWS_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    script_data = {
        "output_id": output_id,
        "client_id": client_id,
        "client_name": persona_data["client_name"],
        "type": "cardnews_script",
        "script": script,
        "created_at": datetime.now().isoformat()
    }
    
    save_path = OUTPUT_DIR / f"{output_id}.json"
    with open(save_path, 'w', encoding='utf-8') as f:
        json.dump(script_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 카드뉴스 스크립트 생성 완료")
    print(f"💾 저장: {save_path}")
    
    return script_data


@mcp.tool()
def list_outputs() -> dict:
    """생성된 모든 콘텐츠 목록"""
    
    outputs = []
    for file_path in OUTPUT_DIR.glob("*.json"):
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            outputs.append({
                "output_id": data["output_id"],
                "client_name": data["client_name"],
                "type": data["type"],
                "created_at": data["created_at"]
            })
    
    return {
        "total": len(outputs),
        "outputs": sorted(outputs, key=lambda x: x["created_at"], reverse=True)
    }


if __name__ == "__main__":
    mcp.run()