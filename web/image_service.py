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
    
    Args:
        blog_content: 블로그 본문 텍스트
        gemini_client: google.genai.Client 인스턴스
    
    Returns:
        영문 이미지 생성 프롬프트 리스트
    """
    try:
        prompt = f"""아래 한국어 블로그 글의 핵심 주제에 맞는 이미지 생성 프롬프트를 3개 만들어주세요.

규칙:
1. 블로그 내용의 핵심 장면이나 분위기를 표현하는 프롬프트
2. 고품질 블로그 삽입 이미지에 적합한 스타일
3. 영문으로 작성, 각 프롬프트는 1~2문장
4. "professional photography", "high quality", "editorial style" 등 품질 키워드 포함
5. 사람 얼굴이 포함되지 않는 이미지로 생성 (풍경, 사물, 추상 등)

블로그 본문 (처음 1500자):
{blog_content[:1500]}

출력 형식 (JSON 배열만 출력, 다른 텍스트 없이):
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


def generate_images_for_blog(blog_content: str, gemini_client, output_dir: Path = None) -> list:
    """
    블로그 본문에 맞는 이미지를 AI로 직접 생성하는 메인 함수.
    
    전체 파이프라인:
    1. Gemini로 본문에서 이미지 프롬프트 추출
    2. Imagen API로 이미지 생성
    3. 결과 반환
    
    Args:
        blog_content: 블로그 본문 텍스트
        gemini_client: google.genai.Client 인스턴스
        output_dir: 이미지 저장 디렉토리
    
    Returns:
        이미지 정보 리스트 (실패 시 빈 리스트)
    """
    if not is_available():
        return []
    
    if not blog_content or not blog_content.strip():
        return []
    
    try:
        # Step 1: 프롬프트 추출
        prompts = extract_image_prompts(blog_content, gemini_client)
        
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
