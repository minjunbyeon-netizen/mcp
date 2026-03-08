#!/usr/bin/env python3
"""
[M3] 원클릭 파이프라인
배포자료/홍보내용을 넣으면 한 번에 바로 쓸 수 있는 블로그 글 생성

사용법:
  python run_oneclick.py
  또는 launcher.py 메뉴 7번

흐름:
  (1) 페르소나 선택
  (2) 배포자료 파일 입력 (경로 붙여넣기 OR input/3_oneclick/ 폴더 자동 스캔)
  (3) 자동 생성 -> Word 저장
"""

import sys
import os
import subprocess
from pathlib import Path
from datetime import datetime

# Windows UTF-8
if sys.platform == 'win32':
    import io
    if not isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from utils import LoadingSpinner, extract_text_from_file, load_api_key, setup_logger
from run_blog_generator import list_personas, generate_blog_post, WORD_OUTPUT_DIR

load_api_key("GEMINI_API_KEY")

# 로거
logger = setup_logger("oneclick")

# 원클릭 입력 폴더
ONECLICK_DIR = Path(__file__).parent / "input" / "3_oneclick"
ONECLICK_DIR.mkdir(parents=True, exist_ok=True)

# 지원 파일 형식
SUPPORTED_EXTENSIONS = ['.txt', '.pdf', '.hwp', '.docx', '.jpg', '.jpeg', '.png']


def _classify_error(e: Exception) -> str:
    """오류 유형에 따라 사용자 친화적 메시지 반환 (티켓 #009)"""
    err_type = type(e).__name__
    err_str = str(e).lower()

    # API 관련 오류
    if err_type in ("APIError", "ValueError") or "api" in err_str or "key" in err_str:
        return "AI 서비스 연결에 문제가 발생했습니다. 인터넷 연결과 API 키를 확인해주세요."

    # 파일 관련 오류
    if err_type in ("FileNotFoundError", "PermissionError") or "file" in err_str or "permission" in err_str:
        return "파일을 읽을 수 없습니다. 파일 경로와 권한을 확인해주세요."

    # 네트워크 관련 오류
    if "requests" in err_type.lower() or "connection" in err_str or "timeout" in err_str or "network" in err_str:
        return "네트워크 연결에 문제가 발생했습니다. 인터넷 연결을 확인해주세요."

    # 기타
    return "처리 중 문제가 발생했습니다. 잠시 후 다시 시도해주세요."


def _scan_oneclick_folder() -> list[Path]:
    """input/3_oneclick/ 폴더에서 지원 파일 자동 스캔"""
    files = [
        f for f in ONECLICK_DIR.iterdir()
        if f.is_file()
        and f.suffix.lower() in SUPPORTED_EXTENSIONS
        and f.name.lower() != "readme.txt"
    ]
    return sorted(files, key=lambda f: f.stat().st_mtime, reverse=True)


def select_input_file() -> str | None:
    """
    배포자료 파일 선택.
    방법 1: input/3_oneclick/ 폴더 자동 스캔
    방법 2: 파일 경로 직접 붙여넣기

    Returns:
        추출된 텍스트, 실패 시 None
    """
    print("\n[배포자료 입력 방법 선택]")
    print("  1. input/3_oneclick/ 폴더에서 파일 선택")
    print("  2. 파일 경로 직접 붙여넣기")
    print()
    method = input(">>> ").strip()

    if method == "2":
        # 경로 직접 입력
        print("\n파일 경로를 붙여넣으세요:")
        print("(예: C:\\Users\\User\\Desktop\\보도자료.pdf)")
        path_input = input(">>> ").strip().strip('"').strip("'")
        if not path_input:
            print("경로를 입력해주세요.")
            return None

        file_path = Path(path_input)
        if not file_path.exists():
            print(f"파일을 찾을 수 없습니다: {file_path}")
            return None

        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            print(f"지원하지 않는 파일 형식입니다: {file_path.suffix}")
            print(f"지원 형식: {', '.join(SUPPORTED_EXTENSIONS)}")
            return None

        print(f"\n선택: {file_path.name}")
        try:
            text = extract_text_from_file(file_path)
            if not text.strip():
                print("파일에서 텍스트를 추출할 수 없습니다.")
                return None
            print(f"배포자료 길이: {len(text):,} 글자")
            return text
        except Exception as e:
            print(f"파일을 읽을 수 없습니다. 파일 경로와 권한을 확인해주세요.")
            logger.error(f"파일 읽기 오류: {e}")
            return None

    else:
        # 폴더 스캔 (기본)
        files = _scan_oneclick_folder()

        if not files:
            print(f"\n배포자료 파일이 없습니다.")
            print(f"아래 폴더에 파일을 넣어주세요:")
            print(f"  {ONECLICK_DIR}")
            print(f"지원 형식: {', '.join(SUPPORTED_EXTENSIONS)}")
            print()
            print("또는 방법 2(경로 직접 입력)를 사용하세요.")
            return None

        # 파일 1개이면 자동 선택 (티켓 #007)
        if len(files) == 1:
            auto_file = files[0]
            size_kb = auto_file.stat().st_size / 1024
            ext_display = auto_file.suffix.upper().lstrip('.')
            print(f"\ninput/3_oneclick/ 폴더에서 파일 1개를 자동으로 선택합니다:")
            # [MINOR-2] 화살표 기호 ASCII "->" -> 유니코드 "→" 통일
            print(f"  → {auto_file.stem} [{ext_display}] ({size_kb:.1f}KB)")
            print("다른 파일을 사용하려면 방법 2(경로 직접 입력)를 선택하세요.")
            selected_files = [auto_file]
        else:
            print(f"\ninput/3_oneclick/ 폴더 내 파일:")
            print("-" * 50)
            for i, f in enumerate(files, 1):
                size_kb = f.stat().st_size / 1024
                ext_display = f.suffix.upper().lstrip('.')
                print(f"  {i}. {f.stem} [{ext_display}] ({size_kb:.1f}KB)")

            print("\n사용할 파일 번호를 입력하세요:")
            print("(여러 파일: 1,2,3 또는 all)")
            choice_input = input(">>> ").strip().lower()

            selected_files = []
            try:
                if choice_input == "all":
                    selected_files = files
                elif "," in choice_input:
                    indices = [int(x.strip()) for x in choice_input.split(",")]
                    selected_files = [files[i - 1] for i in indices]
                else:
                    idx = int(choice_input)
                    selected_files = [files[idx - 1]]
            except (ValueError, IndexError):
                print("잘못된 입력입니다.")
                return None

        if not selected_files:
            return None

        if len(selected_files) == 1:
            print(f"\n선택: {selected_files[0].name}")
        else:
            print(f"\n선택: {len(selected_files)}개 파일")

        # 모든 파일 읽기 및 합치기
        all_texts = []
        for sf in selected_files:
            try:
                text = extract_text_from_file(sf)
                if text.strip():
                    if len(selected_files) > 1:
                        all_texts.append(f"\n\n===== {sf.name} =====\n\n{text}")
                    else:
                        all_texts.append(text)
            except Exception as e:
                print(f"파일을 읽을 수 없습니다: {sf.name} — 파일 경로와 권한을 확인해주세요.")
                logger.error(f"파일 읽기 오류: {sf.name} / {e}")

        if not all_texts:
            print("파일에서 텍스트를 추출할 수 없습니다.")
            return None

        combined = "\n".join(all_texts)
        print(f"배포자료 길이: {len(combined):,} 글자")
        return combined


def run_oneclick():
    """원클릭 파이프라인 메인 실행"""

    print("=" * 60)
    # [MINOR-3] 프로그램명: launcher.py 메뉴명 "원클릭 블로그 생성"과 일치
    print("원클릭 블로그 생성")
    print("배포자료 → 즉시 블로그 출력")
    print("=" * 60)

    # Step 1: 페르소나 선택
    print("\n[Step 1] 페르소나 선택")
    personas = list_personas()
    if not personas:
        # [티켓 #T001] 페르소나 없음 — 다음 단계 안내 추가 (소비자팀 V4-MAJOR-1)
        print("\n저장된 페르소나가 없습니다.")
        print()
        print("원클릭 블로그 생성을 사용하려면 먼저 페르소나를 만들어야 합니다.")
        print("다음 순서로 진행해주세요:")
        print()
        print("  1단계: 메뉴 1 (카카오톡 채널 분석) 실행")
        print("         → 블로그 채널의 글쓰기 스타일을 학습합니다")
        print()
        print("  2단계: 메뉴 8 (블로그 글쓰기 스타일 분석) 실행 (권장)")
        print("         → 더 정교한 스타일 학습을 완료합니다")
        print()
        print("  3단계: 다시 메뉴 7 (원클릭 블로그 생성) 실행")
        print()
        print("launcher.py를 실행하면 전체 메뉴를 확인할 수 있습니다.")
        return

    print("\n사용 가능한 페르소나:")
    print("-" * 50)
    for i, p in enumerate(personas, 1):
        schema_mark = ""
        # 통합 스타일 보유 여부 확인
        from persona_version_manager import load_latest_persona
        result = load_latest_persona(p['client_id'])
        if result:
            pdata = result[0]
            if pdata.get("unified_persona"):
                # [MINOR-1] [DNA 통합] -> [통합 스타일 적용]으로 사용자 친화적 표현 변경
                schema_mark = " [통합 스타일 적용]"
        # 첫 번째 항목에 기본 선택 안내 표시 (티켓 #007)
        default_mark = " (기본)" if i == 1 else ""
        print(f"  {i}. {p['client_name']} ({p['organization']}){schema_mark}{default_mark}")

    print("\n페르소나 번호를 입력하세요 (엔터: 1번 자동 선택):")
    try:
        raw = input(">>> ").strip()
        # 엔터만 입력하면 첫 번째 페르소나 자동 선택 (티켓 #007)
        if raw == "":
            choice = 1
            print(f"  → 1번 페르소나를 자동으로 선택합니다.")
        else:
            choice = int(raw)
        selected = personas[choice - 1]
        client_id = selected["client_id"]
        client_name = selected["client_name"]
    except (ValueError, IndexError):
        print("잘못된 선택입니다.")
        return

    print(f"\n선택: {client_name}")

    # [MINOR-6] DNA 통합 미완 페르소나 선택 시 품질 저하 경고 추가
    from persona_version_manager import load_latest_persona
    persona_result = load_latest_persona(client_id)
    if persona_result:
        pdata = persona_result[0]
        if not pdata.get("unified_persona"):
            print("\n[안내] 이 페르소나는 블로그 글쓰기 스타일이 아직 학습되지 않았습니다.")
            print("  메뉴 8(블로그 글쓰기 스타일 분석)을 먼저 실행하면 더 정교한 결과를 얻을 수 있습니다.")
            print("  지금 바로 계속 진행하려면 엔터를 누르세요.")
            input(">>> ")

    # Step 2: 배포자료 입력
    print("\n[Step 2] 배포자료 입력")
    press_release = select_input_file()
    if not press_release:
        return

    # SEO 키워드 (선택) — 라벨 개선 (티켓 #007)
    print("\n[Step 3] SEO 키워드 (선택사항)")
    print("SEO 키워드를 입력하세요 (쉼표로 구분, 엔터로 건너뛰기):")
    keywords_input = input(">>> ").strip()
    keywords = [k.strip() for k in keywords_input.split(",")] if keywords_input else None

    # Step 4: 자동 생성
    print("\n[Step 4] 블로그 자동 생성")
    print("-" * 60)

    spinner = LoadingSpinner(f"{client_name} 페르소나로 블로그 작성 중")
    spinner.start()

    try:
        result = generate_blog_post(client_id, press_release, keywords)
    except Exception as e:
        spinner.stop("생성 실패")
        msg = _classify_error(e)
        print(f"\n{msg}")
        logger.error(f"원클릭 생성 오류: {client_name} / {type(e).__name__}: {e}")
        return

    if result:
        spinner.stop("생성 완료")
        blog_data, md_path, docx_path, gdrive_path = result
        blog = blog_data["content"]

        # [V4-M4] 제목 3변형 선택 UI
        title_variants = blog_data.get("title_variants") or blog.get("title_variants", [])
        # 빈 문자열 제거 후 유효한 변형만 추출
        valid_variants = [t for t in title_variants if t and t.strip()]

        selected_title = blog.get("title", "")
        if len(valid_variants) >= 2:
            print("\n" + "=" * 60)
            print("제목을 선택하세요:")
            print("-" * 60)
            labels = ["클릭유도형", "정보형", "감성형"]
            for i, (variant, label) in enumerate(zip(valid_variants, labels), 1):
                print(f"  {i}. [{label}] {variant}")
            print("-" * 60)
            print("번호를 입력하세요 (엔터: 1번 자동 선택):")
            try:
                raw = input(">>> ").strip()
                if raw == "":
                    choice_idx = 0
                else:
                    choice_idx = int(raw) - 1
                if 0 <= choice_idx < len(valid_variants):
                    selected_title = valid_variants[choice_idx]
                    blog["title"] = selected_title
                    blog_data["content"]["title"] = selected_title
                    print(f"\n선택된 제목: {selected_title}")
                else:
                    print(f"\n범위를 벗어난 입력 — 1번 제목을 사용합니다: {valid_variants[0]}")
                    selected_title = valid_variants[0]
                    blog["title"] = selected_title
                    blog_data["content"]["title"] = selected_title
            except (ValueError, IndexError):
                print(f"\n잘못된 입력 — 1번 제목을 사용합니다: {valid_variants[0]}")
                selected_title = valid_variants[0]
                blog["title"] = selected_title
                blog_data["content"]["title"] = selected_title

            # 선택된 제목으로 Word 파일명 재지정
            import shutil as _shutil
            safe_title_new = selected_title[:30].replace('/', '_').replace('\\', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_').strip()
            safe_client_name = client_name.replace(' ', '_')
            date_str = datetime.now().strftime('%Y%m%d')
            new_docx_filename = f"{safe_client_name}_{safe_title_new}_{date_str}.docx"
            new_docx_path = WORD_OUTPUT_DIR / new_docx_filename
            if docx_path.exists() and new_docx_path != docx_path:
                try:
                    docx_path.rename(new_docx_path)
                    docx_path = new_docx_path
                    if gdrive_path and gdrive_path.exists():
                        gdrive_new = gdrive_path.parent / new_docx_filename
                        gdrive_path.rename(gdrive_new)
                        gdrive_path = gdrive_new
                except Exception:
                    pass  # 파일명 변경 실패 시 기존 이름 유지

        print("\n" + "=" * 60)
        print("원클릭 블로그 생성 완료!")
        print("=" * 60)
        print(f"\n제목: {blog['title']}")
        print(f"태그: {', '.join(blog.get('tags', []))}")
        print(f"\n저장 위치:")
        print(f"  Word: {docx_path}")
        if gdrive_path:
            print(f"  Google Drive: {gdrive_path}")

        logger.info(f"원클릭 완료: {client_name} / {blog['title']}")

        # 폴더 열기
        print("\n출력 폴더를 여시겠습니까? (Y/n): ", end="")
        if input().strip().lower() != 'n':
            subprocess.run(['explorer', str(WORD_OUTPUT_DIR)])
    else:
        spinner.stop("생성 실패")
        print("\nAI 서비스 연결에 문제가 발생했습니다. 인터넷 연결과 API 키를 확인해주세요.")
        logger.error(f"원클릭 생성 실패: {client_name}")


def main():
    run_oneclick()
    input("\n엔터를 누르면 종료합니다...")


if __name__ == "__main__":
    main()
