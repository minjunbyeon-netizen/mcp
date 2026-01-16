#!/usr/bin/env python3
"""
카카오톡 텍스트 파일 또는 PDF로 페르소나 추출
사용법: python run_persona_test.py
"""

import pdfplumber

import sys
import os
import json
import io
from pathlib import Path

# Windows 터미널 UTF-8 출력 설정
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent / "persona-manager"))

# .env 또는 환경변수에서 API 키 로드
from dotenv import load_dotenv
load_dotenv()

# mcp_config.json에서 API 키 읽기 (백업)
config_path = Path(__file__).parent / "mcp_config.json"
if config_path.exists() and not os.getenv("GEMINI_API_KEY"):
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
        api_key = config.get("mcpServers", {}).get("persona-manager", {}).get("env", {}).get("GEMINI_API_KEY")
        if api_key:
            os.environ["GEMINI_API_KEY"] = api_key

from google import genai
import threading
import time
from datetime import datetime

# 데이터 저장 경로 (프로젝트 폴더)
DATA_DIR = Path(__file__).parent / "output" / "personas"
DATA_DIR.mkdir(parents=True, exist_ok=True)

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

def analyze_persona(client_name: str, organization: str, kakao_chat_log: str, category: str = "general"):
    """카카오톡 대화로 페르소나 분석"""
    
    print(f"\n{'='*50}")
    print(f"  AI 페르소나 분석 시작")
    print(f"{'='*50}")
    print(f"  담당자: {client_name}")
    print(f"  소속: {organization}")
    print(f"  대화량: {len(kakao_chat_log):,} 글자")
    print(f"{'='*50}\n")
    
    # Step 1: API 연결
    print("[1/3] API 연결 준비")
    spinner = LoadingSpinner("Gemini AI 연결 중")
    spinner.start()
    time.sleep(0.5)  # 짧은 딜레이
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        spinner.stop("실패")
        print("❌ GEMINI_API_KEY 환경 변수가 없습니다.")
        return None
    
    client = genai.Client(api_key=api_key)
    spinner.stop("API 연결 완료")
    
    analysis_prompt = f"""
당신은 광고/마케팅 에이전시의 시니어 페르소나 분석 전문가입니다.
아래 카카오톡 대화를 철저히 분석하여 광고주의 상세한 페르소나를 추출해주세요.
모든 분석은 실제 대화 내용에서 발견된 패턴과 근거를 바탕으로 해야 합니다.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【광고주 기본 정보】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• 담당자명: {client_name}
• 소속 기관: {organization}
• 업종 분류: {category}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【분석 대상 카카오톡 대화】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{kakao_chat_log[:8000]}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【분석 지침】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. 모든 점수는 1-10 척도로 평가 (1=매우 낮음, 10=매우 높음)
2. 각 항목에는 반드시 근거(evidence)를 대화에서 발췌하여 포함
3. 콘텐츠 제작 시 실제 적용 가능한 구체적 가이드 제공
4. JSON만 출력 (다른 텍스트 없이)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【출력 JSON 스키마】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{{
    "overall_summary": {{
        "persona_type": "한 문장으로 이 광고주를 정의 (예: 꼼꼼하고 격식을 중시하는 공공기관 담당자)",
        "key_characteristics": ["특징1", "특징2", "특징3"],
        "content_creation_difficulty": 1-10,
        "primary_caution": "콘텐츠 작성 시 가장 주의할 점"
    }},
    
    "formality_analysis": {{
        "overall_score": 1-10,
        "formal_language_usage": {{
            "score": 1-10,
            "examples": ["대화에서 발췌한 예시1", "예시2"]
        }},
        "honorifics_level": {{
            "score": 1-10,
            "preferred_endings": ["~습니다", "~해요" 등 실제 사용되는 종결어미],
            "avoided_expressions": ["피하는 표현들"]
        }},
        "business_formality": {{
            "score": 1-10,
            "description": "업무적 격식 수준 설명"
        }}
    }},
    
    "communication_style": {{
        "directness": {{
            "score": 1-10,
            "style": "direct/diplomatic/indirect",
            "evidence": ["근거가 되는 대화 발췌"]
        }},
        "response_speed_expectation": {{
            "score": 1-10,
            "pattern": "즉시응답요구/여유있음/유연함"
        }},
        "feedback_style": {{
            "score": 1-10,
            "type": "상세/간결/암묵적",
            "evidence": ["근거 발췌"]
        }},
        "decision_making": {{
            "score": 1-10,
            "type": "즉결형/숙고형/합의형",
            "evidence": ["근거 발췌"]
        }},
        "emotional_expression": {{
            "score": 1-10,
            "level": "억제적/중립/표현적",
            "emoji_usage": 1-10,
            "common_expressions": ["자주 쓰는 감정 표현"]
        }}
    }},
    
    "writing_dna": {{
        "sentence_structure": {{
            "avg_length": "short/medium/long",
            "complexity_score": 1-10,
            "preferred_patterns": ["선호하는 문장 패턴"]
        }},
        "vocabulary_level": {{
            "score": 1-10,
            "style": "전문용어다수/일상어중심/혼용",
            "industry_jargon_frequency": 1-10
        }},
        "punctuation_habits": {{
            "exclamation_frequency": 1-10,
            "question_frequency": 1-10,
            "ellipsis_usage": 1-10,
            "special_patterns": ["특이한 문장부호 사용 패턴"]
        }},
        "paragraph_style": {{
            "brevity_score": 1-10,
            "list_preference": 1-10,
            "structure_preference": "나열형/서술형/혼합형"
        }}
    }},
    
    "personality_metrics": {{
        "perfectionism": {{
            "score": 1-10,
            "triggers": ["완벽주의가 발동하는 상황"],
            "evidence": ["근거 발췌"]
        }},
        "detail_orientation": {{
            "score": 1-10,
            "focus_areas": ["세부사항 중시 영역"],
            "evidence": ["근거 발췌"]
        }},
        "urgency_sensitivity": {{
            "score": 1-10,
            "patterns": ["급한 상황에서의 패턴"]
        }},
        "flexibility": {{
            "score": 1-10,
            "description": "변경사항 수용도"
        }},
        "risk_tolerance": {{
            "score": 1-10,
            "preference": "안전선호/중립/도전선호"
        }},
        "autonomy_preference": {{
            "score": 1-10,
            "description": "자율적 진행 vs 확인 요청 성향"
        }}
    }},
    
    "content_preferences": {{
        "tone_preference": {{
            "primary": "professional/friendly/authoritative/warm/neutral",
            "secondary": "보조 톤",
            "avoid": "피해야 할 톤"
        }},
        "length_preference": {{
            "ideal": "concise/moderate/detailed",
            "tolerance_for_long": 1-10
        }},
        "visual_preference": {{
            "image_importance": 1-10,
            "infographic_preference": 1-10,
            "style_keywords": ["선호 비주얼 스타일 키워드"]
        }},
        "structure_preference": {{
            "bullet_points": 1-10,
            "numbered_lists": 1-10,
            "headers_importance": 1-10,
            "whitespace_preference": 1-10
        }}
    }},
    
    "sensitive_areas": {{
        "absolute_dont": {{
            "expressions": ["절대 사용 금지 표현/단어"],
            "topics": ["피해야 할 주제"],
            "styles": ["피해야 할 스타일"]
        }},
        "careful_handling": {{
            "topics": ["조심스럽게 다룰 주제"],
            "reasons": ["주의가 필요한 이유"]
        }},
        "past_issues": ["과거 대화에서 발견된 불만/이슈 패턴"]
    }},
    
    "positive_triggers": {{
        "favorite_expressions": ["긍정 반응을 이끄는 표현"],
        "appreciated_approaches": ["좋아하는 접근 방식"],
        "success_patterns": ["성공적이었던 커뮤니케이션 패턴"],
        "value_keywords": ["중요시하는 가치/키워드"]
    }},
    
    "practical_guidelines": {{
        "opening_recommendations": ["추천 오프닝 문구 스타일"],
        "closing_recommendations": ["추천 마무리 문구 스타일"],
        "reporting_format": "선호하는 보고/공유 형식",
        "revision_handling": "수정요청 시 대응 방식",
        "timeline_sensitivity": 1-10
    }},
    
    "brand_alignment": {{
        "organization_voice_match": 1-10,
        "industry_conventions": ["업종 특성상 고려할 관행"],
        "target_audience_consideration": "타겟 청중 특성"
    }}
}}
"""
    
    # Step 2: AI 분석 요청
    print("\n[2/3] 페르소나 심층 분석 중")
    spinner = LoadingSpinner("AI가 대화 패턴을 정밀 분석하고 있습니다")
    spinner.start()
    
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=analysis_prompt
        )
        spinner.stop("심층 분석 완료")
        
        # Step 3: 결과 처리
        print("\n[3/3] 분석 결과 정리")
        spinner = LoadingSpinner("프로페셔널 페르소나 프로필 생성 중")
        spinner.start()
        
        response_text = response.text
        
        # JSON 추출
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        
        persona_analysis = json.loads(response_text.strip())
        spinner.stop("프로필 생성 완료")
        
    except Exception as e:
        spinner.stop("오류 발생")
        print(f"\n❌ 페르소나 분석 실패: {e}")
        return None
    
    # 맞춤 프롬프트 생성 (개선된 버전)
    formality = persona_analysis.get("formality_analysis", {}).get("overall_score", 5)
    
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
    
    # 점수 추출 헬퍼
    def get_score(path, default=5):
        try:
            result = persona_analysis
            for key in path.split('.'):
                result = result[key]
            return result if isinstance(result, int) else default
        except:
            return default
    
    custom_prompt = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【{client_name} 전용 콘텐츠 제작 가이드】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 페르소나 요약
{persona_analysis.get('overall_summary', {}).get('persona_type', '분석 중')}

🎯 핵심 특성
{chr(10).join(f'• {c}' for c in persona_analysis.get('overall_summary', {}).get('key_characteristics', [])[:5])}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 글쓰기 스타일
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• 톤앤매너: {tone}
• 종결어미: {endings}
• 격식도: {formality}/10
• 완벽주의: {get_score('personality_metrics.perfectionism.score')}/10
• 디테일 중시: {get_score('personality_metrics.detail_orientation.score')}/10
• 긴급성 민감도: {get_score('personality_metrics.urgency_sensitivity.score')}/10

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 반드시 적용
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{chr(10).join(f'• {item}' for item in persona_analysis.get('positive_triggers', {}).get('favorite_expressions', [])[:5])}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ 절대 금지
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{chr(10).join(f'• {item}' for item in persona_analysis.get('sensitive_areas', {}).get('absolute_dont', {}).get('expressions', [])[:5])}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 주의 사항
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• 콘텐츠 제작 난이도: {persona_analysis.get('overall_summary', {}).get('content_creation_difficulty', 5)}/10
• 핵심 주의점: {persona_analysis.get('overall_summary', {}).get('primary_caution', '')}
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
    
    # 입력 폴더 자동 스캔
    input_folder = Path(__file__).parent / "input" / "1_personas"
    input_folder.mkdir(parents=True, exist_ok=True)
    
    # txt 및 pdf 파일 목록 가져오기 (README 제외)
    persona_files = [
        f for f in input_folder.iterdir() 
        if f.suffix.lower() in ['.txt', '.pdf'] and f.name.lower() != "readme.txt"
    ]
    
    if not persona_files:
        print("\n❌ 카카오톡/PDF 파일이 없습니다.")
        print(f"   📂 이 폴더에 .txt 또는 .pdf 파일을 넣어주세요:")
        print(f"   {input_folder}")
        return
    
    # 파일 목록 표시
    print("\n📂 사용 가능한 파일:")
    print("-" * 50)
    for i, f in enumerate(persona_files, 1):
        size_kb = f.stat().st_size / 1024
        file_type = "📄 PDF" if f.suffix.lower() == '.pdf' else "💬 TXT"
        # 파일명에서 이름 추출 시도
        name_part = f.stem.split("_")[-1] if "_" in f.stem else f.stem
        print(f"  {i}. {name_part} {file_type}")
        print(f"     ({f.name}, {size_kb:.1f}KB)")
    
    # 번호로 선택
    print("\n🔢 분석할 파일 번호를 입력하세요:")
    try:
        choice = int(input(">>> ").strip())
        if choice < 1 or choice > len(persona_files):
            print("❌ 잘못된 번호입니다.")
            return
        selected_file = persona_files[choice - 1]
    except ValueError:
        print("❌ 숫자를 입력해주세요.")
        return
    
    # 파일명에서 정보 자동 추출
    filename = selected_file.stem
    name_guess = filename.split("_")[-1] if "_" in filename else "담당자"
    
    print(f"\n✅ 선택: {selected_file.name}")
    
    # 파일 읽기 (TXT 또는 PDF)
    if selected_file.suffix.lower() == '.pdf':
        print("📄 PDF 파일에서 텍스트 추출 중...")
        try:
            with pdfplumber.open(selected_file) as pdf:
                text_content = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_content += page_text + "\n"
            if not text_content.strip():
                print("❌ PDF에서 텍스트를 추출할 수 없습니다.")
                return
        except Exception as e:
            print(f"❌ PDF 읽기 실패: {e}")
            return
    else:
        with open(selected_file, 'r', encoding='utf-8') as f:
            text_content = f.read()
    
    print(f"📄 내용 길이: {len(text_content):,} 글자")
    
    # 광고주 정보 입력 (자동 추천)
    print("\n📝 광고주 정보를 입력하세요 (엔터시 기본값):")
    print(f"   담당자 이름 [{name_guess}]: ", end="")
    client_name = input().strip() or name_guess
    
    print(f"   소속 기관 [하이브미디어]: ", end="")
    organization = input().strip() or "하이브미디어"
    
    print(f"   업종 (government/fitness/cosmetics/general) [general]: ", end="")
    category = input().strip() or "general"
    
    # 분석 실행
    result = analyze_persona(client_name, organization, text_content, category)
    
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
            print(f"   - {flag}")
        
        print(f"\n❌ 피해야 할 것들:")
        for flag in persona_data['persona_analysis'].get('red_flags', []):
            print(f"   - {flag}")
        
        print(f"\n💾 저장 위치: {save_path}")
        
        # 폴더 열기 옵션
        print("\n" + "=" * 60)
        print("📂 페르소나 폴더를 여시겠습니까? (Y/n): ", end="")
        open_folder = input().strip().lower()
        if open_folder != 'n':
            import subprocess
            subprocess.run(['explorer', str(DATA_DIR)])
            print("   폴더를 열었습니다.")
        
        # 블로그 작성 옵션
        print("\n" + "=" * 60)
        print("📝 이 페르소나로 블로그 글을 작성하시겠습니까? (Y/n): ", end="")
        do_blog = input().strip().lower()
        if do_blog != 'n':
            # run_blog_generator 호출
            client_id = persona_data['client_id']
            try:
                from run_blog_generator import generate_blog_with_persona
                generate_blog_with_persona(client_id)
            except ImportError:
                print("\n블로그 생성기를 별도로 실행해주세요:")
                print(f"   python run_blog_generator.py")
    else:
        print("❌ 분석에 실패했습니다.")


if __name__ == "__main__":
    main()
