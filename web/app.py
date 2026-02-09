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
if config_path.exists() and not os.getenv("GEMINI_API_KEY"):
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
        api_key = config.get("mcpServers", {}).get("persona-manager", {}).get("env", {}).get("GEMINI_API_KEY")
        if api_key:
            os.environ["GEMINI_API_KEY"] = api_key

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
        access_token_url='https://oauth2.googleapis.com/token',
        authorize_url='https://accounts.google.com/o/oauth2/auth',
        api_base_url='https://www.googleapis.com/oauth2/v1/',
        client_kwargs={'scope': 'openid email profile'},
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
        user_info = google.get('userinfo').json()
        
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
def generate_blog():
    """페르소나 기반 블로그 글 생성 (파일 업로드 지원)"""
    
    client_id = request.form.get("client_id", "")
    keywords_str = request.form.get("keywords", "")
    keywords = [k.strip() for k in keywords_str.split(",") if k.strip()]
    
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
        
        blog_prompt = f"""
당신은 '{client_name}'의 페르소나에 맞춰 블로그 글을 작성하는 전문가입니다.

【페르소나 정보】
{custom_prompt}

【격식도】
{formality_score}/10

【적극 활용】
{json.dumps(green_flags, ensure_ascii=False)}

【금지 사항】
{json.dumps(red_flags, ensure_ascii=False)}

【보도자료】
{press_release[:5000]}

【타겟 키워드】
{keywords_text}

【작성 지침】
1. 위 페르소나의 톤과 스타일을 100% 반영하세요.
2. SEO 최적화된 제목 (60자 이내)
3. 본문 1,500~2,000자 분량
4. 마크다운 형식 사용

【출력 JSON】
반드시 아래 형식으로만 출력하세요:
{{
    "title": "블로그 제목",
    "content": "마크다운 형식 본문",
    "tags": ["태그1", "태그2", "태그3", "태그4", "태그5"],
    "meta_description": "155자 이내 요약"
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
        
        blog_content = json.loads(response_text.strip())
        
        output_id = f"BLOG_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        md_path = OUTPUT_DIR / f"{output_id}.md"
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(f"# {blog_content['title']}\n\n")
            f.write(f"{blog_content['content']}\n\n")
            f.write(f"**태그:** {', '.join(blog_content['tags'])}\n")
        
        json_path = OUTPUT_DIR / f"{output_id}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump({
                "output_id": output_id,
                "client_id": client_id,
                "content": blog_content,
                "created_at": datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            "success": True,
            "title": blog_content.get("title", ""),
            "content": blog_content.get("content", ""),
            "tags": blog_content.get("tags", []),
            "meta_description": blog_content.get("meta_description", ""),
            "md_path": str(md_path),
            "docx_path": str(OUTPUT_DIR / f"{output_id}.docx")
        })
        
    except Exception as e:
        return jsonify({"error": f"블로그 생성 실패: {str(e)}"}), 500


# ============================================================
# API: Match Rate Tester
# ============================================================

@app.route('/api/match-test', methods=['POST'])
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
# Run Server
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("  페르소나 도구 웹 대시보드")
    print("=" * 60)
    print(f"  서버: http://localhost:5000")
    print(f"  페르소나 폴더: {PERSONA_DIR}")
    print(f"  출력 폴더: {OUTPUT_DIR}")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5000, debug=True)
