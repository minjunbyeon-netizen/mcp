#!/usr/bin/env python3
"""
Gemini Imagen 이미지 생성 서비스
블로그 본문 키워드 기반으로 Google Imagen으로 이미지를 직접 생성합니다.

안전 설계:
- Gemini API Key가 없으면 자동 비활성화
- 모든 함수는 실패 시 빈 리스트/False 반환 (에러 전파 없음)
- 별도 API Key 불필요 (기존 Gemini API Key 사용)
"""

import os
import json
import base64
from pathlib import Path
from datetime import datetime


def is_available() -> bool:
    """Gemini API Key가 설정되어 있는지 확인"""
    return bool(os.getenv("GEMINI_API_KEY", "").strip())


def extract_image_prompts(blog_content: str, gemini_client) -> list:
    """
    Gemini에게 블로그 본문에서 이미지 생성용 영문 프롬프트를 추출하도록 요청.
    이때 타겟 독자와 콘텐츠 앵글을 반영하여 최적의 비주얼 스타일을 제안합니다.
    
    Args:
        blog_content: 블로그 본문 텍스트
        gemini_client: google.genai.Client 인스턴스
        target_audience: 타겟 독자
        content_angle: 콘텐츠 앵글
    
    Returns:
        영문 이미지 생성 프롬프트 리스트
    """
def extract_image_prompts(blog_content: str, gemini_client, target_audience: str = "일반 시민", content_angle: str = "정보전달형") -> list:
    try:
        # 타겟 및 앵글에 따른 비주얼 스타일 가이드라인 정의
        style_guide = f"""
- **Target Audience ({target_audience})**: Tailor the visual mood for this group. (e.g., warm/soft for moms, high contrast/clear for seniors, trendy/vibrant for youth)
- **Content Angle ({content_angle})**: Influence the composition. (e.g., cinematic/wide for storytelling, flat lay/minimalist for information, organized/top-down for checklists)
"""

        prompt = f"""You are a professional Creative Director. Create 3 high-quality image generation prompts based on the following blog content. 
The images must be tailored to the **Target Audience: {target_audience}** and the **Content Angle: {content_angle}**.

【Visual Strategy】
{style_guide}

【Rules】
1. Describe a scene that captures the core message or mood of the blog.
2. High-quality editorial style, professional photography.
3. Write in English, 1-2 descriptive sentences per prompt.
4. Include quality keywords like "high resolution", "award-winning photography", "soft lighting", "4k".
5. **CRITICAL**: No human faces or recognizable people. Focus on objects, landscapes, abstract concepts, or environmental shots that imply human presence.

Blog Content (First 1500 chars):
{blog_content[:1500]}

Output Format (JSON array only, no other text):
["prompt1", "prompt2", "prompt3"]"""

        response = gemini_client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt
        )
        
        response_text = response.text.strip()
        
        # JSON 추출
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        
        prompts = json.loads(response_text.strip())
        
        if isinstance(prompts, list) and len(prompts) > 0:
            return prompts[:3]
        
        return []
        
    except Exception as e:
        print(f"[WARN] 이미지 프롬프트 추출 실패: {e}")
        return []


def generate_images(prompts: list, gemini_client, output_dir: Path = None) -> list:
    """
    Gemini Imagen API로 이미지 생성.
    
    Args:
        prompts: 영문 이미지 생성 프롬프트 리스트
        gemini_client: google.genai.Client 인스턴스
        output_dir: 이미지 저장 디렉토리 (없으면 저장 안 함)
    
    Returns:
        이미지 정보 딕셔너리 리스트:
        [{"data_uri": "data:image/png;base64,...", "prompt": "생성 프롬프트", "saved_path": "저장경로"}]
    """
    from google.genai import types
    
    images = []
    
    for i, img_prompt in enumerate(prompts[:3]):  # 최대 3개
        try:
            response = gemini_client.models.generate_images(
                model='imagen-4.0-fast-generate-001',
                prompt=img_prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                )
            )
            
            if not response.generated_images:
                print(f"[WARN] 이미지 생성 실패 (빈 결과): prompt={img_prompt[:50]}...")
                continue
            
            generated = response.generated_images[0]
            
            # base64 인코딩된 이미지 데이터
            img_bytes = generated.image.image_bytes
            b64_data = base64.b64encode(img_bytes).decode('utf-8')
            data_uri = f"data:image/png;base64,{b64_data}"
            
            image_info = {
                "data_uri": data_uri,
                "prompt": img_prompt,
                "index": i + 1,
                "saved_path": ""
            }
            
            # 파일로 저장 (output_dir이 있는 경우)
            if output_dir:
                output_dir = Path(output_dir)
                output_dir.mkdir(parents=True, exist_ok=True)
                
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                img_filename = f"blog_image_{timestamp}_{i+1}.png"
                img_path = output_dir / img_filename
                
                with open(img_path, 'wb') as f:
                    f.write(img_bytes)
                
                image_info["saved_path"] = str(img_path)
                print(f"[OK] 이미지 저장: {img_path}")
            
            images.append(image_info)
            print(f"[OK] 이미지 {i+1} 생성 완료: {img_prompt[:50]}...")
            
        except Exception as e:
            print(f"[WARN] 이미지 생성 실패: prompt={img_prompt[:50]}..., error={e}")
            continue
    
    return images


def generate_images_for_blog(blog_content: str, gemini_client, target_audience: str = "일반 시민", content_angle: str = "정보전달형", output_dir: Path = None) -> list:
    """
    블로그 본문에 맞는 이미지를 AI로 직접 생성하는 메인 함수.
    
    Args:
        blog_content: 블로그 본문 텍스트
        gemini_client: google.genai.Client 인스턴스
        target_audience: 타겟 독자
        content_angle: 콘텐츠 앵글
        output_dir: 이미지 저장 디렉토리
    
    Returns:
        이미지 정보 리스트 (실패 시 빈 리스트)
    """
    if not is_available():
        return []
    
    if not blog_content or not blog_content.strip():
        return []
    
    try:
        # Step 1: 프롬프트 추출 (타겟/앵글 반영)
        prompts = extract_image_prompts(blog_content, gemini_client, target_audience, content_angle)
        
        if not prompts:
            print("[WARN] 이미지 프롬프트를 추출하지 못했습니다.")
            return []
        
        print(f"[OK] 이미지 생성 프롬프트 {len(prompts)}개 추출")
        for j, p in enumerate(prompts):
            print(f"  {j+1}. {p[:80]}...")
        
        # Step 2: Imagen으로 이미지 생성
        images = generate_images(prompts, gemini_client, output_dir)
        
        print(f"[OK] 이미지 {len(images)}장 생성 완료")
        
        return images
        
    except Exception as e:
        print(f"[WARN] 이미지 생성 전체 실패 (무시됨): {e}")
        return []
