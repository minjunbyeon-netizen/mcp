#!/usr/bin/env python3
"""
카카오톡 텍스트 파일 또는 PDF로 페르소나 추출
사용법: python run_persona_test.py
"""

import re

import sys
import os
import json
import io
from pathlib import Path
from datetime import datetime

# Windows 터미널 UTF-8 출력 설정
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent / "persona-manager"))

from utils import LoadingSpinner, parse_json_response, load_api_key, extract_text_from_file


# ============================================================
# [M-2] 카카오톡 청크 분할 처리
# 8000자 하드코딩 슬라이싱 제거 → 메시지 단위 청크 분할
# ============================================================

# 카카오톡 메시지 시작 패턴: "2024년 1월 1일 월요일" 또는 "홍길동 : 텍스트"
_KAKAO_MSG_PATTERN = re.compile(
    r'^(\d{4}년\s*\d{1,2}월\s*\d{1,2}일)|^(.+?)\s*:\s*',
    re.MULTILINE
)
# 날짜 구분선 패턴 (날짜 헤더)
_KAKAO_DATE_PATTERN = re.compile(
    r'^\d{4}년\s*\d{1,2}월\s*\d{1,2}일',
    re.MULTILINE
)

MAX_CHUNKS = 4          # 최대 청크 수
CHUNK_SIZE = 8000       # 청크당 최대 글자 수 (총 32,000자까지 처리 가능)


def split_kakao_into_chunks(text: str) -> list[str]:
    """
    카카오톡 텍스트를 메시지 단위로 분할하여 최대 MAX_CHUNKS개의 청크로 반환.

    분할 전략:
    1. 날짜/이름 패턴 기준으로 메시지 단위 분리
    2. 각 청크는 CHUNK_SIZE 이내
    3. 전체를 MAX_CHUNKS개로 균등 분배 (앞/중간/뒤 고르게)

    Returns:
        list[str]: 최대 MAX_CHUNKS개의 청크 리스트
    """
    if len(text) <= CHUNK_SIZE:
        # 짧으면 그대로 반환
        return [text]

    # 날짜 헤더 기준으로 단락 분리
    date_positions = [m.start() for m in _KAKAO_DATE_PATTERN.finditer(text)]

    if date_positions:
        # 날짜 헤더가 있는 경우: 날짜 단위로 분할
        segments = []
        for i, pos in enumerate(date_positions):
            end = date_positions[i + 1] if i + 1 < len(date_positions) else len(text)
            segments.append(text[pos:end])
    else:
        # 날짜 헤더가 없는 경우: 줄 단위로 분할
        lines = text.splitlines(keepends=True)
        # 약 CHUNK_SIZE 글자 단위로 묶기
        segments = []
        buf = ""
        for line in lines:
            if len(buf) + len(line) > CHUNK_SIZE and buf:
                segments.append(buf)
                buf = ""
            buf += line
        if buf:
            segments.append(buf)

    # MAX_CHUNKS개로 균등 선택 (앞/중간/뒤 고르게)
    if len(segments) <= MAX_CHUNKS:
        selected = segments
    else:
        # 균등 간격으로 인덱스 선택
        step = len(segments) / MAX_CHUNKS
        selected = [segments[int(i * step)] for i in range(MAX_CHUNKS)]

    # 청크별 CHUNK_SIZE 초과 시 앞부분만 사용
    chunks = [seg[:CHUNK_SIZE] for seg in selected if seg.strip()]

    return chunks[:MAX_CHUNKS]


def summarize_chunk(client, chunk: str, chunk_idx: int, total: int) -> str:
    """
    단일 청크를 Gemini로 요약하여 페르소나 분석용 핵심 특징 추출.

    Returns:
        str: 요약된 특징 텍스트
    """
    prompt = f"""
아래는 카카오톡 대화 텍스트의 {chunk_idx}/{total} 번째 구간입니다.
이 구간에서 담당자의 말투, 표현 습관, 커뮤니케이션 스타일, 특이 표현을 간결하게 요약해주세요.
(원문 인용 포함, 200자 이내)

---
{chunk}
---

요약:"""

    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        print(f"  구간 {chunk_idx} 분석 중 오류가 발생했습니다. 원문 일부를 사용합니다.")
        return chunk[:500]  # 실패 시 앞 500자 사용


def prepare_kakao_text(client, kakao_chat_log: str) -> str:
    """
    [M-2] 카카오톡 텍스트 전처리.

    - 8000자 이하: 그대로 반환
    - 8000자 초과: 최대 MAX_CHUNKS개 청크로 분할 → 각 청크 요약 → 합산 반환

    Returns:
        str: 페르소나 분석 프롬프트에 삽입할 텍스트
    """
    if len(kakao_chat_log) <= CHUNK_SIZE:
        return kakao_chat_log

    print(f"  카카오톡 대화가 길어 여러 부분으로 나눠 분석합니다... ({len(kakao_chat_log):,}자)")
    chunks = split_kakao_into_chunks(kakao_chat_log)
    print(f"  총 {len(chunks)}개 구간으로 나눠 분석합니다.")

    summaries = []
    for i, chunk in enumerate(chunks, 1):
        print(f"  구간 {i}/{len(chunks)} 분석 중...")
        summary = summarize_chunk(client, chunk, i, len(chunks))
        summaries.append(f"[구간 {i}/{len(chunks)}]\n{summary}")

    combined = "\n\n".join(summaries)
    print(f"  분석 준비가 완료되었습니다.")
    return combined

# API 키 로드
load_api_key("GEMINI_API_KEY")

from google import genai

# 데이터 저장 경로 (프로젝트 폴더)
DATA_DIR = Path(__file__).parent / "output" / "personas"
DATA_DIR.mkdir(parents=True, exist_ok=True)

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
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        spinner.stop("실패")
        print("❌ GEMINI_API_KEY 환경 변수가 없습니다.")
        return None
    
    client = genai.Client(api_key=api_key)
    spinner.stop("API 연결 완료")

    # [M-2] 카카오톡 청크 분할 처리 (8000자 하드코딩 슬라이싱 제거)
    prepared_text = prepare_kakao_text(client, kakao_chat_log)

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
{prepared_text}

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
        
        persona_analysis = parse_json_response(response_text)
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
        except (KeyError, TypeError):
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
    print("auto-blog 페르소나 분석기")
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
    
    # [M5] 파일명에서 정보 자동 추출 강화
    # 패턴 우선순위:
    #   1. KakaoTalk_YYYYMMDD_HHMMSS_이름.txt  (카카오 공식 내보내기)
    #   2. 이름_카카오.txt, 카카오_이름.txt
    #   3. _ 구분자 마지막 세그먼트
    #   4. 파일명 전체 사용 (기존 "담당자" 기본값 개선)
    import re as _re
    filename = selected_file.stem

    # 패턴 1: KakaoTalk_YYYYMMDD_HHMMSS_이름 또는 KakaoTalk_이름_...
    _kakao_pattern = _re.match(
        r'^KakaoTalk[_\s]+(?:\d{8}[_\s]+\d{6}[_\s]+)?(.+?)(?:[_\s]+\d+)?$',
        filename,
        _re.IGNORECASE
    )
    if _kakao_pattern:
        name_guess = _kakao_pattern.group(1).replace('_', ' ').strip()
    # 패턴 2: 이름_카카오 또는 카카오_이름
    elif _re.search(r'카카오|kakao', filename, _re.IGNORECASE):
        _parts = _re.split(r'[_\s]+', filename)
        _parts = [p for p in _parts if not _re.search(r'카카오|kakao', p, _re.IGNORECASE)]
        name_guess = _parts[-1] if _parts else filename
    # 패턴 3: _ 구분자 마지막 세그먼트
    elif "_" in filename:
        name_guess = filename.split("_")[-1].strip()
    # 패턴 4: 파일명 전체 사용
    else:
        name_guess = filename.strip() or "담당자"

    # 빈 문자열 방지
    if not name_guess or not name_guess.strip():
        name_guess = filename if filename else "담당자"
    
    print(f"\n✅ 선택: {selected_file.name}")
    
    # 파일 읽기 (TXT, PDF 등 — utils.extract_text_from_file로 통합 처리)
    try:
        text_content = extract_text_from_file(selected_file)
    except Exception as e:
        print(f"파일을 읽는 중 오류가 발생했습니다: {e}")
        return
    if not text_content or not text_content.strip():
        print("파일에서 텍스트를 추출할 수 없습니다. 파일을 확인해주세요.")
        return
    
    print(f"📄 내용 길이: {len(text_content):,} 글자")
    
    # 광고주 정보 입력 (자동 추천)
    print("\n📝 광고주 정보를 입력하세요 (엔터시 기본값):")
    print(f"   담당자 이름 [{name_guess}]: ", end="")
    client_name = input().strip() or name_guess
    
    print(f"   소속 기관 [하이브미디어]: ", end="")
    organization = input().strip() or "하이브미디어"
    
    print("   업종을 선택하세요:")
    print("     1. 공공기관")
    print("     2. 피트니스/헬스")
    print("     3. 뷰티/화장품")
    print("     4. 일반 (기타)")
    print("   번호 입력 (엔터시 4번 선택): ", end="")
    _cat_map = {"1": "government", "2": "fitness", "3": "cosmetics", "4": "general"}
    _cat_input = input().strip()
    category = _cat_map.get(_cat_input, "general")
    print(f"   선택된 업종: {category}")
    
    # 분석 실행
    result = analyze_persona(client_name, organization, text_content, category)
    
    if result:
        persona_data, save_path = result
        
        print("\n" + "=" * 60)
        print("✅ 페르소나 심층 분석 완료!")
        print("=" * 60)
        
        pa = persona_data['persona_analysis']
        
        # 헬퍼 함수: 안전하게 점수 추출
        def get_score(d, *keys, default="-"):
            try:
                result = d
                for key in keys:
                    result = result[key]
                if isinstance(result, (int, float)):
                    return result
                return default
            except (KeyError, TypeError, IndexError):
                return default
        
        def score_bar(score, max_score=10, bar_length=10):
            """점수를 시각적 바로 표시"""
            if score == "-":
                return "[---------]"
            filled = int((score / max_score) * bar_length)
            empty = bar_length - filled
            return f"[{'█' * filled}{'░' * empty}]"
        
        # 전체 요약
        print("\n" + "━" * 60)
        print("[1] 페르소나 요약")
        print("━" * 60)
        summary = pa.get('overall_summary', {})
        print(f"  유형: {summary.get('persona_type', '분석 중')}")
        print(f"  핵심 특성:")
        for i, char in enumerate(summary.get('key_characteristics', [])[:3], 1):
            print(f"     {i}. {char}")
        difficulty = summary.get('content_creation_difficulty', 5)
        print(f"  콘텐츠 제작 난이도: {score_bar(difficulty)} {difficulty}/10")
        print(f"  핵심 주의점: {summary.get('primary_caution', '-')}")
        
        # 격식도 분석
        print("\n" + "━" * 60)
        print("[2] 격식도 분석")
        print("━" * 60)
        formality = pa.get('formality_analysis', {})
        overall = get_score(formality, 'overall_score')
        print(f"  전체 격식도:       {score_bar(overall)} {overall}/10")
        print(f"  격식 언어 사용:    {score_bar(get_score(formality, 'formal_language_usage', 'score'))} {get_score(formality, 'formal_language_usage', 'score')}/10")
        print(f"  경어 레벨:         {score_bar(get_score(formality, 'honorifics_level', 'score'))} {get_score(formality, 'honorifics_level', 'score')}/10")
        print(f"  비즈니스 격식:     {score_bar(get_score(formality, 'business_formality', 'score'))} {get_score(formality, 'business_formality', 'score')}/10")
        
        # 커뮤니케이션 스타일
        print("\n" + "━" * 60)
        print("[3] 커뮤니케이션 스타일")
        print("━" * 60)
        comm = pa.get('communication_style', {})
        print(f"  직접성:            {score_bar(get_score(comm, 'directness', 'score'))} {get_score(comm, 'directness', 'score')}/10 ({get_score(comm, 'directness', 'style', default='?')})")
        print(f"  응답 속도 기대:    {score_bar(get_score(comm, 'response_speed_expectation', 'score'))} {get_score(comm, 'response_speed_expectation', 'score')}/10")
        print(f"  피드백 스타일:     {score_bar(get_score(comm, 'feedback_style', 'score'))} {get_score(comm, 'feedback_style', 'score')}/10 ({get_score(comm, 'feedback_style', 'type', default='?')})")
        print(f"  의사결정 방식:     {score_bar(get_score(comm, 'decision_making', 'score'))} {get_score(comm, 'decision_making', 'score')}/10 ({get_score(comm, 'decision_making', 'type', default='?')})")
        print(f"  감정 표현:         {score_bar(get_score(comm, 'emotional_expression', 'score'))} {get_score(comm, 'emotional_expression', 'score')}/10")
        print(f"  이모지 사용:       {score_bar(get_score(comm, 'emotional_expression', 'emoji_usage'))} {get_score(comm, 'emotional_expression', 'emoji_usage')}/10")
        
        # 글쓰기 DNA
        print("\n" + "━" * 60)
        print("[4] 글쓰기 DNA")
        print("━" * 60)
        writing = pa.get('writing_dna', {})
        print(f"  문장 복잡도:       {score_bar(get_score(writing, 'sentence_structure', 'complexity_score'))} {get_score(writing, 'sentence_structure', 'complexity_score')}/10")
        print(f"  어휘 수준:         {score_bar(get_score(writing, 'vocabulary_level', 'score'))} {get_score(writing, 'vocabulary_level', 'score')}/10")
        print(f"  전문용어 빈도:     {score_bar(get_score(writing, 'vocabulary_level', 'industry_jargon_frequency'))} {get_score(writing, 'vocabulary_level', 'industry_jargon_frequency')}/10")
        print(f"  느낌표 사용:       {score_bar(get_score(writing, 'punctuation_habits', 'exclamation_frequency'))} {get_score(writing, 'punctuation_habits', 'exclamation_frequency')}/10")
        print(f"  간결성:            {score_bar(get_score(writing, 'paragraph_style', 'brevity_score'))} {get_score(writing, 'paragraph_style', 'brevity_score')}/10")
        print(f"  리스트 선호:       {score_bar(get_score(writing, 'paragraph_style', 'list_preference'))} {get_score(writing, 'paragraph_style', 'list_preference')}/10")
        
        # 성격 지표
        print("\n" + "━" * 60)
        print("[5] 성격 지표")
        print("━" * 60)
        personality = pa.get('personality_metrics', {})
        print(f"  완벽주의:          {score_bar(get_score(personality, 'perfectionism', 'score'))} {get_score(personality, 'perfectionism', 'score')}/10")
        print(f"  디테일 지향:       {score_bar(get_score(personality, 'detail_orientation', 'score'))} {get_score(personality, 'detail_orientation', 'score')}/10")
        print(f"  긴급성 민감도:     {score_bar(get_score(personality, 'urgency_sensitivity', 'score'))} {get_score(personality, 'urgency_sensitivity', 'score')}/10")
        print(f"  유연성:            {score_bar(get_score(personality, 'flexibility', 'score'))} {get_score(personality, 'flexibility', 'score')}/10")
        print(f"  리스크 수용도:     {score_bar(get_score(personality, 'risk_tolerance', 'score'))} {get_score(personality, 'risk_tolerance', 'score')}/10")
        print(f"  자율성 선호:       {score_bar(get_score(personality, 'autonomy_preference', 'score'))} {get_score(personality, 'autonomy_preference', 'score')}/10")
        
        # 콘텐츠 선호도
        print("\n" + "━" * 60)
        print("[6] 콘텐츠 선호도")
        print("━" * 60)
        content = pa.get('content_preferences', {})
        print(f"  선호 톤: {get_score(content, 'tone_preference', 'primary', default='?')}")
        print(f"  긴 콘텐츠 수용도:  {score_bar(get_score(content, 'length_preference', 'tolerance_for_long'))} {get_score(content, 'length_preference', 'tolerance_for_long')}/10")
        print(f"  이미지 중요도:     {score_bar(get_score(content, 'visual_preference', 'image_importance'))} {get_score(content, 'visual_preference', 'image_importance')}/10")
        print(f"  불릿포인트 선호:   {score_bar(get_score(content, 'structure_preference', 'bullet_points'))} {get_score(content, 'structure_preference', 'bullet_points')}/10")
        print(f"  제목 중요도:       {score_bar(get_score(content, 'structure_preference', 'headers_importance'))} {get_score(content, 'structure_preference', 'headers_importance')}/10")
        
        # 긍정 트리거
        print("\n" + "━" * 60)
        print("[7] 긍정 반응 트리거")
        print("━" * 60)
        triggers = pa.get('positive_triggers', {})
        for expr in triggers.get('favorite_expressions', [])[:3]:
            print(f"  + {expr}")
        
        # 민감 영역
        print("\n" + "━" * 60)
        print("[8] 절대 금지 사항")
        print("━" * 60)
        sensitive = pa.get('sensitive_areas', {}).get('absolute_dont', {})
        for expr in sensitive.get('expressions', [])[:3]:
            print(f"  - {expr}")
        
        # 저장 정보
        print("\n" + "━" * 60)
        print(f"저장 위치: {save_path}")
        
        # 폴더 열기 옵션
        print("\n" + "=" * 60)
        print("📂 페르소나 폴더를 여시겠습니까? (Y/n): ", end="")
        open_folder = input().strip().lower()
        if open_folder != 'n':
            import subprocess
            subprocess.run(['explorer', str(DATA_DIR)])
            print("   폴더를 열었습니다.")
        
        # 블로그 작성 자동 실행 (SKIP_BLOG 환경변수로 건너뛰기 가능)
        if os.getenv("SKIP_BLOG"):
            print("\n💡 페르소나만 분석 완료! (블로그 생성 건너뜀)")
        else:
            print("\n" + "=" * 60)
            print("📝 블로그 글 자동 생성을 시작합니다...")
            print("=" * 60)
            
            # run_blog_generator 호출
            client_id = persona_data['client_id']
            try:
                from run_blog_generator import generate_blog_with_persona
                generate_blog_with_persona(client_id)
            except ImportError as ie:
                print(f"\n❌ 블로그 생성기 로드 실패: {ie}")
                print("   python run_blog_generator.py 로 별도 실행하세요.")
            except Exception as e:
                print(f"\n❌ 블로그 생성 오류: {e}")
    else:
        print("❌ 분석에 실패했습니다.")


if __name__ == "__main__":
    main()
