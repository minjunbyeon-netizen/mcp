#!/usr/bin/env python3
"""
visual-persona-extractor MCP Server
광고주 시각 페르소나 관리
"""

from mcp.server.fastmcp import FastMCP
from google import genai
import os
import json
import base64
from datetime import datetime
from pathlib import Path
from PIL import Image
from collections import Counter
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# MCP 서버 초기화
mcp = FastMCP("visual-persona-extractor")

# 데이터 저장 경로
DATA_DIR = Path.home() / "mcp-data" / "visual-personas"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Gemini API 설정
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    client = genai.Client(api_key=api_key)
else:
    print("⚠️ GEMINI_API_KEY가 설정되지 않았습니다.")
    client = None


@mcp.tool()
def extract_visual_persona_from_images(
    client_id: str,
    client_name: str,
    sample_image_paths: list[str],
    category: str = "general"
) -> dict:
    """
    광고주의 기존 디자인 이미지로부터 시각적 페르소나 추출
    
    Args:
        client_id: 광고주 ID (persona-manager에서 생성된 것)
        client_name: 광고주 이름
        sample_image_paths: 이미지 파일 경로 리스트 (최대 10개 권장)
        category: 업종
    
    Returns:
        시각 페르소나 정보
    """
    
    print(f"\n🎨 {client_name}님의 시각 페르소나 추출 중...")
    print(f"📁 분석할 이미지: {len(sample_image_paths)}개")
    
    # 이미지 기본 분석
    image_analysis = []
    for img_path in sample_image_paths[:10]:
        try:
            img = Image.open(img_path)
            dominant_colors = extract_dominant_colors(img, n=3)
            
            image_analysis.append({
                'path': img_path,
                'size': img.size,
                'colors': dominant_colors
            })
        except Exception as e:
            print(f"⚠️  이미지 로드 실패: {img_path} - {e}")
    
    if not image_analysis:
        return {"error": "분석 가능한 이미지가 없습니다"}
    
    # Gemini Vision으로 고급 분석 (최대 5개 이미지)
    visual_dna = analyze_images_with_gemini(
        image_paths=sample_image_paths[:5],
        client_name=client_name,
        category=category
    )
    
    # ComfyUI 파라미터 생성
    comfyui_params = generate_comfyui_params(visual_dna, image_analysis)
    
    # 저장
    visual_persona = {
        "client_id": client_id,
        "client_name": client_name,
        "category": category,
        "visual_dna": visual_dna,
        "comfyui_template": comfyui_params,
        "sample_images": sample_image_paths,
        "created_at": datetime.now().isoformat(),
        "version": 1
    }
    
    save_path = DATA_DIR / f"{client_id}_visual.json"
    with open(save_path, 'w', encoding='utf-8') as f:
        json.dump(visual_persona, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 시각 페르소나 생성 완료")
    print(f"💾 저장 위치: {save_path}")
    
    return {
        "client_id": client_id,
        "visual_dna": visual_dna,
        "comfyui_template": comfyui_params,
        "save_path": str(save_path)
    }


def extract_dominant_colors(image: Image.Image, n: int = 3) -> list:
    """이미지에서 지배적인 색상 추출"""
    
    img = image.copy()
    img.thumbnail((150, 150))
    
    pixels = list(img.getdata())
    color_counts = Counter(pixels)
    dominant = color_counts.most_common(n * 2)
    
    unique_colors = []
    for color, count in dominant:
        if len(unique_colors) >= n:
            break
        
        hex_color = '#{:02x}{:02x}{:02x}'.format(*color[:3])
        unique_colors.append({
            'hex': hex_color,
            'frequency': count / len(pixels)
        })
    
    return unique_colors


def analyze_images_with_gemini(
    image_paths: list[str],
    client_name: str,
    category: str
) -> dict:
    """Gemini Vision으로 이미지 분석"""
    
    print(f"🤖 Gemini Vision으로 {len(image_paths)}개 이미지 분석 중...")
    
    image_contents = []
    
    for img_path in image_paths:
        try:
            img = Image.open(img_path)
            # Gemini SDK는 PIL Image 객체를 직접 지원함
            image_contents.append(img)
        except Exception as e:
            print(f"⚠️ 이미지 로드 실패: {img_path} - {e}")
    
    prompt = f"""
당신은 전문 그래픽 디자이너입니다.
{client_name}의 디자인 샘플을 분석하여 시각적 DNA를 추출해주세요.

업종: {category}

다음 JSON 형식으로 분석:

{{
    "color_system": {{
        "primary_colors": ["#RRGGBB"],
        "overall_mood": "vibrant/muted/pastel/bold"
    }},
    "typography": {{
        "font_style": "sans-serif/serif/display",
        "weight": "light/regular/bold",
        "alignment": "left/center/right"
    }},
    "layout_style": {{
        "composition": "minimalist/balanced/dense",
        "white_space": "generous/moderate/minimal"
    }},
    "illustration_style": {{
        "type": "flat/gradient/3d/minimal",
        "characteristics": ["특징1", "특징2"]
    }},
    "mood": "professional/friendly/energetic/elegant"
}}
"""
    
    try:
        if not client:
            raise ValueError("Gemini API가 구성되지 않았습니다.")
            
        full_content = [prompt] + image_contents
        
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=full_content
        )
        response_text = response.text
        
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        
        visual_dna = json.loads(response_text.strip())
        
    except Exception as e:
        print(f"❌ Gemini Vision 분석 실패: {e}")
        visual_dna = {
            "color_system": {
                "primary_colors": ["#333333"],
                "overall_mood": "professional"
            },
            "layout_style": {
                "composition": "balanced"
            }
        }
    
    return visual_dna


def generate_comfyui_params(visual_dna: dict, image_analysis: list) -> dict:
    """ComfyUI 워크플로우 파라미터 생성"""
    
    colors = visual_dna.get("color_system", {})
    primary = colors.get("primary_colors", ["#333333"])[0]
    
    return {
        "colors": {
            "primary": primary,
            "mood": colors.get("overall_mood", "professional")
        },
        "typography": visual_dna.get("typography", {}),
        "layout": visual_dna.get("layout_style", {}),
        "illustration": {
            "style": visual_dna.get("illustration_style", {}).get("type", "flat"),
            "prompt_base": f"{visual_dna.get('mood', 'professional')} illustration"
        }
    }


@mcp.tool()
def get_visual_persona(client_id: str) -> dict:
    """특정 광고주 시각 페르소나 조회"""
    
    file_path = DATA_DIR / f"{client_id}_visual.json"
    
    if not file_path.exists():
        return {"error": f"Visual persona for {client_id} not found"}
    
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


if __name__ == "__main__":
    mcp.run()