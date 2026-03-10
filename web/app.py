#!/usr/bin/env python3
"""
블로그 자동화 도구 웹 대시보드 - Flask 백엔드
사용법: python app.py
"""

import sys
import os
import json
import io
import tempfile
import truststore
truststore.inject_into_ssl()
from pathlib import Path
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, session, redirect, url_for
from flask_cors import CORS
from authlib.integrations.flask_client import OAuth
from functools import wraps
import pdfplumber
import requests as http_requests
import docx
import fitz  # PyMuPDF
import re

# Windows 터미널 UTF-8 출력 설정
if sys.platform == 'win32' and not isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 프로젝트 루트 설정
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 환경 변수 로드
from dotenv import load_dotenv
load_dotenv()

# mcp_config.json에서 API 키 로드
config_path = PROJECT_ROOT / "mcp_config.json"
if config_path.exists():
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
        for _section in config.get("mcpServers", {}).values():
            env_config = _section.get("env", {})
            if not os.getenv("GEMINI_API_KEY") and env_config.get("GEMINI_API_KEY"):
                os.environ["GEMINI_API_KEY"] = env_config["GEMINI_API_KEY"]
            if not os.getenv("UNSPLASH_ACCESS_KEY") and env_config.get("UNSPLASH_ACCESS_KEY"):
                os.environ["UNSPLASH_ACCESS_KEY"] = env_config["UNSPLASH_ACCESS_KEY"]

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
        authorize_url='https://accounts.google.com/o/oauth2/v2/auth',
        access_token_url='https://oauth2.googleapis.com/token',
        jwks_uri='https://www.googleapis.com/oauth2/v3/certs',
        userinfo_endpoint='https://openidconnect.googleapis.com/v1/userinfo',
        client_kwargs={
            'scope': 'openid email profile https://www.googleapis.com/auth/documents',
        },
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

# 스타일 템플릿 로드
_STYLE_TEMPLATES_PATH = Path(__file__).parent / "style_templates.json"
with open(_STYLE_TEMPLATES_PATH, 'r', encoding='utf-8') as _f:
    STYLE_TEMPLATES: list[dict] = json.load(_f)
_STYLE_TEMPLATES_MAP: dict[str, dict] = {t["id"]: t for t in STYLE_TEMPLATES}

# Google Gemini API 클라이언트
from google import genai

def _strip_markdown(text: str) -> str:
    """블로그 본문에서 마크다운 기호를 모두 제거"""
    import re as _re
    # ** bold **, __bold__
    text = _re.sub(r'\*{1,3}(.*?)\*{1,3}', r'\1', text)
    text = _re.sub(r'_{1,2}(.*?)_{1,2}', r'\1', text)
    # ## 헤딩
    text = _re.sub(r'^#{1,6}\s+', '', text, flags=_re.MULTILINE)
    # ``` 코드블록
    text = _re.sub(r'```.*?```', '', text, flags=_re.DOTALL)
    text = _re.sub(r'`([^`]*)`', r'\1', text)
    # <태그>
    text = _re.sub(r'<[^>]+>', '', text)
    # --- === 구분선
    text = _re.sub(r'^[-=]{3,}\s*$', '', text, flags=_re.MULTILINE)
    # > 인용
    text = _re.sub(r'^>\s+', '', text, flags=_re.MULTILINE)
    return text.strip()


def parse_ai_json(text):
    """AI 응답에서 JSON을 안전하게 추출 및 파싱"""
    if not text:
        return {}
    
    # 1. 마크다운 코드 블록 제거
    if "```json" in text:
        text = text.split("```json")[-1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[-1].split("```")[0]
    
    text = text.strip()
    
    try:
        # 2. 일반적인 파싱 시도
        return json.loads(text)
    except json.JSONDecodeError:
        # 3. 이스케이프 문자 등 정제 후 재시도
        # 제어 문자 및 잘못된 백슬래시 처리
        # (단일 백슬래시가 줄을 깨는 경우가 많음)
        # JSON 문자열 내의 단일 \를 \\로 변경하려고 시도 (매우 조심스럽게)
        # 단, 이미 정당한 이스케이프(\", \\, \/, \b, \f, \n, \r, \t, \uXXXX)는 보존해야 함
        
        # 간단한 정제: 불필요한 제어 문자 제거 (strict=False로도 어느 정도 해결됨)
        try:
            return json.loads(text, strict=False)
        except json.JSONDecodeError as e:
            # 마지막 수단: 텍스트를 더 공격적으로 정제
            # 예: "content": "blah \n blah" -> "content": "blah \\n blah"
            # 하지만 이미 json.loads(strict=False)가 \n 등은 어느 정도 허용함.
            # 문제는 문법에 어긋나는 \ 하나임.
            # 정규식으로 유효하지 않은 \를 찾아 \\로 변환 (lookahead 사용)
            # 유효한 이스케이프 시퀀스가 아닌 \ 를 찾아냄
            cleaned = re.sub(r'\\(?![/"\\bfnrtu])', r'\\\\', text)
            try:
                return json.loads(cleaned, strict=False)
            except:
                print(f"[CRITICAL] JSON 파싱 최종 실패: {e}")
                raise


# ============================================================
# File Text Extraction — [M-5] utils.py로 통합, 여기서는 re-export
# ============================================================
from utils import extract_text_from_file  # noqa: F401
from blog_storage import (
    build_blog_package,
    ensure_blog_package_shape,
    load_blog_package,
    save_blog_package,
    update_blog_package_version,
)
from material_pipeline import build_material_bundle, build_material_bundle_from_paths
from offline_engines import generate_blog_versions_offline


def save_uploaded_file(file) -> Path:
    """업로드된 파일을 임시 저장"""
    ext = Path(file.filename).suffix.lower()
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    file.save(temp_file.name)
    return Path(temp_file.name)


def upload_to_gemini(path: Path, client: genai.Client):
    """Gemini File API에 파일 업로드 (PDF / 이미지 네이티브 지원)"""
    MIME_MAP = {
        '.pdf':  'application/pdf',
        '.jpg':  'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png':  'image/png',
        '.gif':  'image/gif',
        '.webp': 'image/webp',
    }
    ext = path.suffix.lower()
    mime_type = MIME_MAP.get(ext)
    if not mime_type:
        print(f"[INFO] {ext} → 텍스트 추출 방식 사용")
        return None
    try:
        from google.genai import types as _gtypes
        gfile = client.files.upload(
            file=str(path),
            config=_gtypes.UploadFileConfig(mime_type=mime_type),
        )
        print(f"[OK] Gemini 파일 업로드: {path.name} → {gfile.name}")
        return gfile
    except Exception as e:
        print(f"[WARN] Gemini 파일 업로드 실패 ({path.name}): {e}")
        return None


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
    # access_type=offline → refresh_token 발급, prompt=consent → 재로그인 시에도 refresh_token 재발급
    return google.authorize_redirect(redirect_uri, access_type='offline', prompt='consent')


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
        # Google API 호출을 위한 액세스 토큰 + 갱신 토큰 저장
        import time as _time
        session['google_token'] = token.get('access_token', '')
        session['google_refresh_token'] = token.get('refresh_token', '')
        session['google_token_expires_at'] = _time.time() + token.get('expires_in', 3600)
        
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
    resp = send_from_directory('.', filename)
    if filename in ('app.js', 'style.css', 'index.html'):
        resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        resp.headers['Pragma'] = 'no-cache'
    return resp


# ============================================================
# API: Style Templates
# ============================================================

@app.route('/api/style-templates', methods=['GET'])
def get_style_templates():
    """10가지 블로그 스타일 템플릿 목록 반환"""
    return jsonify({"templates": STYLE_TEMPLATES})


# 페르소나 기능은 C:\work\email-persona 프로젝트로 이전됨

@app.route('/api/persona/list', methods=['GET'])
@login_required
def list_personas():
    """[이전됨] 페르소나 목록 — 항상 빈 목록 반환 (email-persona 프로젝트로 이전)"""
    return jsonify({"personas": []})


@app.route('/api/persona/get', methods=['GET'])
@login_required
def get_persona():
    return jsonify({"error": "페르소나 기능은 이메일 도구로 이전되었습니다."}), 410


@app.route('/api/persona/extract', methods=['POST'])
@login_required
def extract_persona():
    return jsonify({"error": "페르소나 기능은 이메일 도구로 이전되었습니다."}), 410




# ============================================================
# API: Blog Generator
# ============================================================

@app.route('/api/blog/dna-preview', methods=['GET'])
@login_required
def blog_dna_preview():
    """DNA 분석 결과 미리보기 — 모방 스타일 가이드 + 샘플 글 반환"""
    blog_id = request.args.get("blog_id", "")
    if not blog_id:
        return jsonify({"error": "blog_id 필요"}), 400

    dna_analysis = None
    if DNA_DIR.exists():
        candidates = sorted(
            [f for f in DNA_DIR.glob(f"DNA_{blog_id}_*.json")],
            key=lambda f: f.stat().st_mtime, reverse=True
        )
        if candidates:
            with open(candidates[0], 'r', encoding='utf-8') as f:
                dna_analysis = json.load(f)

    # 원본 글 샘플 1개 로드
    sample_post = None
    if BLOG_COLLECTIONS_DIR.exists():
        all_posts = []
        for item in BLOG_COLLECTIONS_DIR.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                data_file = item / "_data.json"
                if data_file.exists():
                    try:
                        with open(data_file, 'r', encoding='utf-8') as f:
                            col = json.load(f)
                        if col.get("blog_id") == blog_id:
                            all_posts.extend(col.get("posts", []))
                    except Exception:
                        pass
        all_posts.sort(key=lambda x: x.get('addDate', ''), reverse=True)
        seen = set()
        for p in all_posts:
            if p.get("url") not in seen:
                seen.add(p.get("url"))
                if p.get("content", "").strip():
                    sample_post = p
                    break

    if not dna_analysis and not sample_post:
        return jsonify({"error": "DNA 분석 결과 없음. 먼저 글쓰기 DNA 분석을 실행하세요."}), 404

    # 미리보기 텍스트 구성
    lines = []
    if dna_analysis:
        c1 = dna_analysis.get("c1_template_structure", {})
        c2 = dna_analysis.get("c2_tone_mood", {})
        c3 = dna_analysis.get("c3_speech_style", {})
        c5 = dna_analysis.get("c5_frequent_expressions", {})
        c6 = dna_analysis.get("c6_sentence_patterns", {})
        c9 = dna_analysis.get("c9_opening_closing", {})
        c10 = dna_analysis.get("c10_visual_formatting", {})

        lines.append("▌ 글 구조 패턴")
        lines.append(f"  {c1.get('overall_pattern', '-')}")
        if c1.get('section_flow'):
            lines.append("  흐름: " + " → ".join(c1['section_flow'])[:120])

        lines.append("")
        lines.append("▌ 톤 & 어투")
        lines.append(f"  톤: {c2.get('primary_tone', '-')}  /  격식도: {c2.get('formality_level', '-')}/10")
        lines.append(f"  종결어미: {', '.join(c3.get('ending_patterns', []))}")
        lines.append(f"  독자 호칭: {c3.get('reader_address', '-')}")

        lines.append("")
        lines.append("▌ 이모지 & 특수기호")
        emoji_list = ', '.join(c10.get('emoji_types', []))
        lines.append(f"  이모지({c10.get('emoji_usage', '-')}/10): {emoji_list}")
        special = c10.get('special_symbols', c10.get('special_formatting', []))
        if special:
            lines.append(f"  특수기호: {', '.join(special)}")

        lines.append("")
        lines.append("▌ 시각적 포맷팅 (HTML 분석)")
        lines.append(f"  중앙정렬: {c10.get('center_align', '-')}")
        lines.append(f"  폰트: {c10.get('font_family', '-')} / 크기: {c10.get('font_size_pattern', '-')}")
        lines.append(f"  볼드 패턴: {c10.get('bold_pattern', '-')}")
        lines.append(f"  이탤릭: {c10.get('italic_usage', '-')}")
        lines.append(f"  인용/꺽쇠: {c10.get('quote_style', '-')}")
        lines.append(f"  괄호 사용: {c10.get('bracket_usage', '-')}")
        lines.append(f"  줄바꿈: {c10.get('line_break_style', '-')}")
        if c10.get('text_colors'):
            lines.append(f"  강조 색상: {', '.join(c10['text_colors'][:4])}")
        if c10.get('highlight_colors'):
            lines.append(f"  하이라이트: {', '.join(c10['highlight_colors'][:3])}")
        if c10.get('writing_guide'):
            lines.append(f"\n  작성 가이드: {c10['writing_guide']}")

        lines.append("")
        lines.append("▌ 시그니처 표현")
        for phrase in c5.get('signature_phrases', [])[:6]:
            lines.append(f"  • {phrase}")

        lines.append("")
        lines.append("▌ 도입부 예시")
        for ex in c9.get('opening_examples', [])[:2]:
            lines.append(f"  {ex}")

        lines.append("")
        lines.append("▌ 마무리 예시")
        for ex in c9.get('closing_examples', [])[:2]:
            lines.append(f"  {ex}")

    if sample_post:
        lines.append("")
        lines.append("━" * 36)
        lines.append(f"▌ 실제 글 샘플 (AI가 모방하는 글)")
        lines.append(f"  제목: {sample_post.get('title', '')}")
        lines.append(f"  날짜: {sample_post.get('addDate', '')}")
        lines.append("")
        lines.append(sample_post.get('content', '')[:1800])

    # c10 시각 스타일 → JS가 HTML 변환에 쓸 구조화 데이터
    dna_styles = {}
    if dna_analysis:
        c10 = dna_analysis.get("c10_visual_formatting", {})
        # 폰트 패밀리 (Naver CSS font-family 값)
        raw_font = c10.get("font_family", "")
        font_map = {
            "나눔마루부리": "NanumMyeongjo, '나눔마루부리', serif",
            "나눔고딕": "'나눔고딕', NanumGothic, sans-serif",
            "나눔명조": "NanumMyeongjo, '나눔명조', serif",
            "맑은 고딕": "'맑은 고딕', MalgunGothic, sans-serif",
            "돋움": "Dotum, '돋움', sans-serif",
            "굴림": "Gulim, '굴림', sans-serif",
        }
        css_font = font_map.get(raw_font, font_map.get(raw_font.split()[0], "'맑은 고딕', sans-serif"))

        # 중앙정렬 비율 파싱 (숫자 or "57%" 형태 모두 처리)
        center_raw = c10.get("center_align", "0")
        try:
            center_val = float(str(center_raw).replace("%", "").strip())
            if center_val > 1:
                center_val = center_val / 100
        except Exception:
            center_val = 0.0

        # 강조 색상 (첫번째 유효색)
        text_colors = c10.get("text_colors", [])
        accent_color = text_colors[0] if text_colors else ""
        highlight_colors = c10.get("highlight_colors", [])
        highlight_color = highlight_colors[0] if highlight_colors else ""

        dna_styles = {
            "font_family": css_font,
            "center_align_ratio": center_val,
            "accent_color": accent_color,
            "highlight_color": highlight_color,
            "has_italic": bool(c10.get("italic_usage", "")),
            "has_quote": bool(c10.get("quote_style", "")),
            "font_size_body": "11pt",
            "font_size_heading": "14pt",
        }

    return jsonify({
        "blog_id": blog_id,
        "preview_text": "\n".join(lines),
        "has_dna_analysis": dna_analysis is not None,
        "sample_title": sample_post.get("title", "") if sample_post else "",
        "dna_styles": dna_styles,
    })


@app.route('/api/blog/generate', methods=['POST'])
@login_required
def generate_blog():
    """스타일 템플릿 기반 블로그 글 생성 (통합 DNA 데이터 지원)"""
    style_template_id = request.form.get("style_template_id", "informational")
    keywords_str = request.form.get("keywords", "")
    keywords = [k.strip() for k in keywords_str.split(",") if k.strip()]
    blog_dna_id = request.form.get("blog_dna_id", "")
    target_audience = request.form.get("target_audience", "일반 독자")
    content_angle = request.form.get("content_angle", "정보전달형")
    direct_text = request.form.get("press_release", "")

    uploaded_files = [file for file in request.files.getlist("files") if file and file.filename]
    if not uploaded_files and 'file' in request.files and request.files['file'].filename:
        uploaded_files = [request.files['file']]

    # Gemini가 네이티브로 읽을 수 있는 형식
    GEMINI_NATIVE_EXTS = {'.pdf', '.jpg', '.jpeg', '.png', '.gif', '.webp'}

    temp_paths = []
    gemini_uploaded_files = []   # Gemini File API 업로드 객체
    text_sources = []            # 로컬 텍스트 추출 결과

    api_key = os.getenv("GEMINI_API_KEY")
    _gemini_client = genai.Client(api_key=api_key) if api_key else None

    try:
        for file in uploaded_files:
            temp_path = save_uploaded_file(file)
            temp_paths.append(temp_path)
            ext = temp_path.suffix.lower()

            if ext in GEMINI_NATIVE_EXTS and _gemini_client:
                # Gemini File API로 직접 업로드
                gfile = upload_to_gemini(temp_path, _gemini_client)
                if gfile:
                    gemini_uploaded_files.append(gfile)
                    print(f"[OK] Gemini 네이티브 처리: {file.filename}")
                else:
                    # 업로드 실패 시 텍스트 추출로 폴백
                    try:
                        text = extract_text_from_file(temp_path)
                        text_sources.append({
                            "name": file.filename,
                            "kind": ext.lstrip("."),
                            "text": text,
                        })
                    except Exception:
                        pass
            else:
                # DOCX / HWP / TXT → 로컬 텍스트 추출
                try:
                    text = extract_text_from_file(temp_path)
                    text_sources.append({
                        "name": file.filename,
                        "kind": ext.lstrip("."),
                        "text": text,
                    })
                except Exception as ex:
                    print(f"[WARN] 텍스트 추출 실패 ({file.filename}): {ex}")

        material_bundle = build_material_bundle(sources=text_sources, direct_text=direct_text)

    except Exception as e:
        return jsonify({"error": f"파일 처리 실패: {str(e)}"}), 500
    finally:
        for temp_path in temp_paths:
            try:
                if temp_path.exists():
                    temp_path.unlink()
            except Exception:
                pass

    if not uploaded_files:
        material_bundle = build_material_bundle(direct_text=direct_text)

    has_content = material_bundle.get("combined_text", "").strip() or bool(gemini_uploaded_files)
    if not has_content:
        return jsonify({"error": "보도자료 내용이 필요합니다."}), 400

    # 스타일 템플릿 로드
    style_template = _STYLE_TEMPLATES_MAP.get(style_template_id, STYLE_TEMPLATES[0])

    blog_dna_text = ""
    if blog_dna_id:
        try:
            # ① DNA 분석 결과 (스타일 가이드) 로드
            dna_analysis = None
            if DNA_DIR.exists():
                # blog_dna_id와 blog_id가 매칭되는 가장 최근 DNA 분석 결과 찾기
                candidates = sorted(
                    [f for f in DNA_DIR.glob(f"DNA_{blog_dna_id}_*.json")],
                    key=lambda f: f.stat().st_mtime, reverse=True
                )
                if candidates:
                    with open(candidates[0], 'r', encoding='utf-8') as f:
                        dna_analysis = json.load(f)

            # ② 원본 글 샘플 로드 (전문 1개 + 제목 목록)
            all_dna_posts = []
            if BLOG_COLLECTIONS_DIR.exists():
                for item in BLOG_COLLECTIONS_DIR.iterdir():
                    if item.is_dir() and not item.name.startswith('.'):
                        data_file = item / "_data.json"
                        if data_file.exists():
                            try:
                                with open(data_file, 'r', encoding='utf-8') as f:
                                    collection = json.load(f)
                                if collection.get("blog_id") == blog_dna_id:
                                    all_dna_posts.extend(collection.get("posts", []))
                            except Exception:
                                pass

            seen_urls = set()
            unique_posts = []
            for post in all_dna_posts:
                url = post.get("url")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    unique_posts.append(post)
            unique_posts.sort(key=lambda x: x.get('addDate', ''), reverse=True)

            # ③ DNA 스타일 가이드 + 샘플 글 조합
            dna_parts = []

            if dna_analysis:
                c1 = dna_analysis.get("c1_template_structure", {})
                c2 = dna_analysis.get("c2_tone_mood", {})
                c3 = dna_analysis.get("c3_speech_style", {})
                c5 = dna_analysis.get("c5_frequent_expressions", {})
                c6 = dna_analysis.get("c6_sentence_patterns", {})
                c9 = dna_analysis.get("c9_opening_closing", {})
                c10 = dna_analysis.get("c10_visual_formatting", {})

                dna_parts.append("【블로그 글쓰기 DNA 스타일 가이드】")
                dna_parts.append(f"구조 패턴: {c1.get('overall_pattern', '')}")
                dna_parts.append(f"섹션 흐름: {' → '.join(c1.get('section_flow', []))}")
                dna_parts.append(f"톤: {c2.get('primary_tone', '')} / 격식도: {c2.get('formality_level', '')}/10")
                dna_parts.append(f"종결어미 패턴: {', '.join(c3.get('ending_patterns', []))}")
                dna_parts.append(f"독자 호칭: {c3.get('reader_address', '')}")
                dna_parts.append(f"시그니처 표현: {', '.join(c5.get('signature_phrases', [])[:5])}")
                dna_parts.append(f"문장 길이: {c6.get('avg_length', '')} / 리듬: {c6.get('rhythm', '')}")
                dna_parts.append(f"도입 방식: {', '.join(c9.get('opening_types', []))}")
                dna_parts.append(f"마무리 방식: {', '.join(c9.get('closing_types', []))}")
                dna_parts.append(f"이모지 사용(1-10): {c10.get('emoji_usage', '')} / 자주 쓰는 이모지: {', '.join(c10.get('emoji_types', []))}")
                dna_parts.append(f"특수 포맷팅: {', '.join(c10.get('special_formatting', []))}")

                # 도입/마무리 실제 예시
                if c9.get("opening_examples"):
                    dna_parts.append(f"\n실제 도입부 예시:\n" + "\n".join(c9["opening_examples"][:2]))
                if c9.get("closing_examples"):
                    dna_parts.append(f"\n실제 마무리 예시:\n" + "\n".join(c9["closing_examples"][:2]))

            # 원본 글 전문 1개 (가장 최근 글)
            if unique_posts:
                full_sample = unique_posts[0]
                dna_parts.append(f"\n【실제 글 전문 샘플 (이 스타일을 그대로 따라쓸 것)】")
                dna_parts.append(f"제목: {full_sample.get('title', '')}")
                dna_parts.append(full_sample.get('content', '')[:2000])

                # 제목 목록 (참고용)
                title_list = [f"- {p.get('title', '')}" for p in unique_posts[1:8]]
                if title_list:
                    dna_parts.append(f"\n【최근 글 제목 목록 (주제 참고용)】\n" + "\n".join(title_list))

            blog_dna_text = "\n".join(dna_parts)

        except Exception as e:
            print(f"[WARN] 블로그 DNA 로드 실패: {e}")

    template_name = style_template.get("name", "정보전달형")
    formality_score = style_template.get("formality_score", 5)
    custom_prompt = style_template.get("custom_prompt", "")

    api_key = os.getenv("GEMINI_API_KEY")
    generation_mode = "offline"
    versions = []

    if api_key:
        try:
            client = genai.Client(api_key=api_key)

            # Gemini 네이티브 파일 처리 대기 (PROCESSING → ACTIVE)
            active_gfiles = []
            for gf in gemini_uploaded_files:
                for _ in range(30):
                    if gf.state.name == 'ACTIVE':
                        active_gfiles.append(gf)
                        break
                    _time.sleep(1)
                    gf = client.files.get(name=gf.name)
                else:
                    print(f"[WARN] Gemini 파일 처리 타임아웃: {gf.name}")

            # 파일 첨부 안내 문구
            native_note = ""
            if active_gfiles:
                native_note = f"첨부된 파일 {len(active_gfiles)}개를 직접 읽고 핵심 내용을 파악하세요."

            prompt = f"""당신은 실전형 블로그 콘텐츠 에디터입니다.
아래 스타일 가이드와 자료를 바탕으로 3가지 버전의 블로그 글을 만드세요.
반드시 JSON만 출력하세요.

[글쓰기 스타일 템플릿: {template_name}]
- 격식도: {formality_score}/10
- 종결어미: {', '.join(style_template.get('ending_patterns', []))}
{custom_prompt}

[블로그 DNA — 반드시 이 스타일로 작성]
{blog_dna_text or '선택 안 함 (일반 블로그 스타일로 작성)'}

[DNA 스타일 준수 규칙]
- 위 DNA 가이드의 이모지, 특수기호(✅ 〰️ ➡️ 등), 종결어미, 도입/마무리 패턴을 그대로 사용
- 실제 글 전문 샘플이 있다면 그 스타일을 최대한 모방
- 줄바꿈 패턴, 문장 길이, 단락 구성도 샘플과 유사하게

[첨부 파일 안내]
{native_note or '없음'}

[추가 텍스트 자료]
{material_bundle.get('briefing', '')[:8000] or '없음'}

[타겟 독자]
{target_audience}

[콘텐츠 앵글]
{content_angle}

[키워드]
{", ".join(keywords) if keywords else "없음"}

[글 길이 요구사항 — 반드시 준수]
- 각 버전 본문은 최소 1,500자 이상, 권장 2,000~3,000자
- 서론(흥미 유발) → 본론(핵심 내용 3~5개 단락) → 결론(행동 유도) 구조 필수
- 각 단락은 3~6문장 이상으로 충분히 풀어서 작성
- 정보를 압축하지 말고 독자가 이해하기 쉽게 상세히 설명

[절대 금지 규칙 — 반드시 준수]
- 제목과 본문에 작성자 실명 노출 금지
- ** ** (별표 볼드) 절대 사용 금지
- ## # (샵 헤딩) 절대 사용 금지
- __ __ (언더스코어 볼드/이탤릭) 절대 사용 금지
- ``` (백틱 코드블록) 절대 사용 금지
- <> 꺽쇠괄호 절대 사용 금지
- --- === (구분선) 절대 사용 금지
- 마크다운 기호 전체 사용 금지 — 순수 텍스트만 출력
- 각 버전은 구조와 어조가 분명히 달라야 함
- 핵심 일정/대상/혜택/문의 정보를 가능한 한 놓치지 말 것

[출력 JSON]
{{
  "versions": [
    {{"version_type":"formal","version_label":"포멀","title":"제목","content":"본문","tags":["태그"],"meta_description":"설명"}},
    {{"version_type":"balanced","version_label":"밸런스","title":"제목","content":"본문","tags":["태그"],"meta_description":"설명"}},
    {{"version_type":"casual","version_label":"캐주얼","title":"제목","content":"본문","tags":["태그"],"meta_description":"설명"}}
  ]
}}"""

            # 멀티모달 contents: 텍스트 프롬프트 + 네이티브 파일 객체들
            from google.genai import types as _gtypes
            contents = [_gtypes.Part.from_text(text=prompt)]
            for gf in active_gfiles:
                contents.append(_gtypes.Part.from_uri(
                    file_uri=gf.uri,
                    mime_type=gf.mime_type,
                ))

            from google.genai import types as _cfg_types
            response = client.models.generate_content(
                model='gemini-2.5-pro',
                contents=contents,
                config=_cfg_types.GenerateContentConfig(
                    max_output_tokens=8192,
                    temperature=0.8,
                ),
            )

            # Gemini 업로드 파일 사용 후 삭제 (48시간 자동 만료지만 즉시 정리)
            for gf in active_gfiles:
                try:
                    client.files.delete(name=gf.name)
                except Exception:
                    pass
            blog_result = parse_ai_json(response.text)
            versions = blog_result.get("versions", [])
            for v in versions:
                if "content" in v:
                    v["content"] = _strip_markdown(v["content"])
                if "title" in v:
                    v["title"] = _strip_markdown(v["title"])
            if versions:
                generation_mode = "ai"
        except Exception as e:
            print(f"[WARN] AI 블로그 생성 실패, 오프라인 모드로 전환: {e}")

    if not versions:
        versions = generate_blog_versions_offline(
            persona_data=persona_data,
            material_bundle=material_bundle,
            keywords=keywords,
            target_audience=target_audience,
            content_angle=content_angle,
        )

    output_id = f"BLOG_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    package = build_blog_package(
        output_id=output_id,
        client_id=style_template_id,
        client_name=template_name,
        versions=versions,
        source_bundle=material_bundle,
        extra={"generation_mode": generation_mode, "style_template_id": style_template_id},
    )
    save_blog_package(package, OUTPUT_DIR)

    return jsonify({
        "success": True,
        "versions": package.get("versions", []),
        "output_id": output_id,
        "output_dir": str(OUTPUT_DIR),
        "generation_mode": generation_mode,
        "source_bundle": {
            "sources": material_bundle.get("sources", []),
            "warnings": material_bundle.get("warnings", []),
        },
    })


# ============================================================
# API: Blog Image Generation (On-Demand)
# ============================================================

@app.route('/api/blog/suggest-prompts', methods=['POST'])
@login_required
def suggest_blog_prompts():
    """블로그 본문 기반 이미지 생성 프롬프트 제안"""
    data = request.json
    blog_content = data.get("content", "")
    target_audience = data.get("target_audience", "일반 시민")
    content_angle = data.get("content_angle", "정보전달형")
    
    if not blog_content or not blog_content.strip():
        return jsonify({"error": "프롬프트 제안을 위한 블로그 본문이 필요합니다."}), 400
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return jsonify({"error": "GEMINI_API_KEY가 설정되지 않았습니다."}), 500
    
    try:
        client = genai.Client(api_key=api_key)
        from image_service import extract_image_prompts
        prompts = extract_image_prompts(blog_content, client, target_audience, content_angle)
        
        return jsonify({
            "success": True,
            "prompts": prompts
        })
    except Exception as e:
        return jsonify({"error": f"프롬프트 추출 실패: {str(e)}"}), 500


@app.route('/api/blog/generate-images', methods=['POST'])
@login_required
def generate_blog_images():
    """블로그 본문 또는 커스텀 프롬프트 기반 AI 이미지 생성 (On-Demand)"""
    data = request.json
    
    blog_content = data.get("content", "")
    target_audience = data.get("target_audience", "일반 시민")
    content_angle = data.get("content_angle", "정보전달형")
    custom_prompts = data.get("prompts", [])
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return jsonify({"error": "GEMINI_API_KEY가 설정되지 않았습니다."}), 500
    
    try:
        client = genai.Client(api_key=api_key)
        from image_service import generate_images_for_blog, generate_images
        
        if custom_prompts:
            # 사용자가 수정한 프롬프트로 생성
            images = generate_images(custom_prompts, client, OUTPUT_DIR)
        else:
            # 블로그 본문에서 자동 추출하여 생성 (기존 방식)
            if not blog_content or not blog_content.strip():
                return jsonify({"error": "이미지 생성을 위한 본문 또는 프롬프트가 필요합니다."}), 400
            images = generate_images_for_blog(blog_content, client, target_audience, content_angle, OUTPUT_DIR)
        
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
# API: Blog Save & Export
# ============================================================

@app.route('/api/blog/save', methods=['POST'])
@login_required
def save_blog():
    """편집된 블로그 글을 JSON 파일로 저장"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "데이터가 없습니다."}), 400
    
    title = data.get("title", "")
    content = data.get("content", "")
    version_type = data.get("version_type", "unknown")
    version_label = data.get("version_label", "")
    tags = data.get("tags", [])
    output_id = data.get("output_id", "")
    output_dir = data.get("output_dir", "")
    
    if not title or not content:
        return jsonify({"error": "제목과 본문을 입력해주세요."}), 400
    
    try:
        if output_dir and Path(output_dir).exists():
            save_dir = Path(output_dir)
        else:
            save_dir = OUTPUT_DIR

        if output_id:
            package, save_path = update_blog_package_version(
                output_dir=save_dir,
                output_id=output_id,
                version_type=version_type,
                updated_fields={
                    "title": title,
                    "content": content,
                    "tags": tags,
                    "meta_description": data.get("meta_description", ""),
                },
            )
        else:
            filename = f"edited_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            save_path = save_dir / filename
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "title": title,
                    "content": content,
                    "version_type": version_type,
                    "version_label": version_label,
                    "tags": tags,
                    "edited_at": datetime.now().isoformat(),
                    "is_edited": True,
                }, f, ensure_ascii=False, indent=2)

        return jsonify({
            "success": True,
            "saved_path": str(save_path),
            "filename": Path(save_path).name
        })
    except Exception as e:
        return jsonify({"error": f"저장 실패: {str(e)}"}), 500


@app.route('/api/blog/export-docs', methods=['POST'])
@login_required
def export_blog_docs():
    """편집된 블로그 글을 DOCX 파일로 내보내기"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "데이터가 없습니다."}), 400
    
    title = data.get("title", "제목 없음")
    content = data.get("content", "")
    version_label = data.get("version_label", "")
    tags = data.get("tags", [])
    
    if not content:
        return jsonify({"error": "본문 내용이 없습니다."}), 400
    
    try:
        from docx.shared import Pt, Inches, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        
        doc = docx.Document()
        
        # 스타일 설정
        style = doc.styles['Normal']
        font = style.font
        font.name = '맑은 고딕'
        font.size = Pt(11)
        
        # 버전 라벨
        if version_label:
            label_para = doc.add_paragraph()
            label_run = label_para.add_run(f"[{version_label}]")
            label_run.font.size = Pt(9)
            label_run.font.color.rgb = RGBColor(128, 128, 128)
        
        # 제목
        heading = doc.add_heading(title, level=1)
        
        # 본문
        paragraphs = content.split('\n')
        for para_text in paragraphs:
            stripped = para_text.strip()
            if stripped:
                doc.add_paragraph(stripped)
        
        # 태그
        if tags:
            doc.add_paragraph()
            tag_para = doc.add_paragraph()
            tag_run = tag_para.add_run(' '.join(f'#{t}' for t in tags))
            tag_run.font.size = Pt(9)
            tag_run.font.color.rgb = RGBColor(100, 100, 100)
        
        # 메모리에 저장 후 전송
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        
        from flask import send_file
        safe_title = re.sub(r'[^\w가-힣\s]', '', title)[:30].strip() or 'blog'
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"{safe_title}.docx",
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
    except Exception as e:
        return jsonify({"error": f"DOCX 생성 실패: {str(e)}"}), 500


# ============================================================
# API: Blog Collection (blog_pull 통합)
# ============================================================

# ─── match-test 제거 (persona 의존) ─── 이하 생략됨

# ============================================================
# API: Blog Collection (blog_pull 통합)
# ============================================================

try:
    from run_crawler import get_blog_id, get_post_list, get_post_content, get_post_content_with_style, save_results
    import run_crawler as _run_crawler
    _run_crawler.OUTPUT_DIR = str(BLOG_COLLECTIONS_DIR)
    BLOG_PULL_AVAILABLE = True
except Exception as e:
    BLOG_PULL_AVAILABLE = False
    get_blog_id = get_post_list = get_post_content = get_post_content_with_style = save_results = None
    print(f"[WARN] blog_pull 크롤러를 불러오지 못했습니다: {e}")
import time as _time

@app.route('/api/blog/collect', methods=['POST'])
@login_required
def collect_blog():
    """네이버 블로그 글 수집 (blog_pull 크롤러 통합)"""
    if not BLOG_PULL_AVAILABLE:
        return jsonify({"error": "blog_pull 크롤러가 설치되지 않아 블로그 수집 기능을 사용할 수 없습니다."}), 503

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
        
        # STEP 2: 본문 + 스타일 메타 수집
        for post in posts:
            result = get_post_content_with_style(blog_id, post['logNo'])
            post['content'] = result.get('text') or "(본문 추출 실패)"
            post['style_meta'] = result.get('style_meta', {})
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
    """수집된 블로그 컬렉션 목록 (블로그 ID별 통합 버전)"""
    blog_map = {}
    
    if BLOG_COLLECTIONS_DIR.exists():
        # 날짜 내림차순 정렬 (최신 폴더 먼저)
        for item in sorted(BLOG_COLLECTIONS_DIR.iterdir(), reverse=True):
            if item.is_dir() and not item.name.startswith('.'):
                data_file = item / "_data.json"
                if data_file.exists():
                    try:
                        with open(data_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        blog_id = data.get("blog_id", "")
                        if not blog_id: continue
                        
                        posts = data.get("posts", [])
                        post_count = len(posts)
                        total_chars = sum(len(p.get("content", "")) for p in posts)
                        collected_at = data.get("collected_at", item.name)
                        
                        if blog_id not in blog_map:
                            blog_map[blog_id] = {
                                "blog_id": blog_id,
                                "folders": [item.name],
                                "post_count": post_count,
                                "total_chars": total_chars,
                                "last_collected_at": collected_at
                            }
                        else:
                            # 기존 데이터에 합치기 (Merging)
                            blog_map[blog_id]["folders"].append(item.name)
                            blog_map[blog_id]["post_count"] += post_count
                            blog_map[blog_id]["total_chars"] += total_chars
                            # (이미 날짜 역순 정렬이므로 처음 발견된 게 가장 최신일 가능성이 높음)
                    except:
                        pass
    
    # 결과를 리스트로 변환
    collections = list(blog_map.values())
    return jsonify({"collections": collections})


@app.route('/api/blog/analyze-status', methods=['POST'])
@login_required
def analyze_blog_status():
    """수집된 블로그 글을 AI로 분석하여 상태 파악 (모든 수집 데이터 통합 분석)"""
    data = request.json
    blog_id = data.get("blog_id", "")  # 이제 folder 대신 blog_id를 직접 받음
    
    if not blog_id:
        return jsonify({"error": "분석할 블로그 ID를 선택해주세요."}), 400
    
    all_posts = []
    
    # 해당 blog_id를 가진 모든 폴더 찾아서 데이터 합치기
    if BLOG_COLLECTIONS_DIR.exists():
        for item in BLOG_COLLECTIONS_DIR.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                data_file = item / "_data.json"
                if data_file.exists():
                    try:
                        with open(data_file, 'r', encoding='utf-8') as f:
                            collection = json.load(f)
                        if collection.get("blog_id") == blog_id:
                            all_posts.extend(collection.get("posts", []))
                    except:
                        pass
    
    if not all_posts:
        return jsonify({"error": f"'{blog_id}'에 대한 수집 데이터를 찾을 수 없습니다."}), 404
    
    # 중복 글 제거 (url 또는 logNo 기준)
    seen_urls = set()
    unique_posts = []
    for post in all_posts:
        url = post.get("url")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_posts.append(post)
    
    try:
        # 날짜순 정렬 (최신순)
        unique_posts.sort(key=lambda x: x.get('addDate', ''), reverse=True)
        
        # 블로그 글 요약 텍스트 생성 (통합된 데이터 중 최근 15개 분석)
        blog_summary = ""
        for i, post in enumerate(unique_posts[:15], 1):
            content = post.get("content", "")[:1500]
            blog_summary += f"\n\n--- 글 {i}: {post.get('title', '')} (날짜: {post.get('addDate', '')}) ---\n{content}"

        # 시각적 스타일 메타 집계 (HTML에서 추출한 데이터)
        from collections import Counter as _Counter
        style_metas = [p.get("style_meta", {}) for p in unique_posts if p.get("style_meta")]
        visual_summary = ""
        if style_metas:
            avg_center = round(sum(m.get("center_align_ratio", 0) for m in style_metas) / len(style_metas), 2)
            all_accent = [c for m in style_metas for c, _ in m.get("accent_colors", [])]
            all_highlight = [c for m in style_metas for c, _ in m.get("highlight_colors", [])]
            all_fonts = [f for m in style_metas for f in m.get("dominant_fonts", [])]
            all_sizes = [s for m in style_metas for s in m.get("font_sizes", [])]
            bold_total = sum(m.get("bold_count", 0) for m in style_metas)
            italic_total = sum(m.get("italic_count", 0) for m in style_metas)
            has_quote = any(m.get("has_quote_block") for m in style_metas)

            top_accents = _Counter(all_accent).most_common(5)
            top_highlights = _Counter(all_highlight).most_common(3)
            top_fonts = _Counter(all_fonts).most_common(3)
            top_sizes = _Counter(all_sizes).most_common(3)

            visual_summary = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【HTML 시각적 스타일 데이터 ({len(style_metas)}개 글 분석)】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
중앙정렬 비율: {avg_center*100:.0f}% ({"매우 자주 씀" if avg_center > 0.5 else "가끔 씀" if avg_center > 0.2 else "거의 안 씀"})
강조 색상(텍스트): {', '.join(f'{c}(x{n})' for c, n in top_accents) or '없음'}
강조 색상(배경/하이라이트): {', '.join(f'{c}(x{n})' for c, n in top_highlights) or '없음'}
사용 폰트: {', '.join(f for f, _ in top_fonts) or '기본 폰트'}
폰트 크기: {', '.join(s for s, _ in top_sizes) or '기본'}
볼드 사용 횟수: {bold_total}회
이탤릭 사용 횟수: {italic_total}회
인용구 블록 사용: {"있음" if has_quote else "없음"}
"""

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return jsonify({"error": "GEMINI_API_KEY가 설정되지 않았습니다."}), 500

        client = genai.Client(api_key=api_key)

        analysis_prompt = f"""당신은 블로그 글쓰기 DNA 분석 전문가입니다.
아래는 네이버 블로그 '{blog_id}'에서 수집한 최근 글들입니다.
이 블로그의 글쓰기 스타일, 구조, 어투, 화법, 표현 패턴을 아주 꼼꼼하게 분석해주세요.
모든 분석은 실제 글에서 발견된 패턴과 근거를 바탕으로 해야 합니다.

{blog_summary}
{visual_summary}

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
    "emoji_types": ["자주 쓰는 이모지 종류 — 실제 문자로"],
    "center_align": "중앙정렬 사용 여부 및 빈도 (HTML 분석 기반)",
    "text_colors": ["강조 텍스트 색상 목록 (HTML color 속성 기반)"],
    "highlight_colors": ["배경 하이라이트 색상 (background-color 기반)"],
    "font_family": "주로 사용하는 폰트명",
    "font_size_pattern": "주로 쓰는 폰트 크기 패턴",
    "bold_pattern": "볼드(굵기) 강조 사용 패턴 및 빈도",
    "italic_usage": "기울임꼴 사용 여부",
    "quote_style": "인용구/꺽쇠/따옴표 사용 방식 — 실제 예시 포함",
    "bracket_usage": "괄호 사용 패턴 (소괄호, 대괄호, 꺽쇠 등)",
    "separator_style": "구분선/구분 요소 스타일",
    "special_symbols": ["특수기호 사용 패턴 — ✅ 〰️ ➡️ ▼ ⚠️ 등 실제 문자로"],
    "line_break_style": "줄바꿈 패턴 (짧은 줄 중앙정렬형 vs 긴 단락형)",
    "writing_guide": "이 블로그 스타일을 재현하기 위한 구체적 작성 가이드 (3~5문장)",
    "examples": ["포맷팅 특징이 보이는 실제 예시 — 기호/이모지 포함"]
  }}
}}

반드시 유효한 JSON으로만 응답하세요. 다른 텍스트는 포함하지 마세요."""

        response = client.models.generate_content(
            model="gemini-2.5-pro",
            contents=analysis_prompt
        )
        
        result_text = response.text.strip()
        result = parse_ai_json(result_text)
        result["blog_id"] = blog_id
        result["post_count"] = len(unique_posts)
        result["created_at"] = datetime.now().isoformat()
        
        # DNA 분석 결과 자동 저장
        dna_id = f"DNA_{blog_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
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
    """[이전됨] 페르소나 기반 업무성격 분석은 email-persona 프로젝트로 이전"""
    return jsonify({"error": "이 기능은 이메일 도구로 이전되었습니다."}), 410




# ============================================================
# API: My Page (데이터 관리)
# ============================================================

@app.route('/api/mypage/personas', methods=['GET'])
@login_required
def mypage_personas():
    """[이전됨] 페르소나 목록 — 항상 빈 목록 반환"""
    return jsonify({"items": []})


@app.route('/api/mypage/personas/<client_id>', methods=['GET'])
@login_required
def mypage_persona_detail(client_id):
    return jsonify({"error": "이 기능은 이메일 도구로 이전되었습니다."}), 410


@app.route('/api/mypage/blogs', methods=['GET'])
@login_required
def mypage_blogs():
    """생성된 블로그 글 목록"""
    items = []
    for fp in OUTPUT_DIR.glob("BLOG_*.json"):
        try:
            data = load_blog_package(fp)
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
    data = load_blog_package(fp)
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
        primary_md = target_dir / f"{item_id}.md"
        if primary_md.exists():
            primary_md.unlink()
        for md in target_dir.glob(f"{item_id}_*.md"):
            md.unlink()
    
    return jsonify({"success": True, "message": "삭제되었습니다."})


# ============================================================
# Google Docs Export
# ============================================================

def _get_valid_google_token():
    """유효한 access_token 반환. 만료 5분 전이면 refresh_token으로 자동 갱신."""
    import time as _time
    access_token = session.get('google_token', '')
    expires_at = session.get('google_token_expires_at', 0)
    refresh_token = session.get('google_refresh_token', '')

    # 만료까지 5분 미만이면 갱신 시도
    if expires_at and _time.time() > expires_at - 300:
        if not refresh_token:
            return None  # refresh_token 없으면 재로그인 필요
        resp = http_requests.post('https://oauth2.googleapis.com/token', data={
            'client_id': GOOGLE_CLIENT_ID,
            'client_secret': GOOGLE_CLIENT_SECRET,
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token',
        })
        if resp.status_code == 200:
            new_token = resp.json()
            session['google_token'] = new_token.get('access_token', '')
            session['google_token_expires_at'] = _time.time() + new_token.get('expires_in', 3600)
            return session['google_token']
        return None  # 갱신 실패

    return access_token or None


@app.route('/api/export/google-docs', methods=['POST'])
@login_required
def export_to_google_docs():
    """블로그 글을 Google Docs로 내보내기"""
    access_token = _get_valid_google_token()
    if not access_token:
        return jsonify({"error": "Google 로그인이 필요합니다. 다시 로그인해주세요.", "login_required": True}), 401

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
        session.pop('google_refresh_token', None)
        return jsonify({"error": "Google 인증이 만료되었습니다. 다시 로그인해주세요.", "login_required": True}), 401

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
        data = ensure_blog_package_shape(data)
        title = data.get('title', item_id)
        doc_title = f"[블로그] {title}"

        versions = data.get('versions', [])
        for i, v in enumerate(versions):
            # 두 번째 버전부터 페이지 나누기 삽입
            if i > 0:
                requests_list.append({
                    'insertPageBreak': {'location': {'index': idx}}
                })
                idx += 1

            ver_label = v.get('version_label', v.get('version_type', ''))
            ver_title = v.get('title', '')
            ver_content = v.get('content', '')
            tags = v.get('tags', [])

            # 버전 라벨
            header = f"{ver_label} 버전\n{'='*40}\n\n"
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
    print("  블로그 자동화 도구")
    print(f"  서버: http://localhost:5050")
    print(f"  출력 폴더: {OUTPUT_DIR}")
    print(f"  스타일 템플릿: {len(STYLE_TEMPLATES)}개")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5050, debug=True)

