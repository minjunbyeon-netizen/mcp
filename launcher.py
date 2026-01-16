#!/usr/bin/env python3
"""
MCP 콘텐츠 자동화 런처
start.bat 더블클릭으로 실행
"""

import sys
import os
import subprocess
from pathlib import Path

# Windows UTF-8
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def show_menu():
    clear_screen()
    print("=" * 60)
    print("🚀 MCP 콘텐츠 자동화 시스템")
    print("=" * 60)
    print()
    print("  1. 📊 페르소나 분석 → 블로그 생성 (통합)")
    print("  2. 🎯 페르소나만 분석")
    print("  3. 📝 블로그만 생성 (기존 페르소나 사용)")
    print("  4. ⚙️  환경 설정 확인")
    print("  5. 📂 출력 폴더 열기")
    print()
    print("  0. ❌ 종료")
    print()
    print("=" * 60)
    print("선택하세요: ", end="")

def check_environment():
    """환경 설정 확인"""
    clear_screen()
    print("=" * 60)
    print("⚙️  환경 설정 확인")
    print("=" * 60)
    
    # API 키 확인
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        print(f"✅ GEMINI_API_KEY: {api_key[:10]}...{api_key[-4:]}")
    else:
        print("❌ GEMINI_API_KEY가 설정되지 않았습니다!")
        print("   .env 파일에 GEMINI_API_KEY=your_key 추가하세요.")
    
    # 폴더 확인
    print()
    print("📂 폴더 상태:")
    
    folders = [
        ("input/1_personas", "페르소나 입력"),
        ("input/2_blog_writhing", "보도자료 입력"),
        ("output/personas", "페르소나 저장"),
        ("output/blog", "블로그 저장"),
    ]
    
    base = Path(__file__).parent
    for folder, desc in folders:
        path = base / folder
        if path.exists():
            files = list(path.glob("*"))
            print(f"  ✅ {desc}: {len(files)}개 파일")
        else:
            path.mkdir(parents=True, exist_ok=True)
            print(f"  📁 {desc}: 생성됨")
    
    # 필수 패키지 확인
    print()
    print("📦 필수 패키지:")
    packages = ["google.genai", "pdfplumber", "docx", "dotenv", "PIL"]
    for pkg in packages:
        try:
            __import__(pkg.replace(".", "_") if "." in pkg else pkg)
            print(f"  ✅ {pkg}")
        except:
            try:
                __import__(pkg.split(".")[0])
                print(f"  ✅ {pkg}")
            except:
                print(f"  ❌ {pkg} - pip install 필요")
    
    print()
    input("엔터를 누르면 메뉴로 돌아갑니다...")

def open_output_folder():
    """출력 폴더 열기"""
    folders = [
        Path(__file__).parent / "output" / "blog",
        Path(__file__).parent / "output" / "personas",
    ]
    for folder in folders:
        if folder.exists():
            subprocess.run(['explorer', str(folder)])

def main():
    while True:
        show_menu()
        choice = input().strip()
        
        if choice == "1":
            # 통합 실행 (페르소나 → 블로그)
            clear_screen()
            subprocess.run([sys.executable, "run_persona_test.py"], cwd=Path(__file__).parent)
            input("\n엔터를 누르면 메뉴로 돌아갑니다...")
            
        elif choice == "2":
            # 페르소나만
            clear_screen()
            # 블로그 자동 실행을 건너뛰는 플래그 추가
            os.environ["SKIP_BLOG"] = "1"
            subprocess.run([sys.executable, "run_persona_test.py"], cwd=Path(__file__).parent)
            os.environ.pop("SKIP_BLOG", None)
            input("\n엔터를 누르면 메뉴로 돌아갑니다...")
            
        elif choice == "3":
            # 블로그만
            clear_screen()
            subprocess.run([sys.executable, "run_blog_generator.py"], cwd=Path(__file__).parent)
            input("\n엔터를 누르면 메뉴로 돌아갑니다...")
            
        elif choice == "4":
            check_environment()
            
        elif choice == "5":
            open_output_folder()
            
        elif choice == "0":
            print("\n👋 종료합니다.")
            break
        else:
            print("❌ 잘못된 선택입니다.")
            input()

if __name__ == "__main__":
    main()
