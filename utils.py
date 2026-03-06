#!/usr/bin/env python3
"""
공통 유틸리티 모듈
LoadingSpinner, JSON 추출, API 키 로드, 파일 텍스트 추출 등 공통 기능
"""

import os
import json
import re
import threading
import time
from pathlib import Path


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


def extract_json_from_response(response_text: str) -> str:
    """AI 응답에서 JSON 문자열 추출"""
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0]
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0]
    return response_text.strip()


def parse_json_response(response_text: str) -> dict:
    """AI 응답에서 JSON을 추출하고 파싱"""
    cleaned = extract_json_from_response(response_text)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # 잘못된 이스케이프 문자 정리 후 재시도
        cleaned = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', cleaned)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # 최종 시도: 제어 문자 제거
            cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', cleaned)
            return json.loads(cleaned)


def load_api_key(key_name: str = "GEMINI_API_KEY") -> str | None:
    """환경변수 또는 mcp_config.json에서 API 키 로드"""
    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.getenv(key_name)
    if api_key:
        return api_key

    config_path = Path(__file__).parent / "mcp_config.json"
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            for server in config.get("mcpServers", {}).values():
                key = server.get("env", {}).get(key_name)
                if key:
                    os.environ[key_name] = key
                    return key

    return None


# ============================================================
# [M-5] 공통 파일 텍스트 추출 함수 (web/app.py에서 통합)
# 지원 형식: .txt, .pdf (PyMuPDF 우선 → pdfplumber fallback),
#            .docx, .hwp, .jpg/.jpeg/.png
# ============================================================

# HWP 지원 여부
try:
    import olefile as _olefile
    import zlib as _zlib
    _HWP_SUPPORTED = True
except ImportError:
    _HWP_SUPPORTED = False


def extract_text_from_file(file_path: Path) -> str:
    """
    다양한 파일 형식에서 텍스트 추출 (공통 유틸).

    지원 형식:
    - .txt  : UTF-8 텍스트
    - .pdf  : PyMuPDF(fitz) 우선, 실패 시 pdfplumber fallback
    - .docx : python-docx (단락 + 표)
    - .hwp  : olefile + zlib 압축 해제
    - .jpg/.jpeg/.png : 이미지 경로 마커 반환 (Gemini Vision 처리용)

    Returns:
        추출된 텍스트 문자열
    Raises:
        ValueError: 지원하지 않는 파일 형식 또는 라이브러리 미설치
    """
    file_path = Path(file_path)
    ext = file_path.suffix.lower()

    if ext == '.txt':
        for enc in ('utf-8', 'cp949', 'euc-kr'):
            try:
                with open(file_path, 'r', encoding=enc) as f:
                    return f.read()
            except (UnicodeDecodeError, LookupError):
                continue
        raise ValueError(f"TXT 파일 인코딩을 인식할 수 없습니다: {file_path}")

    elif ext == '.pdf':
        text = ""
        # 1차 시도: PyMuPDF (fitz) — 레이아웃 보존, 빠름
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(str(file_path))
            for page in doc:
                text += page.get_text("text") + "\n"
            doc.close()
        except Exception as e:
            print("  PDF 읽는 중입니다... (레이아웃 방식 전환)")
            # 2차 시도: pdfplumber (백업)
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        return text

    elif ext == '.docx':
        text = ""
        try:
            import docx
            doc = docx.Document(file_path)
            # 단락 텍스트
            for para in doc.paragraphs:
                if para.text.strip():
                    text += para.text + "\n"
            # 표(Table) 데이터
            for table in doc.tables:
                for row in table.rows:
                    row_data = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if row_data:
                        text += " | ".join(row_data) + "\n"
        except Exception as e:
            raise ValueError(f"DOCX 파일 읽기 실패: {e}")
        return text

    elif ext == '.hwp':
        if not _HWP_SUPPORTED:
            raise ValueError("HWP 지원을 위해 'pip install olefile'를 실행하세요.")

        text_parts = []
        try:
            ole = _olefile.OleFileIO(str(file_path))
            for stream in ole.listdir():
                if 'BodyText' in stream or 'Section' in stream:
                    try:
                        data = ole.openstream(stream).read()
                        try:
                            decompressed = _zlib.decompress(data, -15)
                            chunk = decompressed.decode('utf-16-le', errors='ignore')
                            chunk = ''.join(c for c in chunk if c.isprintable() or c in '\n\r\t')
                            if chunk.strip():
                                text_parts.append(chunk)
                        except (_zlib.error, UnicodeDecodeError):
                            pass
                    except Exception:
                        pass
            ole.close()
        except Exception as e:
            raise ValueError(f"HWP 파일 읽기 실패: {e}")

        return "\n".join(text_parts) if text_parts else ""

    elif ext in ['.jpg', '.jpeg', '.png']:
        # 이미지는 호출자가 Gemini Vision으로 처리 (경로 마커 반환)
        return f"[IMAGE_FILE:{file_path}]"

    else:
        raise ValueError(f"지원되지 않는 파일 형식: {ext}")
