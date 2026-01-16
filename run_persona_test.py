#!/usr/bin/env python3
"""
카카오톡 텍스트 파일로 페르소나 추출 테스트
사용법: python run_persona_test.py [카톡파일경로]
"""

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

import google.generativeai as genai
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
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.0-flash')
    spinner.stop("API 연결 완료")
    
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
다음 JSON 형식으로 분석해주세요 (다른 텍스트 없이 오직 JSON만 출력):

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
    
    # Step 2: AI 분석 요청
    print("\n[2/3] 페르소나 분석 중")
    spinner = LoadingSpinner("AI가 대화 패턴을 분석하고 있습니다")
    spinner.start()
    
    try:
        response = model.generate_content(analysis_prompt)
        spinner.stop("대화 분석 완료")
        
        # Step 3: 결과 처리
        print("\n[3/3] 분석 결과 정리")
        spinner = LoadingSpinner("페르소나 프로필 생성 중")
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
    
    # 입력 폴더 자동 스캔
    input_folder = Path(__file__).parent / "input" / "1_personas"
    input_folder.mkdir(parents=True, exist_ok=True)
    
    # txt 파일 목록 가져오기 (README 제외)
    kakao_files = [f for f in input_folder.glob("*.txt") if f.name.lower() != "readme.txt"]
    
    if not kakao_files:
        print("\n❌ 카카오톡 파일이 없습니다.")
        print(f"   📂 이 폴더에 .txt 파일을 넣어주세요:")
        print(f"   {input_folder}")
        return
    
    # 파일 목록 표시
    print("\n📂 사용 가능한 카카오톡 파일:")
    print("-" * 50)
    for i, f in enumerate(kakao_files, 1):
        size_kb = f.stat().st_size / 1024
        # 파일명에서 이름 추출 시도
        name_part = f.stem.split("_")[-1] if "_" in f.stem else f.stem
        print(f"  {i}. {name_part}")
        print(f"     ({f.name}, {size_kb:.1f}KB)")
    
    # 번호로 선택
    print("\n🔢 분석할 파일 번호를 입력하세요:")
    try:
        choice = int(input(">>> ").strip())
        if choice < 1 or choice > len(kakao_files):
            print("❌ 잘못된 번호입니다.")
            return
        kakao_file = kakao_files[choice - 1]
    except ValueError:
        print("❌ 숫자를 입력해주세요.")
        return
    
    # 파일명에서 정보 자동 추출
    filename = kakao_file.stem
    name_guess = filename.split("_")[-1] if "_" in filename else "담당자"
    
    print(f"\n✅ 선택: {kakao_file.name}")
    
    # 파일 읽기
    with open(kakao_file, 'r', encoding='utf-8') as f:
        kakao_chat = f.read()
    
    print(f"📄 대화 길이: {len(kakao_chat):,} 글자")
    
    # 광고주 정보 입력 (자동 추천)
    print("\n📝 광고주 정보를 입력하세요 (엔터시 기본값):")
    print(f"   담당자 이름 [{name_guess}]: ", end="")
    client_name = input().strip() or name_guess
    
    print(f"   소속 기관 [하이브미디어]: ", end="")
    organization = input().strip() or "하이브미디어"
    
    print(f"   업종 (government/fitness/cosmetics/general) [general]: ", end="")
    category = input().strip() or "general"
    
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
