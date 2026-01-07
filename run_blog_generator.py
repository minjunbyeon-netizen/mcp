#!/usr/bin/env python3
"""
페르소나 기반 블로그 글 생성기
사용법: python run_blog_generator.py
"""

import sys
import os
import json
import io
import threading
import time
import subprocess
from datetime import datetime
from pathlib import Path

# Windows 터미널 UTF-8 출력 설정
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

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
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH


class LoadingSpinner:
    """로딩 스피너 애니메이션"""
    def __init__(self, message="처리 중"):
        self.message = message
        self.running = False
        self.thread = None
    
    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._animate)
        self.thread.start()
    
    def _animate(self):
        frames = ['|', '/', '-', '\\']
        i = 0
        while self.running:
            print(f"\r  {frames[i % 4]} {self.message}...", end="", flush=True)
            time.sleep(0.2)
            i += 1
    
    def stop(self, success_msg="완료"):
        self.running = False
        if self.thread:
            self.thread.join()
        print(f"\r  [OK] {success_msg}" + " " * 20)

# 경로 설정
PERSONA_DIR = Path(__file__).parent / "output" / "personas"
PERSONA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR = Path.home() / "mcp-data" / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Word 파일 전용 저장 위치
WORD_OUTPUT_DIR = Path(__file__).parent / "output" / "blog"
WORD_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 입력 폴더 (보도자료 텍스트 파일 넣는 곳)
INPUT_DIR = Path(__file__).parent / "input" / "press_release"
INPUT_DIR.mkdir(parents=True, exist_ok=True)


def list_personas():
    """저장된 페르소나 목록"""
    personas = []
    for file_path in PERSONA_DIR.glob("*.json"):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if "client_id" in data and "persona_analysis" in data:
                    personas.append({
                        "client_id": data["client_id"],
                        "client_name": data["client_name"],
                        "organization": data["organization"],
                        "formality": data["persona_analysis"]["formality_level"]["score"]
                    })
        except:
            pass
    return personas


def generate_blog_post(client_id: str, press_release: str, target_keywords: list = None):
    """블로그 글 생성"""
    
    print(f"\n{'='*50}")
    print(f"  AI 블로그 글 생성 시작")
    print(f"{'='*50}")
    
    # 페르소나 로드
    persona_path = PERSONA_DIR / f"{client_id}.json"
    if not persona_path.exists():
        print(f"❌ 페르소나를 찾을 수 없습니다: {client_id}")
        return None
    
    with open(persona_path, 'r', encoding='utf-8') as f:
        persona_data = json.load(f)
    
    custom_prompt = persona_data["custom_prompt"]
    client_name = persona_data["client_name"]
    
    print(f"  페르소나: {client_name}")
    print(f"  보도자료: {len(press_release):,} 글자")
    print(f"{'='*50}\n")
    
    # Step 1: API 연결
    print("[1/3] API 연결 준비")
    spinner = LoadingSpinner("Claude AI 연결 중")
    spinner.start()
    time.sleep(0.5)
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    spinner.stop("API 연결 완료")
    
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
    
    # Step 2: AI 블로그 생성
    print("\n[2/3] 블로그 글 생성 중")
    spinner = LoadingSpinner("AI가 페르소나 스타일로 글을 작성하고 있습니다")
    spinner.start()
    
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=3000,
            messages=[{"role": "user", "content": blog_prompt}]
        )
        spinner.stop("블로그 글 생성 완료")
        
        # Step 3: 결과 처리
        print("\n[3/3] 파일 저장 중")
        spinner = LoadingSpinner("Word/Markdown 파일 생성 중")
        spinner.start()
        
        response_text = response.content[0].text
        
        # JSON 추출
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        
        blog_content = json.loads(response_text.strip())
        
    except Exception as e:
        spinner.stop("오류 발생")
        print(f"\n❌ 블로그 생성 실패: {e}")
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
    
    # Word 파일 생성 (별도 위치에 페르소나명_제목_날짜 형식으로)
    # 파일명에 사용할 수 없는 문자 제거
    safe_title = blog_content['title'][:30].replace('/', '_').replace('\\', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_').strip()
    safe_client_name = client_name.replace(' ', '_')
    date_str = datetime.now().strftime('%Y%m%d')
    docx_filename = f"{safe_client_name}_{safe_title}_{date_str}.docx"
    docx_path = WORD_OUTPUT_DIR / docx_filename
    doc = Document()
    
    # 기본 스타일에 한글 폰트 설정
    style = doc.styles['Normal']
    font = style.font
    font.name = '맑은 고딕'
    font.size = Pt(11)
    
    # 제목 추가
    title = doc.add_heading(blog_content['title'], level=1)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    # 제목에도 한글 폰트 적용
    for run in title.runs:
        run.font.name = '맑은 고딕'
    
    # 본문 추가 (마크다운 파싱 간소화)
    content = blog_content['content']
    paragraphs = content.split('\n\n')
    
    for para in paragraphs:
        if para.strip():
            # 소제목 처리 (「 」)
            if para.strip().startswith('「') and para.strip().endswith('」'):
                p = doc.add_heading(para.strip()[1:-1].strip(), level=2)
                for run in p.runs:
                    run.font.name = '맑은 고딕'
            # 구분선 처리
            elif para.strip() == '• • • • •':
                p = doc.add_paragraph('─' * 30)
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for run in p.runs:
                    run.font.name = '맑은 고딕'
            # 이미지 자리 표시
            elif para.strip().startswith('[이미지'):
                p = doc.add_paragraph(para.strip())
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = p.runs[0]
                run.italic = True
                run.font.name = '맑은 고딕'
            else:
                # 일반 본문 - **굵게** 처리
                p = doc.add_paragraph()
                parts = para.split('**')
                for i, part in enumerate(parts):
                    run = p.add_run(part)
                    run.font.name = '맑은 고딕'
                    run.font.size = Pt(11)
                    if i % 2 == 1:  # 홀수 인덱스는 굵게
                        run.bold = True
    
    # 태그 추가
    doc.add_paragraph()
    tags_para = doc.add_paragraph()
    tags_run = tags_para.add_run(f"태그: {', '.join(blog_content['tags'])}")
    tags_run.italic = True
    tags_run.font.name = '맑은 고딕'
    
    # 메타 설명 추가
    meta_para = doc.add_paragraph()
    meta_run = meta_para.add_run(f"메타 설명: {blog_content['meta_description']}")
    meta_run.italic = True
    meta_run.font.name = '맑은 고딕'
    
    doc.save(str(docx_path))
    spinner.stop("파일 저장 완료")
    
    return blog_data, md_path, docx_path


def generate_blog_with_persona(client_id: str):
    """페르소나 추출 후 바로 블로그 생성 (연계 호출용)"""
    print("\n" + "=" * 60)
    print("📝 페르소나 기반 블로그 글 생성기")
    print("=" * 60)
    
    # 보도자료 폴더 스캔
    press_files = [f for f in INPUT_DIR.glob("*.txt") if f.name.lower() != "readme.txt"]
    
    if not press_files:
        print("\n❌ 보도자료 파일이 없습니다.")
        print(f"   📂 이 폴더에 .txt 파일을 넣어주세요:")
        print(f"   {INPUT_DIR}")
        return
    
    # 파일 목록 표시
    print("\n📂 사용 가능한 보도자료:")
    print("-" * 50)
    for i, f in enumerate(press_files, 1):
        size_kb = f.stat().st_size / 1024
        print(f"  {i}. {f.stem}")
        print(f"     ({f.name}, {size_kb:.1f}KB)")
    
    # 번호로 선택
    print("\n🔢 사용할 보도자료 번호를 입력하세요:")
    try:
        choice = int(input(">>> ").strip())
        if choice < 1 or choice > len(press_files):
            print("❌ 잘못된 번호입니다.")
            return
        selected_file = press_files[choice - 1]
    except ValueError:
        print("❌ 숫자를 입력해주세요.")
        return
    
    print(f"\n✅ 선택: {selected_file.name}")
    
    # 파일 읽기
    with open(selected_file, 'r', encoding='utf-8') as f:
        press_release = f.read()
    
    print(f"📄 보도자료 길이: {len(press_release):,} 글자")
    
    # SEO 키워드 (선택)
    print("\n🔑 SEO 키워드를 입력하세요 (쉼표로 구분, 없으면 엔터):")
    keywords_input = input(">>> ").strip()
    keywords = [k.strip() for k in keywords_input.split(",")] if keywords_input else None
    
    # 블로그 생성
    result = generate_blog_post(client_id, press_release, keywords)
    
    if result:
        blog_data, md_path, docx_path = result
        blog = blog_data["content"]
        
        print("\n" + "=" * 60)
        print("✅ 블로그 글 생성 완료!")
        print("=" * 60)
        
        print(f"\n📌 제목: {blog['title']}")
        print(f"🏷️ 태그: {', '.join(blog['tags'])}")
        print(f"\n💾 저장 위치:")
        print(f"   - Word: {docx_path}")
        
        # 폴더 열기 옵션
        print("\n" + "=" * 60)
        print("📂 블로그 폴더를 여시겠습니까? (Y/n): ", end="")
        open_folder = input().strip().lower()
        if open_folder != 'n':
            subprocess.run(['explorer', str(WORD_OUTPUT_DIR)])
            print("   폴더를 열었습니다.")
    else:
        print("\n❌ 블로그 생성에 실패했습니다.")


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
        print(f"  {i}. {p['client_name']}")
        print(f"     ({p['organization']}) - 격식도: {p['formality']}/10")
    
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
    
    # 보도자료 폴더 스캔
    press_files = [f for f in INPUT_DIR.glob("*.txt") if f.name.lower() != "readme.txt"]
    
    if not press_files:
        print("\n❌ 보도자료 파일이 없습니다.")
        print(f"   📂 이 폴더에 .txt 파일을 넣어주세요:")
        print(f"   {INPUT_DIR}")
        return
    
    # 파일 목록 표시
    print("\n📂 사용 가능한 보도자료:")
    print("-" * 50)
    for i, f in enumerate(press_files, 1):
        size_kb = f.stat().st_size / 1024
        print(f"  {i}. {f.stem}")
        print(f"     ({f.name}, {size_kb:.1f}KB)")
    
    # 번호로 선택
    print("\n🔢 사용할 보도자료 번호를 입력하세요:")
    try:
        choice = int(input(">>> ").strip())
        if choice < 1 or choice > len(press_files):
            print("❌ 잘못된 번호입니다.")
            return
        selected_file = press_files[choice - 1]
    except ValueError:
        print("❌ 숫자를 입력해주세요.")
        return
    
    print(f"\n✅ 선택: {selected_file.name}")
    
    # 파일 읽기
    with open(selected_file, 'r', encoding='utf-8') as f:
        press_release = f.read()
    
    print(f"📄 보도자료 길이: {len(press_release):,} 글자")
    
    # SEO 키워드 (선택)
    print("\n🔑 SEO 키워드를 입력하세요 (쉼표로 구분, 없으면 엔터):")
    keywords_input = input(">>> ").strip()
    keywords = [k.strip() for k in keywords_input.split(",")] if keywords_input else None
    
    # 블로그 생성
    result = generate_blog_post(client_id, press_release, keywords)
    
    if result:
        blog_data, md_path, docx_path = result
        blog = blog_data["content"]
        
        print("\n" + "=" * 60)
        print("✅ 블로그 글 생성 완료!")
        print("=" * 60)
        
        print(f"\n📌 제목: {blog['title']}")
        print(f"🏷️ 태그: {', '.join(blog['tags'])}")
        print(f"\n💾 저장 위치:")
        print(f"   - Word: {docx_path}")
        
        # 폴더 열기 옵션
        print("\n" + "=" * 60)
        print("📂 블로그 폴더를 여시겠습니까? (Y/n): ", end="")
        open_folder = input().strip().lower()
        if open_folder != 'n':
            subprocess.run(['explorer', str(WORD_OUTPUT_DIR)])
            print("   폴더를 열었습니다.")
    else:
        print("\n❌ 블로그 생성에 실패했습니다.")


if __name__ == "__main__":
    main()
