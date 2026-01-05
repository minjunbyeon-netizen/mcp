#!/usr/bin/env python3
"""
페르소나 기반 블로그 글 생성기
사용법: python run_blog_generator.py
"""

import sys
import os
import json
from datetime import datetime
from pathlib import Path

# mcp_config.json에서 API 키 로드
from dotenv import load_dotenv
load_dotenv()

config_path = Path(__file__).parent / "mcp_config.json"
if config_path.exists() and not os.getenv("ANTHROPIC_API_KEY"):
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
        api_key = config.get("mcpServers", {}).get("content-automation", {}).get("env", {}).get("ANTHROPIC_API_KEY")
        if api_key:
            os.environ["ANTHROPIC_API_KEY"] = api_key

import anthropic

# 경로 설정
PERSONA_DIR = Path.home() / "mcp-data" / "personas"
OUTPUT_DIR = Path.home() / "mcp-data" / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 입력 폴더 (보도자료 텍스트 파일 넣는 곳)
INPUT_DIR = Path(__file__).parent / "input" / "press_release"
INPUT_DIR.mkdir(parents=True, exist_ok=True)


def list_personas():
    """저장된 페르소나 목록"""
    personas = []
    for file_path in PERSONA_DIR.glob("CLI_*.json"):
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            personas.append({
                "client_id": data["client_id"],
                "client_name": data["client_name"],
                "organization": data["organization"],
                "formality": data["persona_analysis"]["formality_level"]["score"]
            })
    return personas


def generate_blog_post(client_id: str, press_release: str, target_keywords: list = None):
    """블로그 글 생성"""
    
    print(f"\n📝 블로그 글 생성 중...")
    
    # 페르소나 로드
    persona_path = PERSONA_DIR / f"{client_id}.json"
    if not persona_path.exists():
        print(f"❌ 페르소나를 찾을 수 없습니다: {client_id}")
        return None
    
    with open(persona_path, 'r', encoding='utf-8') as f:
        persona_data = json.load(f)
    
    custom_prompt = persona_data["custom_prompt"]
    client_name = persona_data["client_name"]
    
    print(f"👤 페르소나: {client_name}")
    print(f"📄 보도자료 길이: {len(press_release)} 글자")
    print("-" * 50)
    
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    
    # 블로그 글 생성 프롬프트 (부산시 블로그 스타일)
    keywords_str = ", ".join(target_keywords) if target_keywords else ""
    
    blog_prompt = f"""
{{
  "system_settings": {{
    "role": "부산시 공식 블로그 콘텐츠 에디터 (페르소나 일치율 100% 목표)",
    "objective": "딱딱한 보도자료를 '부산시 블로그 고유의 친근하고 상냥한 스타일'로 완벽하게 변환",
    "persona_enforcement_level": "CRITICAL (이 가이드를 따르지 않을 경우 오답으로 간주함)"
  }},
  "input_context": {{
    "press_release": "{press_release}",
    "target_keywords": ["{keywords_str}"],
    "custom_request": "{custom_prompt}"
  }},
  "strict_persona_guide": {{
    "tone_and_manner": {{
      "primary_emotion": "친절함, 따뜻함, 자부심, 긍정적 에너지",
      "sentence_ending_rule": "해요체(~인데요, ~인데요!) 70% + 합쇼체(~습니다) 30% 비율 유지. (절대 딱딱한 '한다'체 금지)",
      "mandatory_punctuation": [
        "문장 끝을 부드럽게 맺는 물결표(~) 필수 사용 (예: 아실 텐데요~, 예정인데요~)",
        "감정을 싣는 느낌표(!) 사용",
        "서론과 결론에 친근한 이모티콘 ( :), 😀 ) 배치"
      ],
      "banned_styles": [
        "기계적인 번역투",
        "지나치게 건조한 개조식 나열",
        "어렵고 권위적인 행정 용어 그대로 사용 (반드시 쉬운 말로 풀어서 쓸 것)"
      ],
      "banned_characters": [
        "스마트 따옴표 금지: " " ' ' 대신 일반 따옴표 사용",
        "말줄임표 금지: ... 또는 … 사용 금지",
        "불필요한 생략 표현 금지"
      ]
    }},
    "visual_formatting_rules": {{
      "header_style": "소제목은 반드시 「 꺽쇠 괄호 」 안에 키워드로 작성 (예: 「 15분 도시 」)",
      "emphasis_style": "핵심 혜택, 숫자, 목표 시기는 반드시 **굵게(Bold)** 처리",
      "layout_style": "가독성을 위해 3~4줄마다 줄바꿈(Enter) 필수, 섹션 간 구분선(• • • • •) 사용",
      "image_placeholder": "각 섹션(소제목) 아래에 [이미지] 자리 표시 삽입 (예: [이미지: 한중 MOU 체결 현장])"
    }}
  }},
  "content_structure_blueprint": {{
    "intro": {{
      "hook_question": "독자에게 말을 거는 질문형 시작 (예: '~~ 소식, 알고 계시나요?')",
      "bridge": "모르는 분들을 위해 핵심만 정리했다는 친절한 안내 멘트"
    }},
    "body": {{
      "flow": "소제목(키워드) -> 현황 설명(친근하게) -> **핵심 내용/혜택 강조** -> 향후 계획",
      "narrative": "보도자료의 팩트를 전달하되, '시민의 입장에서 이게 왜 좋은지'를 설명하는 화법 사용"
    }},
    "outro": {{
      "closing": "내용 요약 및 앞으로도 소식을 빠르게 전하겠다는 약속",
      "cta": "관심과 지켜봐 달라는 당부 + 이모티콘(😀)으로 마무리"
    }}
  }},
  "task_requirements": {{
    "seo_optimization": {{
      "title": "공백 포함 60자 이내, 클릭을 유도하는 매력적인 제목, 키워드 포함",
      "meta_description": "155자 이내, 검색 결과 노출용 요약",
      "keyword_integration": "제공된 키워드를 본문에 3회 이상 자연스럽게 녹여낼 것"
    }},
    "length": "공백 포함 1,500 ~ 2,000자 (내용을 풍성하게 늘려서 작성)"
  }},
  "output_schema": {{
    "description": "반드시 아래 JSON 포맷으로만 출력할 것 (Markdown 코드 블록 내부에)",
    "format": {{
      "title": "블로그 제목 String",
      "content": "HTML 태그 없이 Markdown 형식이 적용된 본문 String",
      "tags": ["태그1", "태그2", "태그3", "태그4", "태그5"],
      "meta_description": "메타 설명 String"
    }}
  }}
}}
"""
    
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=3000,
            messages=[{"role": "user", "content": blog_prompt}]
        )
        
        response_text = response.content[0].text
        
        # JSON 추출
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        
        blog_content = json.loads(response_text.strip())
        
    except Exception as e:
        print(f"❌ 블로그 생성 실패: {e}")
        return None
    
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
    
    # JSON 저장
    json_path = OUTPUT_DIR / f"{output_id}.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(blog_data, f, ensure_ascii=False, indent=2)
    
    # 마크다운 파일도 생성
    md_path = OUTPUT_DIR / f"{output_id}.md"
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(f"# {blog_content['title']}\n\n")
        f.write(f"{blog_content['content']}\n\n")
        f.write(f"**태그:** {', '.join(blog_content['tags'])}\n")
    
    return blog_data, md_path


def main():
    print("=" * 60)
    print("📝 페르소나 기반 블로그 글 생성기")
    print("=" * 60)
    
    # 페르소나 목록 표시
    personas = list_personas()
    if not personas:
        print("\n❌ 저장된 페르소나가 없습니다.")
        print("   먼저 run_persona_test.py로 페르소나를 생성해주세요.")
        return
    
    print("\n📋 사용 가능한 페르소나:")
    print("-" * 50)
    for i, p in enumerate(personas, 1):
        print(f"  {i}. [{p['client_id']}]")
        print(f"     {p['client_name']} ({p['organization']}) - 격식도: {p['formality']}/10")
    
    # 페르소나 선택
    print("\n🔢 사용할 페르소나 번호를 입력하세요:")
    try:
        choice = int(input(">>> ").strip())
        selected = personas[choice - 1]
        client_id = selected["client_id"]
    except:
        print("❌ 잘못된 선택입니다.")
        return
    
    print(f"\n✅ 선택된 페르소나: {selected['client_name']}")
    
    # 보도자료 입력 방법 선택
    print("\n📄 보도자료 입력 방법을 선택하세요:")
    print("  1. 텍스트 파일 경로 입력")
    print("  2. 직접 입력 (여러 줄, 빈 줄 2번으로 종료)")
    
    method = input("\n>>> ").strip()
    
    if method == "1":
        print("\n📂 보도자료 텍스트 파일 경로를 입력하세요:")
        print(f"   (또는 {INPUT_DIR} 폴더에 파일을 넣고 파일명만 입력)")
        file_path = input(">>> ").strip().strip('"')
        
        # 상대 경로면 INPUT_DIR 기준
        if not os.path.isabs(file_path):
            file_path = INPUT_DIR / file_path
        
        if not os.path.exists(file_path):
            print(f"❌ 파일을 찾을 수 없습니다: {file_path}")
            return
        
        with open(file_path, 'r', encoding='utf-8') as f:
            press_release = f.read()
    else:
        print("\n📝 보도자료 내용을 입력하세요 (빈 줄 2번으로 종료):")
        print("-" * 50)
        lines = []
        empty_count = 0
        while True:
            line = input()
            if line == "":
                empty_count += 1
                if empty_count >= 2:
                    break
                lines.append("")
            else:
                empty_count = 0
                lines.append(line)
        press_release = "\n".join(lines).strip()
    
    if not press_release:
        print("❌ 보도자료 내용이 비어있습니다.")
        return
    
    print(f"\n✅ 보도자료 로드 완료: {len(press_release)} 글자")
    
    # SEO 키워드 (선택)
    print("\n🔑 SEO 키워드를 입력하세요 (쉼표로 구분, 없으면 엔터):")
    keywords_input = input(">>> ").strip()
    keywords = [k.strip() for k in keywords_input.split(",")] if keywords_input else None
    
    # 블로그 생성
    result = generate_blog_post(client_id, press_release, keywords)
    
    if result:
        blog_data, md_path = result
        blog = blog_data["content"]
        
        print("\n" + "=" * 60)
        print("✅ 블로그 글 생성 완료!")
        print("=" * 60)
        
        print(f"\n📌 제목:\n{blog['title']}")
        
        print(f"\n📝 본문 (미리보기):")
        print("-" * 50)
        print(blog['content'][:500] + "..." if len(blog['content']) > 500 else blog['content'])
        
        print(f"\n🏷️ 태그: {', '.join(blog['tags'])}")
        
        print(f"\n📊 메타 설명:\n{blog['meta_description']}")
        
        print(f"\n💾 저장 위치:")
        print(f"   - JSON: {OUTPUT_DIR / f'{blog_data['output_id']}.json'}")
        print(f"   - Markdown: {md_path}")
    else:
        print("\n❌ 블로그 생성에 실패했습니다.")


if __name__ == "__main__":
    main()
