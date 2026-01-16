#!/usr/bin/env python3
"""
MCP 서버 테스트 스크립트
각 서버의 핵심 기능을 직접 호출하여 테스트
(Gemini API 버전)
"""

import io
import sys
import os

# Windows 터미널 UTF-8 출력 설정
if sys.platform == 'win32' and not isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from dotenv import load_dotenv
load_dotenv("persona-manager/.env")

print("=" * 50)
print("[TEST] MCP 서버 테스트 (Gemini API)")
print("=" * 50)

# 1. API 키 확인
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    print(f"[OK] Gemini API 키 로드됨: {api_key[:15]}...{api_key[-5:]}")
else:
    print("[FAIL] Gemini API 키가 없습니다!")
    sys.exit(1)

# 2. Gemini API 테스트
print("\n[STEP 1/3] Gemini API 테스트")
print("-" * 40)

try:
    import google.generativeai as genai
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.0-flash')
    
    # 간단한 API 호출 테스트
    response = model.generate_content("안녕! 한 문장으로 테스트 성공이라고 말해줘.")
    
    print(f"[OK] Gemini API 연결 성공!")
    print(f"   응답: {response.text}")
    
except Exception as e:
    print(f"[FAIL] 실패: {e}")

# 3. 데이터 디렉토리 확인
print("\n[STEP 2/3] 데이터 디렉토리 확인")
print("-" * 40)

from pathlib import Path

data_dirs = [
    Path.home() / "mcp-data" / "personas",
    Path.home() / "mcp-data" / "visual-personas",
    Path.home() / "mcp-data" / "outputs"
]

for d in data_dirs:
    if d.exists():
        files = list(d.glob("*"))
        print(f"[OK] {d.name}: {len(files)}개 파일")
    else:
        print(f"[WARN] {d.name}: 디렉토리 없음 (첫 사용 시 자동 생성됨)")

# 4. 서버 import 테스트
print("\n[STEP 3/3] 서버 모듈 import 테스트")
print("-" * 40)

servers = [
    ("persona-manager", "persona-manager/server.py"),
    ("content-automation", "mcp-servers/content-automation/server.py"),
    ("visual-persona-extractor", "mcp-servers/visual-persona-extractor/server.py"),
]

for name, path in servers:
    try:
        # 파일 존재 확인
        if os.path.exists(path):
            print(f"[OK] {name}: 파일 존재")
        else:
            print(f"[FAIL] {name}: 파일 없음")
    except Exception as e:
        print(f"[FAIL] {name}: {e}")

print("\n" + "=" * 50)
print("[DONE] 테스트 완료!")
print("=" * 50)
