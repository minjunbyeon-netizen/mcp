#!/usr/bin/env python3
"""
페르소나 도구 웹 대시보드 - Flask 백엔드
사용법: python app.py
"""

import sys
import os
import json
import io
import tempfile
from pathlib import Path
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, session, redirect, url_for
from flask_cors import CORS
from authlib.integrations.flask_client import OAuth
from functools import wraps
import pdfplumber
import requests as http_requests

# Windows 터미널 UTF-8 출력 설정
if sys.platform == 'win32' and not isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 프로젝트 루트 설정
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "persona-manager"))

# 환경 변수 로드
from dotenv import load_dotenv
load_dotenv()
load_dotenv(PROJECT_ROOT / "persona-manager" / ".env")

# mcp_config.json에서 API 키 로드
config_path = PROJECT_ROOT / "mcp_config.json"
if config_path.exists():
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
        env_config = config.get("mcpServers", {}).get("persona-manager", {}).get("env", {})
        if not os.getenv("GEMINI_API_KEY"):
            api_key = env_config.get("GEMINI_API_KEY")
            if api_key:
                os.environ["GEMINI_API_KEY"] = api_key
        if not os.getenv("UNSPLASH_ACCESS_KEY"):
            unsplash_key = env_config.get("UNSPLASH_ACCESS_KEY")
            if unsplash_key:
                os.environ["UNSPLASH_ACCESS_KEY"] = unsplash_key

# HWP 지원
try:
    import olefile
    import zlib
    HWP_SUPPORTED = True
except ImportError:
    HWP_SUPPORTED = False

# Flask 앱 설정
app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# 세션 시크릿 키 (SSO용)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')

# OAuth 설정
oauth = OAuth(app)

# Google OAuth 설정 (환경 변수에서 로드)
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')

if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    google = oauth.register(
        name='google',
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile https://www.googleapis.com/auth/drive.file'},
    )
    SSO_ENABLED = True
    print("[OK] Google OAuth SSO 활성화됨")
else:
    google = None
    SSO_ENABLED = False
    print("[INFO] Google OAuth 미설정 (GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET 환경 변수 필요)")

# 허용된 이메일 도메인 (쉼표로 구분)
ALLOWED_DOMAINS = os.getenv('ALLOWED_DOMAINS', '').split(',')
ALLOWED_DOMAINS = [d.strip() for d in ALLOWED_DOMAINS if d.strip()]

# 경로 설정
PERSONA_DIR = PROJECT_ROOT / "output" / "personas"
PERSONA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR = Path.home() / "mcp-data" / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
BLOG_COLLECTIONS_DIR = PROJECT_ROOT / "blog_pull" / "output"
BLOG_COLLECTIONS_DIR.mkdir(parents=True, exist_ok=True)
DNA_DIR = OUTPUT_DIR / "dna"
DNA_DIR.mkdir(parents=True, exist_ok=True)
BUSINESS_DIR = OUTPUT_DIR / "business"
BUSINESS_DIR.mkdir(parents=True, exist_ok=True)

# blog_pull 모듈 경로 추가
sys.path.insert(0, str(PROJECT_ROOT / "blog_pull"))

# Google Gemini API 클라이언트
from google import genai


# ============================================================
# File Text Extraction (run_persona_test.py 기능 동일)
# ============================================================

def extract_text_from_file(file_path: Path) -> str:
    """다양한 파일 형식에서 텍스트 추출"""
    ext = file_path.suffix.lower()
    
    if ext == '.txt':
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    elif ext == '.pdf':
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text
    
    elif ext == '.hwp':
        if not HWP_SUPPORTED:
            raise ValueError("HWP 지원을 위해 'pip install olefile'를 실행하세요.")
        
        text_parts = []
        try:
            ole = olefile.OleFileIO(str(file_path))
            for stream in ole.listdir():
                if 'BodyText' in stream or 'Section' in stream:
                    try:
                        data = ole.openstream(stream).read()
                        try:
                            decompressed = zlib.decompress(data, -15)
                            text = decompressed.decode('utf-16-le', errors='ignore')
                            text = ''.join(c for c in text if c.isprintable() or c in '\n\r\t')
                            if text.strip():
                                text_parts.append(text)
                        except:
                            pass
                    except:
                        pass
            ole.close()
        except Exception as e:
            raise ValueError(f"HWP 파일 읽기 실패: {e}")
        
        return "\n".join(text_parts) if text_parts else ""
    
    else:
        raise ValueError(f"지원되지 않는 파일 형식: {ext}")


def save_uploaded_file(file) -> Path:
    """업로드된 파일을 임시 저장"""
    ext = Path(file.filename).suffix.lower()
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    file.save(temp_file.name)
    return Path(temp_file.name)


# ============================================================
# SSO Authentication (Google OAuth)
# ============================================================

def login_required(f):
    """로그인 필수 데코레이터"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not SSO_ENABLED:
            # SSO 미설정 시 바로 통과
            return f(*args, **kwargs)
        if 'user' not in session:
            return jsonify({"error": "로그인이 필요합니다.", "login_required": True}), 401
        return f(*args, **kwargs)
    return decorated_function


@app.route('/login')
def login():
    """Google 로그인 시작"""
    if not SSO_ENABLED:
        return jsonify({"error": "SSO가 설정되지 않았습니다."}), 500
    redirect_uri = url_for('callback', _external=True)
    return google.authorize_redirect(redirect_uri)


@app.route('/callback')
def callback():
    """Google 로그인 콜백"""
    if not SSO_ENABLED:
        return redirect('/')
    
    try:
        token = google.authorize_access_token()
        user_info = token.get('userinfo', {})
        
        email = user_info.get('email', '')
        domain = email.split('@')[-1] if '@' in email else ''
        
        # 도메인 검증 (ALLOWED_DOMAINS가 설정된 경우만)
        if ALLOWED_DOMAINS and domain not in ALLOWED_DOMAINS:
            return f'''
            <html>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h2>❌ 접근 거부</h2>
                <p>허용되지 않은 도메인입니다: <strong>{domain}</strong></p>
                <p>허용 도메인: {', '.join(ALLOWED_DOMAINS)}</p>
                <a href="/">돌아가기</a>
            </body>
            </html>
            ''', 403
        
        # 세션에 사용자 정보 저장
        session['user'] = {
            'email': email,
            'name': user_info.get('name', ''),
            'picture': user_info.get('picture', '')
        }
        # Google API 호출을 위한 액세스 토큰 저장
        session['google_token'] = token.get('access_token', '')
        
        print(f"[OK] 로그인 성공: {email}")
        return redirect('/')
        
    except Exception as e:
        print(f"[ERROR] 로그인 실패: {e}")
        return f"로그인 실패: {str(e)}", 500


@app.route('/logout')
def logout():
    """로그아웃"""
    user_email = session.get('user', {}).get('email', 'unknown')
    session.pop('user', None)
    print(f"[INFO] 로그아웃: {user_email}")
    return redirect('/')


@app.route('/api/auth/status')
def auth_status():
    """현재 인증 상태 반환"""
    if 'user' in session:
        return jsonify({
            "logged_in": True,
            "sso_enabled": SSO_ENABLED,
            "user": session['user']
        })
    else:
        return jsonify({
            "logged_in": False,
            "sso_enabled": SSO_ENABLED,
            "allowed_domains": ALLOWED_DOMAINS
        })


# ============================================================
# Static Files (Frontend)
# ============================================================

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory('.', filename)


# ============================================================
# API: Persona
# ============================================================

@app.route('/api/persona/list', methods=['GET'])
@login_required
def list_personas():
    """저장된 페르소나 목록 반환"""
    personas = []
    
    for file_path in PERSONA_DIR.glob("*.json"):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                if "client_id" in data and "persona_analysis" in data:
                    pa = data.get("persona_analysis", {})
                    formality = pa.get("formality_level", {})
                    if isinstance(formality, dict):
                        score = formality.get("score", 5)
                    else:
                        score = formality if isinstance(formality, (int, float)) else 5
                    
                    if score == 5 and "formality_analysis" in pa:
                        score = pa.get("formality_analysis", {}).get("overall_score", 5)
                    
                    personas.append({
                        "client_id": data["client_id"],
                        "client_name": data.get("client_name", data["client_id"]),
                        "organization": data.get("organization", ""),
                        "formality": score,
                        "created_at": data.get("created_at", "")
                    })
        except Exception as e:
            print(f"페르소나 로드 오류: {file_path.name} - {e}")
    
    personas.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return jsonify({"personas": personas})


@app.route('/api/persona/extract', methods=['POST'])
@login_required
def extract_persona():
    """파일 업로드로 페르소나 추출 (run_persona_test.py 기능과 동일)"""
    
    # 파일 확인
    if 'file' not in request.files:
        return jsonify({"error": "파일이 업로드되지 않았습니다."}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "파일이 선택되지 않았습니다."}), 400
    
    # 폼 데이터
    client_name = request.form.get("client_name", "")
    organization = request.form.get("organization", "하이브미디어")
    category = request.form.get("category", "general")
    
    # 파일명에서 이름 자동 추출
    filename = Path(file.filename).stem
    if not client_name:
        name_parts = filename.split("_")
        client_name = name_parts[-1] if len(name_parts) > 1 else filename
    
    # 파일 저장 및 텍스트 추출
    temp_path = None
    try:
        temp_path = save_uploaded_file(file)
        kakao_chat = extract_text_from_file(temp_path)
        
        if not kakao_chat.strip():
            return jsonify({"error": "파일에서 텍스트를 추출할 수 없습니다."}), 400
        
        print(f"파일 처리 완료: {file.filename}, {len(kakao_chat)}자")
        
    except Exception as e:
        return jsonify({"error": f"파일 읽기 실패: {str(e)}"}), 500
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink()
    
    # API 키 확인
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return jsonify({"error": "GEMINI_API_KEY가 설정되지 않았습니다."}), 500
    
    try:
        client = genai.Client(api_key=api_key)
        
        # 분석 프롬프트 (run_persona_test.py와 100% 동일한 상세 버전)
        analysis_prompt = f"""
당신은 광고/마케팅 에이전시의 시니어 페르소나 분석 전문가입니다.
아래 카카오톡 대화를 철저히 분석하여 광고주의 상세한 페르소나를 추출해주세요.
모든 분석은 실제 대화 내용에서 발견된 패턴과 근거를 바탕으로 해야 합니다.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【광고주 기본 정보】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
담당자명: {client_name}
소속 기관: {organization}
업종 분류: {category}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【분석 대상 카카오톡 대화】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{kakao_chat[:10000]}

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
        "key_characteristics": ["특징1", "특징2", "특징3", "특징4", "특징5"],
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
            "preferred_endings": ["실제 사용되는 종결어미들"],
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
        
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=analysis_prompt
        )
        
        response_text = response.text
        
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        
        persona_analysis = json.loads(response_text.strip())
        
        # 저장
        safe_org = organization.replace(' ', '_').replace('/', '_')
        safe_name = client_name.replace(' ', '_').replace('/', '_')
        client_id = f"{safe_org}_{safe_name}"
        
        # 격식도 추출 (상세 분석 구조)
        formality_data = persona_analysis.get("formality_analysis", {})
        formality = formality_data.get("overall_score", 5)
        
        if formality >= 8:
            tone = "매우 격식있고 공식적인"
            endings = "~습니다, ~입니다"
        elif formality >= 6:
            tone = "정중하되 부드러운"
            endings = "~합니다, ~해요"
        elif formality >= 4:
            tone = "친근하고 편안한"
            endings = "~해요, ~예요"
        else:
            tone = "매우 캐주얼하고 편한"
            endings = "~해, ~야"
        
        # 상세 custom_prompt 생성
        personality = persona_analysis.get("personality_metrics", {})
        content_pref = persona_analysis.get("content_preferences", {})
        sensitive = persona_analysis.get("sensitive_areas", {})
        positive = persona_analysis.get("positive_triggers", {})
        
        custom_prompt = f"""
【{client_name} 전용 콘텐츠 제작 가이드】

[기본 톤앤매너]
- 격식도: {formality}/10
- 톤: {tone}
- 종결어미: {endings}
- 선호 톤: {content_pref.get('tone_preference', {}).get('primary', 'professional')}

[성격 지표]
- 완벽주의: {personality.get('perfectionism', {}).get('score', 5)}/10
- 디테일 중시: {personality.get('detail_orientation', {}).get('score', 5)}/10
- 긴급성 민감도: {personality.get('urgency_sensitivity', {}).get('score', 5)}/10
- 유연성: {personality.get('flexibility', {}).get('score', 5)}/10

[금기 사항]
- 금지 표현: {', '.join(sensitive.get('absolute_dont', {}).get('expressions', [])[:3])}
- 피할 주제: {', '.join(sensitive.get('absolute_dont', {}).get('topics', [])[:3])}

[긍정 트리거]
- 선호 표현: {', '.join(positive.get('favorite_expressions', [])[:3])}
- 중요 가치: {', '.join(positive.get('value_keywords', [])[:3])}
"""
        
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
        
        save_path = PERSONA_DIR / f"{client_id}.json"
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(persona_data, f, ensure_ascii=False, indent=2)
        
        # 응답 데이터 (더 많은 정보 포함)
        summary = persona_analysis.get("overall_summary", {})
        personality_metrics = persona_analysis.get("personality_metrics", {})
        writing_dna = persona_analysis.get("writing_dna", {})
        comm_style = persona_analysis.get("communication_style", {})
        
        return jsonify({
            "success": True,
            "client_id": client_id,
            # 기본 점수
            "formality_score": formality,
            "perfectionism_score": personality_metrics.get("perfectionism", {}).get("score", 5),
            "detail_orientation_score": personality_metrics.get("detail_orientation", {}).get("score", 5),
            "urgency_sensitivity_score": personality_metrics.get("urgency_sensitivity", {}).get("score", 5),
            "flexibility_score": personality_metrics.get("flexibility", {}).get("score", 5),
            # 커뮤니케이션 스타일
            "directness_score": comm_style.get("directness", {}).get("score", 5),
            "decision_making_type": comm_style.get("decision_making", {}).get("type", "숙고형"),
            "emotional_expression": comm_style.get("emotional_expression", {}).get("level", "중립"),
            # 문체 DNA
            "sentence_length": writing_dna.get("sentence_structure", {}).get("avg_length", "medium"),
            "vocabulary_style": writing_dna.get("vocabulary_level", {}).get("style", "혼용"),
            # 종합
            "persona_type": summary.get("persona_type", "분석 완료"),
            "key_characteristics": summary.get("key_characteristics", []),
            "content_difficulty": summary.get("content_creation_difficulty", 5),
            "primary_caution": summary.get("primary_caution", ""),
            # 세부 정보
            "red_flags": sensitive.get("absolute_dont", {}).get("expressions", []),
            "green_flags": positive.get("favorite_expressions", []),
            "save_path": str(save_path)
        })
        
    except Exception as e:
        return jsonify({"error": f"페르소나 분석 실패: {str(e)}"}), 500


# ============================================================
# API: Blog Generator
# ============================================================

@app.route('/api/blog/generate', methods=['POST'])
@login_required
def generate_blog():
    """페르소나 기반 블로그 글 생성 (파일 업로드 지원)"""
    
    client_id = request.form.get("client_id", "")
    keywords_str = request.form.get("keywords", "")
    keywords = [k.strip() for k in keywords_str.split(",") if k.strip()]
    blog_dna_folder = request.form.get("blog_dna_folder", "")
    
    # 보도자료: 파일 또는 직접 입력
    press_release = ""
    
    if 'file' in request.files and request.files['file'].filename:
        file = request.files['file']
        temp_path = None
        try:
            temp_path = save_uploaded_file(file)
            press_release = extract_text_from_file(temp_path)
        except Exception as e:
            return jsonify({"error": f"파일 읽기 실패: {str(e)}"}), 500
        finally:
            if temp_path and temp_path.exists():
                temp_path.unlink()
    else:
        press_release = request.form.get("press_release", "")
    
    if not client_id or not press_release.strip():
        return jsonify({"error": "페르소나와 보도자료 내용이 필요합니다."}), 400
    
    # 페르소나 로드
    persona_data = None
    for file_path in PERSONA_DIR.glob("*.json"):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data_loaded = json.load(f)
                if data_loaded.get("client_id") == client_id:
                    persona_data = data_loaded
                    break
        except:
            pass
    
    if not persona_data:
        return jsonify({"error": f"페르소나를 찾을 수 없습니다: {client_id}"}), 404
    
    # 블로그 DNA 로드 (선택사항)
    blog_dna_text = ""
    if blog_dna_folder:
        dna_data_file = BLOG_COLLECTIONS_DIR / blog_dna_folder / "_data.json"
        if dna_data_file.exists():
            try:
                with open(dna_data_file, 'r', encoding='utf-8') as f:
                    dna_collection = json.load(f)
                
                dna_posts = dna_collection.get("posts", [])
                dna_blog_id = dna_collection.get("blog_id", "")
                
                # 블로그 글 요약 생성 (DNA 분석용)
                dna_summary = ""
                for i, post in enumerate(dna_posts[:8], 1):
                    content = post.get("content", "")[:1200]
                    dna_summary += f"\n--- 글 {i}: {post.get('title', '')} ---\n{content}\n"
                
                if dna_summary.strip():
                    blog_dna_text = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【블로그 DNA - {dna_blog_id}의 실제 글쓰기 스타일】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
아래는 이 블로그의 실제 글들입니다. 이 글들의 구조, 어투, 화법, 자주 쓰는 표현,
문장 패턴, 문단 구성 등을 철저히 분석하여 동일한 스타일로 글을 작성해야 합니다.

{dna_summary}

※ 위 블로그 글의 다음 요소를 반드시 재현하세요:
- 글의 전체 구조/템플릿 (도입-본문-마무리 패턴)
- 종결어미와 어투 (예: ~요, ~습니다, ~거든요 등)
- 소제목/헤딩 사용 방식
- 자주 쓰는 표현과 접속어
- 문장 길이와 복잡도
- 독자를 부르는 방식
- 감성적 표현 or 정보 전달 비율
"""
                    print(f"[OK] 블로그 DNA 로드됨: {dna_blog_id} ({len(dna_posts)}개 글)")
            except Exception as e:
                print(f"[WARN] 블로그 DNA 로드 실패: {e}")
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return jsonify({"error": "GEMINI_API_KEY가 설정되지 않았습니다."}), 500
    
    try:
        client = genai.Client(api_key=api_key)
        
        client_name = persona_data.get("client_name", client_id)
        custom_prompt = persona_data.get("custom_prompt", "")
        persona_analysis = persona_data.get("persona_analysis", {})
        
        formality = persona_analysis.get("formality_level", {})
        if isinstance(formality, dict):
            formality_score = formality.get("score", 5)
        else:
            formality_score = formality if isinstance(formality, (int, float)) else 5
        
        if formality_score == 5 and "formality_analysis" in persona_analysis:
            formality_score = persona_analysis.get("formality_analysis", {}).get("overall_score", 5)
        
        green_flags = persona_analysis.get("green_flags", [])
        red_flags = persona_analysis.get("red_flags", [])
        
        keywords_text = ", ".join(keywords) if keywords else ""
        
        # 블로그 DNA 관련 작성 지침 추가
        dna_instruction = ""
        if blog_dna_text:
            dna_instruction = """6. 【중요】 블로그 DNA에서 분석된 글쓰기 스타일(구조, 어투, 화법, 표현)을 최우선으로 반영하세요.
7. 페르소나의 톤/성격과 블로그 DNA의 글쓰기 패턴을 자연스럽게 융합하세요."""
        
        blog_prompt = f"""
당신은 '{client_name}'의 페르소나에 맞춰 블로그 글을 작성하는 전문가입니다.
동일한 보도자료를 기반으로 **3가지 톤 버전**의 블로그 글을 작성해야 합니다.

【페르소나 정보】
{custom_prompt}

【격식도】
{formality_score}/10

【적극 활용】
{json.dumps(green_flags, ensure_ascii=False)}

【금지 사항】
{json.dumps(red_flags, ensure_ascii=False)}
{blog_dna_text}
【보도자료】
{press_release[:5000]}

【타겟 키워드】
{keywords_text}

【작성 지침】
1. 위 페르소나의 톤과 스타일을 기본으로 삼되, 3가지 톤 버전으로 변주하세요.
2. SEO 최적화된 제목 (60자 이내)
3. 각 버전 본문 1,500~2,000자 분량
4. **절대 금지 사항**: 마크다운 기호를 절대 사용하지 마세요. ##, **, ***, >, -, ```, [ ], " " 등 어떤 마크다운/서식 기호도 사용 금지.
   - 소제목이 필요하면 그냥 줄바꿈 후 텍스트로 쓰세요 (예: "첫 번째 이야기")
   - 강조가 필요하면 문맥으로 표현하세요, 기호로 하지 마세요
   - 진짜 사람이 블로그에 직접 타이핑한 것처럼 자연스러운 일반 텍스트로 작성하세요
5. 3가지 버전의 핵심 차이:
   - formal (포멀): 격식체, 공식적 어투, ~습니다/~입니다 종결, 전문 용어 적극 사용, 정보 중심
   - balanced (밸런스): 페르소나+DNA 조합 그대로의 자연스러운 어투, 원래 분석된 톤 유지
   - casual (캐주얼): 더 자유로운 어투, 친근한 표현, 이모티콘/감탄사 활용 가능, 독자와 대화하는 느낌
{dna_instruction}

【출력 JSON】
반드시 아래 형식으로만 출력하세요 (3개 버전 모두 포함):
{{
    "versions": [
        {{
            "version_type": "formal",
            "version_label": "포멀",
            "title": "포멀 버전 제목",
            "content": "일반 텍스트 본문 (마크다운 기호 절대 금지)",
            "tags": ["태그1", "태그2", "태그3", "태그4", "태그5"],
            "meta_description": "155자 이내 요약"
        }},
        {{
            "version_type": "balanced",
            "version_label": "밸런스",
            "title": "밸런스 버전 제목",
            "content": "일반 텍스트 본문 (마크다운 기호 절대 금지)",
            "tags": ["태그1", "태그2", "태그3", "태그4", "태그5"],
            "meta_description": "155자 이내 요약"
        }},
        {{
            "version_type": "casual",
            "version_label": "캐주얼",
            "title": "캐주얼 버전 제목",
            "content": "일반 텍스트 본문 (마크다운 기호 절대 금지)",
            "tags": ["태그1", "태그2", "태그3", "태그4", "태그5"],
            "meta_description": "155자 이내 요약"
        }}
    ]
}}
"""
        
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=blog_prompt
        )
        
        response_text = response.text
        
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        
        blog_result = json.loads(response_text.strip())
        versions = blog_result.get("versions", [])
        
        if not versions:
            return jsonify({"error": "AI가 3가지 버전을 생성하지 못했습니다."}), 500
        
        output_id = f"BLOG_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 각 버전별 MD 파일 저장
        for ver in versions:
            vtype = ver.get("version_type", "unknown")
            md_path = OUTPUT_DIR / f"{output_id}_{vtype}.md"
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(f"# [{ver.get('version_label', vtype)}] {ver.get('title', '')}\n\n")
                f.write(f"{ver.get('content', '')}\n\n")
                f.write(f"**태그:** {', '.join(ver.get('tags', []))}\n")
        
        # 전체 JSON 저장
        json_path = OUTPUT_DIR / f"{output_id}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump({
                "output_id": output_id,
                "client_id": client_id,
                "versions": versions,
                "created_at": datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            "success": True,
            "versions": versions,
            "output_id": output_id,
            "output_dir": str(OUTPUT_DIR)
        })
        
    except Exception as e:
        return jsonify({"error": f"블로그 생성 실패: {str(e)}"}), 500


# ============================================================
# API: Blog Image Generation (On-Demand)
# ============================================================

@app.route('/api/blog/generate-images', methods=['POST'])
@login_required
def generate_blog_images():
    """블로그 본문 기반 AI 이미지 생성 (On-Demand)"""
    data = request.json
    
    blog_content = data.get("content", "")
    if not blog_content or not blog_content.strip():
        return jsonify({"error": "이미지 생성을 위한 블로그 본문이 필요합니다."}), 400
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return jsonify({"error": "GEMINI_API_KEY가 설정되지 않았습니다."}), 500
    
    try:
        client = genai.Client(api_key=api_key)
        
        from image_service import generate_images_for_blog
        images = generate_images_for_blog(blog_content, client, OUTPUT_DIR)
        
        if not images:
            return jsonify({"error": "이미지를 생성하지 못했습니다. 다시 시도해주세요."}), 500
        
        return jsonify({
            "success": True,
            "images": images,
            "count": len(images)
        })
        
    except Exception as e:
        return jsonify({"error": f"이미지 생성 실패: {str(e)}"}), 500


# ============================================================
# API: Match Rate Tester
# ============================================================

@app.route('/api/match-test', methods=['POST'])
@login_required
def match_test():
    """콘텐츠와 페르소나 일치율 테스트"""
    data = request.json
    
    client_id = data.get("client_id", "")
    content = data.get("content", "")
    
    if not client_id or not content:
        return jsonify({"error": "페르소나와 테스트할 콘텐츠가 필요합니다."}), 400
    
    persona_data = None
    for file_path in PERSONA_DIR.glob("*.json"):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data_loaded = json.load(f)
                if data_loaded.get("client_id") == client_id:
                    persona_data = data_loaded
                    break
        except:
            pass
    
    if not persona_data:
        return jsonify({"error": f"페르소나를 찾을 수 없습니다: {client_id}"}), 404
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return jsonify({"error": "GEMINI_API_KEY가 설정되지 않았습니다."}), 500
    
    try:
        client = genai.Client(api_key=api_key)
        
        client_name = persona_data.get("client_name", client_id)
        custom_prompt = persona_data.get("custom_prompt", "")
        persona_analysis = persona_data.get("persona_analysis", {})
        
        match_prompt = f"""
당신은 콘텐츠와 페르소나 일치율을 분석하는 전문가입니다.

【페르소나 정보: {client_name}】
{custom_prompt}

【분석 기준 페르소나】
{json.dumps(persona_analysis, ensure_ascii=False, indent=2)[:3000]}

【분석할 콘텐츠】
{content[:3000]}

【출력 JSON】
반드시 아래 형식으로만 출력하세요:
{{
    "overall_score": 0-100,
    "tone_match": 0-100,
    "style_match": 0-100,
    "vocabulary_match": 0-100,
    "analysis": "상세 분석 내용",
    "strengths": ["잘된 점1", "잘된 점2"],
    "weaknesses": ["개선점1", "개선점2"],
    "suggestions": ["제안1", "제안2", "제안3"]
}}
"""
        
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=match_prompt
        )
        
        response_text = response.text
        
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        
        result = json.loads(response_text.strip())
        
        return jsonify({
            "success": True,
            "overall_score": result.get("overall_score", 0),
            "tone_match": result.get("tone_match", 0),
            "style_match": result.get("style_match", 0),
            "vocabulary_match": result.get("vocabulary_match", 0),
            "analysis": result.get("analysis", ""),
            "strengths": result.get("strengths", []),
            "weaknesses": result.get("weaknesses", []),
            "suggestions": result.get("suggestions", [])
        })
        
    except Exception as e:
        return jsonify({"error": f"일치율 분석 실패: {str(e)}"}), 500


# ============================================================
# API: Blog Collection (blog_pull 통합)
# ============================================================

from run_crawler import get_blog_id, get_post_list, get_post_content, save_results
import run_crawler as _run_crawler
_run_crawler.OUTPUT_DIR = str(BLOG_COLLECTIONS_DIR)
import time as _time

@app.route('/api/blog/collect', methods=['POST'])
@login_required
def collect_blog():
    """네이버 블로그 글 수집 (blog_pull 크롤러 통합)"""
    data = request.json
    
    blog_input = data.get("blog_id", "").strip()
    count = min(int(data.get("count", 5)), 30)
    
    if not blog_input:
        return jsonify({"error": "블로그 주소 또는 ID를 입력해주세요."}), 400
    
    blog_id = get_blog_id(blog_input)
    if not blog_id:
        return jsonify({"error": f"올바른 블로그 주소가 아닙니다: {blog_input}"}), 400
    
    try:
        # STEP 1: 글 목록 가져오기
        posts = get_post_list(blog_id, count)
        
        if not posts:
            return jsonify({"error": "글 목록을 가져올 수 없습니다. 블로그 주소를 확인해주세요."}), 404
        
        # STEP 2: 본문 수집
        for post in posts:
            content = get_post_content(blog_id, post['logNo'])
            post['content'] = content if content else "(본문 추출 실패)"
            _time.sleep(0.3)
        
        # STEP 3: 저장
        folder = save_results(blog_id, posts)
        
        total_chars = sum(len(p.get('content', '')) for p in posts)
        
        return jsonify({
            "blog_id": blog_id,
            "blog_url": f"https://blog.naver.com/{blog_id}",
            "post_count": len(posts),
            "total_chars": total_chars,
            "output_folder": os.path.basename(folder),
            "posts": [
                {
                    "title": p['title'],
                    "date": p['addDate'],
                    "url": p['url'],
                    "content_length": len(p.get('content', '')),
                    "content_preview": p.get('content', '')[:200]
                }
                for p in posts
            ]
        })
        
    except Exception as e:
        return jsonify({"error": f"블로그 수집 실패: {str(e)}"}), 500


@app.route('/api/blog/collections', methods=['GET'])
@login_required
def list_blog_collections():
    """수집된 블로그 컬렉션 목록"""
    collections = []
    
    if BLOG_COLLECTIONS_DIR.exists():
        for item in sorted(BLOG_COLLECTIONS_DIR.iterdir(), reverse=True):
            if item.is_dir() and not item.name.startswith('.'):
                # _data.json에서 정보 읽기
                data_file = item / "_data.json"
                if data_file.exists():
                    try:
                        with open(data_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        collections.append({
                            "folder": item.name,
                            "blog_id": data.get("blog_id", ""),
                            "collected_at": data.get("collected_at", ""),
                            "post_count": len(data.get("posts", [])),
                            "total_chars": sum(len(p.get("content", "")) for p in data.get("posts", []))
                        })
                    except:
                        pass
    
    return jsonify({"collections": collections})


@app.route('/api/blog/analyze-status', methods=['POST'])
@login_required
def analyze_blog_status():
    """수집된 블로그 글을 AI로 분석하여 상태 파악"""
    data = request.json
    folder_name = data.get("folder", "")
    
    if not folder_name:
        return jsonify({"error": "분석할 컬렉션 폴더를 선택해주세요."}), 400
    
    folder_path = BLOG_COLLECTIONS_DIR / folder_name
    data_file = folder_path / "_data.json"
    
    if not data_file.exists():
        return jsonify({"error": "컬렉션 데이터를 찾을 수 없습니다."}), 404
    
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            collection = json.load(f)
        
        posts = collection.get("posts", [])
        blog_id = collection.get("blog_id", "")
        
        # 블로그 글 요약 텍스트 생성
        blog_summary = ""
        for i, post in enumerate(posts[:10], 1):  # 최대 10개
            content = post.get("content", "")[:1500]  # 글당 1500자
            blog_summary += f"\n\n--- 글 {i}: {post.get('title', '')} (날짜: {post.get('addDate', '')}) ---\n{content}"
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return jsonify({"error": "GEMINI_API_KEY가 설정되지 않았습니다."}), 500
        
        client = genai.Client(api_key=api_key)
        
        analysis_prompt = f"""당신은 블로그 글쓰기 DNA 분석 전문가입니다.
아래는 네이버 블로그 '{blog_id}'에서 수집한 최근 글들입니다.
이 블로그의 글쓰기 스타일, 구조, 어투, 화법, 표현 패턴을 아주 꼼꼼하게 분석해주세요.
모든 분석은 실제 글에서 발견된 패턴과 근거를 바탕으로 해야 합니다.

{blog_summary}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【분석 지침】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 10가지 카테고리별로 글에서 실제로 발견한 패턴을 근거(evidence)와 함께 제시
- 각 항목의 examples에는 실제 글에서 발췌한 표현을 반드시 포함
- 블로그 글을 그대로 재현할 수 있을 정도로 구체적으로 분석

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【출력 JSON 스키마 (10가지 카테고리)】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{{
  "c1_template_structure": {{
    "title": "글 템플릿/구조",
    "overall_pattern": "글의 전체적인 구조 패턴 (예: 서론-본론-결론, 리스트형, Q&A형 등)",
    "section_flow": ["도입부 패턴", "본문 전개 방식", "마무리 패턴"],
    "heading_style": "소제목/헤딩 사용 방식",
    "average_sections": "평균 섹션 수와 구성",
    "examples": ["실제 글에서 발췌한 구조 예시"]
  }},
  "c2_tone_mood": {{
    "title": "톤/분위기",
    "primary_tone": "주된 톤 (예: 친근한, 전문적, 공식적, 감성적 등)",
    "secondary_tone": "보조 톤",
    "formality_level": "격식 수준 (1-10)",
    "warmth_level": "친밀감 수준 (1-10)",
    "consistency": "톤 일관성 평가",
    "examples": ["톤을 보여주는 실제 문장 발췌"]
  }},
  "c3_speech_style": {{
    "title": "어투/말투",
    "ending_patterns": ["자주 쓰는 종결어미 (예: ~요, ~습니다, ~해요, ~거든요)"],
    "characteristic_phrases": ["특징적인 말투 패턴"],
    "question_style": "질문 던지기 방식 (있다면)",
    "reader_address": "독자를 부르는 방식 (예: 여러분, ~님, 우리 등)",
    "examples": ["실제 어투 발췌"]
  }},
  "c4_rhetoric": {{
    "title": "화법/수사법",
    "storytelling": "스토리텔링 활용 여부와 방식",
    "persuasion_technique": "설득/전달 기법",
    "humor_usage": "유머/위트 활용 수준 (1-10)",
    "metaphor_usage": "비유/은유 활용 빈도와 스타일",
    "emotional_appeal": "감정 호소 방식",
    "examples": ["화법이 드러나는 실제 문장"]
  }},
  "c5_frequent_expressions": {{
    "title": "자주 쓰는 표현",
    "signature_phrases": ["이 블로거만의 시그니처 표현 5개 이상"],
    "transition_words": ["자주 쓰는 접속/전환 표현"],
    "emphasis_expressions": ["강조할 때 쓰는 표현"],
    "filler_expressions": ["습관적으로 쓰는 군더더기 표현"],
    "examples": ["실제 반복 등장하는 표현 발췌"]
  }},
  "c6_sentence_patterns": {{
    "title": "문장 구조 패턴",
    "avg_length": "평균 문장 길이 (짧은/중간/긴)",
    "complexity": "문장 복잡도 (단문 위주/복문 위주/혼합)",
    "rhythm": "문장 리듬감 (짧은 문장과 긴 문장의 배치 패턴)",
    "list_usage": "나열/리스트 활용 빈도 (1-10)",
    "examples": ["특징적인 문장 구조 발췌"]
  }},
  "c7_vocabulary": {{
    "title": "어휘/용어 선택",
    "level": "어휘 수준 (쉬운/보통/전문적)",
    "style": "한자어 vs 순우리말 vs 외래어 비율",
    "jargon_usage": "전문용어/업계용어 사용 빈도",
    "trendy_words": "유행어/신조어 사용 여부",
    "characteristic_words": ["이 블로거가 특히 자주 쓰는 단어 목록"],
    "examples": ["어휘 특성이 보이는 문장 발췌"]
  }},
  "c8_paragraph_composition": {{
    "title": "단락/문단 구성",
    "avg_paragraph_length": "평균 문단 길이 (짧은/중간/긴)",
    "paragraph_count": "글당 평균 문단 수",
    "whitespace_usage": "여백/줄바꿈 활용 (많은/적절/적은)",
    "content_density": "정보 밀도 (높은/중간/낮은)",
    "examples": ["단락 구성 특징이 보이는 예시"]
  }},
  "c9_opening_closing": {{
    "title": "도입/마무리 패턴",
    "opening_types": ["자주 쓰는 도입 방식 (예: 질문, 인사, 상황 설명, 공감 유도 등)"],
    "closing_types": ["자주 쓰는 마무리 방식 (예: 요약, CTA, 인사, 감성 마무리 등)"],
    "hook_technique": "독자 후킹 기법",
    "cta_pattern": "행동 유도(CTA) 패턴",
    "opening_examples": ["실제 도입부 발췌"],
    "closing_examples": ["실제 마무리부 발췌"]
  }},
  "c10_visual_formatting": {{
    "title": "시각적 요소/포맷팅",
    "emoji_usage": "이모지/이모티콘 사용 빈도 (1-10)",
    "emoji_types": ["자주 쓰는 이모지 종류"],
    "bold_highlight": "볼드/강조 사용 패턴",
    "image_placement": "이미지 배치 패턴",
    "separator_style": "구분선/구분 요소 스타일",
    "special_formatting": ["특수 포맷팅 습관 (예: 괄호 사용, 따옴표, 말줄임표 등)"],
    "examples": ["포맷팅 특징이 보이는 예시"]
  }}
}}

반드시 유효한 JSON으로만 응답하세요. 다른 텍스트는 포함하지 마세요."""

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=analysis_prompt
        )
        
        result_text = response.text.strip()
        if result_text.startswith("```"):
            result_text = result_text.split("\n", 1)[1] if "\n" in result_text else result_text
            result_text = result_text.rsplit("```", 1)[0]
        
        result = json.loads(result_text)
        result["blog_id"] = blog_id
        result["post_count"] = len(posts)
        result["folder"] = folder_name
        result["created_at"] = datetime.now().isoformat()
        
        # DNA 분석 결과 자동 저장
        dna_id = f"DNA_{folder_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        result["dna_id"] = dna_id
        dna_path = DNA_DIR / f"{dna_id}.json"
        with open(dna_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        return jsonify(result)
        
    except json.JSONDecodeError:
        return jsonify({"error": "AI 분석 결과 파싱 실패", "raw": result_text}), 500
    except Exception as e:
        return jsonify({"error": f"블로그 분석 실패: {str(e)}"}), 500


@app.route('/api/persona/business-analysis', methods=['POST'])
@login_required
def business_analysis():
    """페르소나 + 블로그 교차 분석으로 업무적 성격 파악"""
    data = request.json
    client_id = data.get("client_id", "")
    folder_name = data.get("folder", "")
    
    if not client_id or not folder_name:
        return jsonify({"error": "페르소나와 블로그 컬렉션을 모두 선택해주세요."}), 400
    
    # 페르소나 데이터 로드
    persona_path = PERSONA_DIR / f"{client_id}.json"
    if not persona_path.exists():
        return jsonify({"error": f"페르소나를 찾을 수 없습니다: {client_id}"}), 404
    
    with open(persona_path, 'r', encoding='utf-8') as f:
        persona_data = json.load(f)
    
    # 블로그 데이터 로드
    data_file = BLOG_COLLECTIONS_DIR / folder_name / "_data.json"
    if not data_file.exists():
        return jsonify({"error": "블로그 컬렉션을 찾을 수 없습니다."}), 404
    
    with open(data_file, 'r', encoding='utf-8') as f:
        blog_data = json.load(f)
    
    try:
        # 페르소나 요약
        persona_text = json.dumps(persona_data, ensure_ascii=False, indent=2)[:3000]
        
        # 블로그 글 요약
        blog_summary = ""
        for i, post in enumerate(blog_data.get("posts", [])[:8], 1):
            content = post.get("content", "")[:1000]
            blog_summary += f"\n--- 글 {i}: {post.get('title', '')} ---\n{content}\n"
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return jsonify({"error": "GEMINI_API_KEY가 설정되지 않았습니다."}), 500
        
        client_ai = genai.Client(api_key=api_key)
        
        prompt = f"""당신은 광고/마케팅 에이전시의 시니어 분석가입니다.
아래 두 가지 데이터를 교차 분석하여 광고주의 업무적 성격을 종합 파악해주세요.

━━━ DATA 1: 카카오톡 대화 기반 페르소나 ━━━
{persona_text}

━━━ DATA 2: 운영 중인 블로그 글 ━━━
{blog_summary}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
위 두 데이터를 교차 분석하여 아래 JSON 형식으로 응답해주세요:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{{
  "business_personality": {{
    "type": "업무 성격 유형 (예: 꼼꼼한 관리자형, 감성적 기획자형 등)",
    "description": "종합적인 업무 성격 설명 (3-4줄)"
  }},
  "communication_style": {{
    "preferred": "선호하는 커뮤니케이션 방식",
    "response_speed": "응답 속도/패턴",
    "detail_level": "요구하는 디테일 수준"
  }},
  "content_preferences": {{
    "tone": "선호하는 콘텐츠 톤",
    "topics": ["관심 토픽 1", "관심 토픽 2"],
    "style": "콘텐츠 스타일 성향"
  }},
  "work_approach": {{
    "decision_style": "의사결정 스타일",
    "feedback_pattern": "피드백 패턴",
    "priority_focus": "우선시하는 것"
  }},
  "agency_recommendations": [
    "대응 전략 1",
    "대응 전략 2",
    "대응 전략 3"
  ],
  "risk_factors": ["주의할 점 1", "주의할 점 2"],
  "summary": "3줄 이내 핵심 요약"
}}

반드시 유효한 JSON으로만 응답하세요."""

        response = client_ai.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        
        result_text = response.text.strip()
        if result_text.startswith("```"):
            result_text = result_text.split("\n", 1)[1] if "\n" in result_text else result_text
            result_text = result_text.rsplit("```", 1)[0]
        
        result = json.loads(result_text)
        result["client_id"] = client_id
        result["blog_folder"] = folder_name
        result["created_at"] = datetime.now().isoformat()
        
        # 업무성격 분석 결과 자동 저장
        biz_id = f"BIZ_{client_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        result["biz_id"] = biz_id
        biz_path = BUSINESS_DIR / f"{biz_id}.json"
        with open(biz_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        return jsonify(result)
        
    except json.JSONDecodeError:
        return jsonify({"error": "AI 분석 결과 파싱 실패", "raw": result_text}), 500
    except Exception as e:
        return jsonify({"error": f"업무적 성격 분석 실패: {str(e)}"}), 500



# ============================================================
# API: My Page (데이터 관리)
# ============================================================

@app.route('/api/mypage/personas', methods=['GET'])
@login_required
def mypage_personas():
    """저장된 페르소나 목록 (상세 포함)"""
    items = []
    for fp in PERSONA_DIR.glob("*.json"):
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if "client_id" in data and "persona_analysis" in data:
                items.append({
                    "id": data["client_id"],
                    "client_name": data.get("client_name", data["client_id"]),
                    "organization": data.get("organization", ""),
                    "created_at": data.get("created_at", ""),
                    "filename": fp.name
                })
        except Exception:
            pass
    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return jsonify({"items": items})


@app.route('/api/mypage/personas/<client_id>', methods=['GET'])
@login_required
def mypage_persona_detail(client_id):
    """페르소나 상세"""
    fp = PERSONA_DIR / f"{client_id}.json"
    if not fp.exists():
        return jsonify({"error": "페르소나를 찾을 수 없습니다."}), 404
    with open(fp, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return jsonify(data)


@app.route('/api/mypage/blogs', methods=['GET'])
@login_required
def mypage_blogs():
    """생성된 블로그 글 목록"""
    items = []
    for fp in OUTPUT_DIR.glob("BLOG_*.json"):
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                data = json.load(f)
            versions = data.get("versions", [])
            title = versions[0].get("title", "") if versions else ""
            items.append({
                "id": data.get("output_id", fp.stem),
                "title": title,
                "client_id": data.get("client_id", ""),
                "version_count": len(versions),
                "created_at": data.get("created_at", ""),
                "filename": fp.name
            })
        except Exception:
            pass
    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return jsonify({"items": items})


@app.route('/api/mypage/blogs/<blog_id>', methods=['GET'])
@login_required
def mypage_blog_detail(blog_id):
    """블로그 상세 (3버전 포함)"""
    fp = OUTPUT_DIR / f"{blog_id}.json"
    if not fp.exists():
        return jsonify({"error": "블로그를 찾을 수 없습니다."}), 404
    with open(fp, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return jsonify(data)


@app.route('/api/mypage/dna', methods=['GET'])
@login_required
def mypage_dna_list():
    """DNA 분석 결과 목록"""
    items = []
    for fp in DNA_DIR.glob("DNA_*.json"):
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                data = json.load(f)
            items.append({
                "id": data.get("dna_id", fp.stem),
                "blog_id": data.get("blog_id", ""),
                "folder": data.get("folder", ""),
                "post_count": data.get("post_count", 0),
                "created_at": data.get("created_at", ""),
                "filename": fp.name
            })
        except Exception:
            pass
    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return jsonify({"items": items})


@app.route('/api/mypage/dna/<dna_id>', methods=['GET'])
@login_required
def mypage_dna_detail(dna_id):
    """DNA 상세"""
    fp = DNA_DIR / f"{dna_id}.json"
    if not fp.exists():
        return jsonify({"error": "DNA 분석 결과를 찾을 수 없습니다."}), 404
    with open(fp, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return jsonify(data)


@app.route('/api/mypage/business', methods=['GET'])
@login_required
def mypage_business_list():
    """업무적 성격 분석 결과 목록"""
    items = []
    for fp in BUSINESS_DIR.glob("BIZ_*.json"):
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                data = json.load(f)
            bp = data.get("business_personality", {})
            items.append({
                "id": data.get("biz_id", fp.stem),
                "client_id": data.get("client_id", ""),
                "blog_folder": data.get("blog_folder", ""),
                "type": bp.get("type", ""),
                "created_at": data.get("created_at", ""),
                "filename": fp.name
            })
        except Exception:
            pass
    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return jsonify({"items": items})


@app.route('/api/mypage/business/<biz_id>', methods=['GET'])
@login_required
def mypage_business_detail(biz_id):
    """업무적 성격 상세"""
    fp = BUSINESS_DIR / f"{biz_id}.json"
    if not fp.exists():
        return jsonify({"error": "업무적 성격 분석 결과를 찾을 수 없습니다."}), 404
    with open(fp, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return jsonify(data)


@app.route('/api/mypage/<data_type>/<item_id>', methods=['DELETE'])
@login_required
def mypage_delete(data_type, item_id):
    """마이페이지 항목 삭제"""
    dir_map = {
        "personas": PERSONA_DIR,
        "blogs": OUTPUT_DIR,
        "dna": DNA_DIR,
        "business": BUSINESS_DIR
    }
    target_dir = dir_map.get(data_type)
    if not target_dir:
        return jsonify({"error": "잘못된 데이터 타입입니다."}), 400
    
    fp = target_dir / f"{item_id}.json"
    if not fp.exists():
        return jsonify({"error": "항목을 찾을 수 없습니다."}), 404
    
    fp.unlink()
    
    # 블로그의 경우 MD 파일도 삭제
    if data_type == "blogs":
        for md in target_dir.glob(f"{item_id}_*.md"):
            md.unlink()
    
    return jsonify({"success": True, "message": "삭제되었습니다."})


# ============================================================
# Google Docs Export
# ============================================================

@app.route('/api/export/google-docs', methods=['POST'])
@login_required
def export_to_google_docs():
    """블로그 글을 Google Docs로 내보내기"""
    access_token = session.get('google_token')
    if not access_token:
        return jsonify({"error": "Google 로그인이 필요합니다. 다시 로그인해주세요."}), 401

    data = request.get_json()
    data_type = data.get('type', 'blogs')
    item_id = data.get('id', '')

    if not item_id:
        return jsonify({"error": "항목 ID가 필요합니다."}), 400

    # 데이터 로드
    if data_type == 'blogs':
        fp = OUTPUT_DIR / f"{item_id}.json"
    elif data_type == 'dna':
        fp = DNA_DIR / f"{item_id}.json"
    elif data_type == 'business':
        fp = BUSINESS_DIR / f"{item_id}.json"
    elif data_type == 'personas':
        fp = PERSONA_DIR / f"{item_id}.json"
    else:
        return jsonify({"error": "지원되지 않는 데이터 유형입니다."}), 400

    if not fp.exists():
        return jsonify({"error": "파일을 찾을 수 없습니다."}), 404

    with open(fp, 'r', encoding='utf-8') as f:
        content_data = json.load(f)

    # Google Docs 문서 내용 구성
    doc_title, doc_body = _build_doc_content(data_type, content_data, item_id)

    # 1) Google Docs 문서 생성
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    create_resp = http_requests.post(
        'https://docs.googleapis.com/v1/documents',
        headers=headers,
        json={'title': doc_title}
    )

    if create_resp.status_code == 401:
        session.pop('google_token', None)
        return jsonify({"error": "토큰이 만료되었습니다. 다시 로그인해주세요."}), 401

    if create_resp.status_code != 200:
        return jsonify({"error": f"Google Docs 생성 실패: {create_resp.text}"}), 500

    doc = create_resp.json()
    doc_id = doc['documentId']
    doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"

    # 2) 문서에 내용 삽입
    update_resp = http_requests.post(
        f'https://docs.googleapis.com/v1/documents/{doc_id}:batchUpdate',
        headers=headers,
        json={'requests': doc_body}
    )

    if update_resp.status_code != 200:
        print(f"[WARN] Google Docs 내용 입력 실패: {update_resp.text}")

    return jsonify({
        "success": True,
        "doc_url": doc_url,
        "doc_id": doc_id,
        "message": "Google Docs에 내보내기 완료!"
    })


def _build_doc_content(data_type, data, item_id):
    """데이터 유형별 Google Docs 내용 생성"""
    requests_list = []
    idx = 1  # 커서 위치 (1-indexed)

    if data_type == 'blogs':
        title = data.get('title', item_id)
        doc_title = f"[블로그] {title}"

        versions = data.get('versions', [])
        for v in versions:
            ver_label = v.get('version_label', v.get('version_type', ''))
            ver_title = v.get('title', '')
            ver_content = v.get('content', '')
            tags = v.get('tags', [])

            # 버전 라벨
            header = f"\n{'='*40}\n{ver_label} 버전\n{'='*40}\n\n"
            requests_list.append({
                'insertText': {'location': {'index': idx}, 'text': header}
            })
            idx += len(header)

            # 제목
            title_text = f"제목: {ver_title}\n\n"
            requests_list.append({
                'insertText': {'location': {'index': idx}, 'text': title_text}
            })
            idx += len(title_text)

            # 태그
            if tags:
                tags_text = f"태그: {', '.join(tags)}\n\n"
                requests_list.append({
                    'insertText': {'location': {'index': idx}, 'text': tags_text}
                })
                idx += len(tags_text)

            # 본문
            body_text = f"{ver_content}\n\n"
            requests_list.append({
                'insertText': {'location': {'index': idx}, 'text': body_text}
            })
            idx += len(body_text)

    elif data_type == 'dna':
        doc_title = f"[DNA 분석] {data.get('blog_id', item_id)}"
        text = json.dumps(data, ensure_ascii=False, indent=2)
        requests_list.append({
            'insertText': {'location': {'index': idx}, 'text': text}
        })

    elif data_type == 'business':
        bp = data.get('business_personality', {})
        doc_title = f"[업무성격] {bp.get('type', item_id)}"
        text = json.dumps(data, ensure_ascii=False, indent=2)
        requests_list.append({
            'insertText': {'location': {'index': idx}, 'text': text}
        })

    elif data_type == 'personas':
        doc_title = f"[페르소나] {data.get('client_name', data.get('client_id', item_id))}"
        text = json.dumps(data, ensure_ascii=False, indent=2)
        requests_list.append({
            'insertText': {'location': {'index': idx}, 'text': text}
        })

    else:
        doc_title = f"내보내기 - {item_id}"
        text = json.dumps(data, ensure_ascii=False, indent=2)
        requests_list.append({
            'insertText': {'location': {'index': idx}, 'text': text}
        })

    return doc_title, requests_list


# ============================================================
# Run Server
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("  페르소나 도구 웹 대시보드")
    print("=" * 60)
    print(f"  서버: http://localhost:5050")
    print(f"  페르소나 폴더: {PERSONA_DIR}")
    print(f"  출력 폴더: {OUTPUT_DIR}")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5050, debug=True)

