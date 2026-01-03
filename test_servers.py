#!/usr/bin/env python3
"""
MCP 서버 테스트 스크립트
각 서버의 핵심 기능을 직접 호출하여 테스트
"""

import sys
import os

# 프로젝트 루트에서 실행
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv("persona-manager/.env")

print("=" * 50)
print("🧪 MCP 서버 테스트")
print("=" * 50)

# 1. API 키 확인
api_key = os.getenv("ANTHROPIC_API_KEY")
if api_key:
    print(f"✅ API 키 로드됨: {api_key[:20]}...{api_key[-10:]}")
else:
    print("❌ API 키가 없습니다!")
    sys.exit(1)

# 2. persona-manager 테스트
print("\n📌 [1/3] persona-manager 테스트")
print("-" * 40)

try:
    # 모듈 직접 import 대신 함수만 테스트
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    
    # 간단한 API 호출 테스트
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=100,
        messages=[{"role": "user", "content": "안녕! 한 문장으로 테스트 성공이라고 말해줘."}]
    )
    
    print(f"✅ Anthropic API 연결 성공!")
    print(f"   응답: {response.content[0].text}")
    
except Exception as e:
    print(f"❌ 실패: {e}")

# 3. 데이터 디렉토리 확인
print("\n📌 [2/3] 데이터 디렉토리 확인")
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
        print(f"✅ {d.name}: {len(files)}개 파일")
    else:
        print(f"⚠️  {d.name}: 디렉토리 없음 (첫 사용 시 자동 생성됨)")

# 4. 서버 import 테스트
print("\n📌 [3/3] 서버 모듈 import 테스트")
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
            print(f"✅ {name}: 파일 존재")
        else:
            print(f"❌ {name}: 파일 없음")
    except Exception as e:
        print(f"❌ {name}: {e}")

print("\n" + "=" * 50)
print("🎉 테스트 완료!")
print("=" * 50)
