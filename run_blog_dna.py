#!/usr/bin/env python3
"""
[M1] 블로그 DNA 분석 모듈
네이버 블로그 URL -> 최근 10~20개 글 수집 -> blog_dna JSON 생성

사용법:
  python run_blog_dna.py
  또는 다른 모듈에서 import:
    from run_blog_dna import analyze_blog_dna
"""

import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime

# Windows UTF-8
if sys.platform == 'win32':
    import io
    if not isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# blog_pull 크롤러 재사용
sys.path.insert(0, str(Path(__file__).parent / "blog_pull"))
from run_crawler import get_blog_id, get_post_list, get_post_content

from utils import LoadingSpinner, parse_json_response, load_api_key, setup_logger

load_api_key("GEMINI_API_KEY")
from google import genai

# 로거 설정
logger = setup_logger("blog_dna")

# 청크 설정 (run_persona_test.py의 split_kakao_into_chunks 패턴 재사용)
BLOG_CHUNK_SIZE = 6000   # 블로그 글 1개당 최대 글자 수
MAX_BLOG_POSTS = 20      # 최대 수집 글 수


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

    # 네트워크 관련 오류 (requests.exceptions 포함)
    if "requests" in err_type.lower() or "connection" in err_str or "timeout" in err_str or "network" in err_str:
        return "네트워크 연결에 문제가 발생했습니다. 인터넷 연결을 확인해주세요."

    # 기타
    return "처리 중 문제가 발생했습니다. 잠시 후 다시 시도해주세요."


def collect_blog_posts(blog_url: str, count: int = 15) -> list[dict]:
    """
    네이버 블로그 URL에서 글 목록 + 본문 수집.

    Args:
        blog_url: 네이버 블로그 URL 또는 블로그 ID
        count: 수집할 글 수 (기본 15, 최대 20)

    Returns:
        list of {"title", "url", "addDate", "content"} dict
    """
    count = min(count, MAX_BLOG_POSTS)

    blog_id = get_blog_id(blog_url)
    if not blog_id:
        logger.error(f"블로그 ID 추출 실패: {blog_url}")
        return []

    logger.info(f"블로그 수집 시작: {blog_id} ({count}개)")

    posts = get_post_list(blog_id, count)
    if not posts:
        logger.error(f"글 목록 가져오기 실패: {blog_id}")
        return []

    logger.info(f"글 목록 {len(posts)}개 확인, 본문 수집 중...")

    for i, post in enumerate(posts, 1):
        title_short = post['title'][:30] + "..." if len(post['title']) > 30 else post['title']
        print(f"  [{i}/{len(posts)}] {title_short}", end="", flush=True)

        content = get_post_content(blog_id, post['logNo'])
        if content:
            # BLOG_CHUNK_SIZE 초과분 자르기
            post['content'] = content[:BLOG_CHUNK_SIZE]
            # [MINOR-4] OK/FAILED 영문 -> 한국어 변환
            print(f" ... 완료 ({len(content):,}자)")
        else:
            post['content'] = ""
            # [MINOR-4] OK/FAILED 영문 -> 한국어 변환
            print(" ... 실패")

        if i < len(posts):
            time.sleep(0.4)  # rate limit 대비

    # 본문 없는 글 제거
    posts = [p for p in posts if p.get('content')]
    logger.info(f"본문 수집 완료: {len(posts)}개")
    return posts


def _split_posts_into_chunks(posts: list[dict], chunk_size: int = 4) -> list[str]:
    """
    수집된 블로그 글을 분석용 청크로 분할.
    split_kakao_into_chunks() 패턴 재사용.

    Args:
        posts: 수집된 블로그 글 list
        chunk_size: 청크당 글 수 (기본 4)

    Returns:
        list of 합쳐진 텍스트 청크
    """
    chunks = []
    for i in range(0, len(posts), chunk_size):
        batch = posts[i:i + chunk_size]
        chunk_text = ""
        for post in batch:
            chunk_text += f"\n\n[제목] {post['title']}\n[날짜] {post.get('addDate', '')}\n{post['content']}"
        chunks.append(chunk_text.strip())
    return chunks


def analyze_blog_dna(blog_url: str, count: int = 15) -> dict | None:
    """
    [M1] 블로그 DNA 분석 메인 함수.

    1. 블로그 글 수집 (get_blog_id, get_post_list, get_post_content 재사용)
    2. 청크 분할
    3. Gemini API로 DNA 추출
    4. blog_dna dict 반환

    Args:
        blog_url: 네이버 블로그 URL 또는 블로그 ID
        count: 수집할 글 수

    Returns:
        blog_dna dict (아래 스키마), 실패 시 None
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY 환경변수가 없습니다.")
        return None

    gemini_client = genai.Client(api_key=api_key)

    # 1. 글 수집
    spinner = LoadingSpinner("블로그 글 수집 중")
    spinner.start()
    posts = collect_blog_posts(blog_url, count)
    spinner.stop(f"{len(posts)}개 글 수집 완료")

    if not posts:
        return None

    # 2. 청크 분할 (split_kakao_into_chunks 패턴)
    chunks = _split_posts_into_chunks(posts, chunk_size=4)
    logger.info(f"분석 청크: {len(chunks)}개")

    # 3. Gemini API 분석
    print(f"\n  AI로 글쓰기 스타일 분석 중 ({len(chunks)}개 구간)...")

    # 각 청크에서 1차 특징 요약
    chunk_summaries = []
    for i, chunk in enumerate(chunks, 1):
        # [MINOR-2] 구분선 통일: 구간 표시에 = 구분선 사용
        print(f"  구간 {i}/{len(chunks)} 분석 중...", end="", flush=True)
        try:
            summary_prompt = f"""
아래 네이버 블로그 글 묶음({i}/{len(chunks)})을 분석하여 글쓰기 특징을 요약해주세요.
분석 항목: 제목 패턴, 소제목 스타일, 단락 구성, 인트로/아웃트로 문구, 이모티콘/이미지 빈도, 해시태그 패턴

---
{chunk}
---

요약 (300자 이내, 구체적 예시 포함):"""
            resp = gemini_client.models.generate_content(
                model='gemini-2.0-flash',
                contents=summary_prompt
            )
            chunk_summaries.append(f"[구간 {i}]\n{resp.text.strip()}")
            # [MINOR-4] OK/FAILED 영문 -> 한국어 변환
            print(f" 완료")
        except Exception as e:
            logger.warning(f"구간 {i} 분석 실패: {e}")
            chunk_summaries.append(f"[구간 {i}] 분석 실패")
            # [MINOR-4] OK/FAILED 영문 -> 한국어 변환
            print(f" 실패")
        time.sleep(0.5)

    combined_summary = "\n\n".join(chunk_summaries)

    # 4. 최종 blog_dna JSON 생성
    print("  최종 스타일 구조화 중...", end="", flush=True)
    blog_id = get_blog_id(blog_url)

    dna_prompt = f"""
당신은 블로그 글쓰기 스타일 분석 전문가입니다.
아래 요약을 바탕으로 이 블로그의 글쓰기 DNA를 JSON으로 구조화해주세요.

[블로그 분석 요약]
{combined_summary}

[메타 정보]
- 블로그 ID: {blog_id}
- 수집 글 수: {len(posts)}개
- 수집 일시: {datetime.now().isoformat()}

[출력 JSON 스키마 - JSON만 출력]
{{
  "source_blog_url": "https://blog.naver.com/{blog_id}",
  "collected_posts": {len(posts)},
  "collected_at": "{datetime.now().isoformat()}",
  "title_patterns": {{
    "dominant_style": "제목 주요 패턴 설명",
    "avg_title_length": 25,
    "examples": ["예시 제목1", "예시 제목2"]
  }},
  "structure_patterns": {{
    "avg_sections": 3,
    "subheading_style": "소제목 스타일 (예: 번호형, 이모티콘형, 꺽쇠형 등)",
    "paragraph_style": "단락 스타일 (짧은 단락/긴 단락/혼합)"
  }},
  "opening_patterns": ["자주 쓰는 인트로 문구 패턴1", "패턴2"],
  "closing_patterns": ["자주 쓰는 아웃트로 문구 패턴1", "패턴2"],
  "image_placeholder_frequency": 2.0,
  "hashtag_style": {{
    "position": "하단/중간/없음",
    "avg_count": 5,
    "format_example": "#예시해시태그"
  }},
  "vocabulary_profile": {{
    "signature_phrases": ["시그니처 문구1", "시그니처 문구2"],
    "industry_terms": ["자주 쓰는 전문용어1", "전문용어2"]
  }}
}}
"""

    try:
        dna_resp = gemini_client.models.generate_content(
            model='gemini-2.0-flash',
            contents=dna_prompt
        )
        blog_dna = parse_json_response(dna_resp.text)
        # [MINOR-4] OK/FAILED 영문 -> 한국어 변환
        print(" 완료")
        logger.info("blog_dna 생성 완료")

        # [V4-M1] few_shot_examples 추출: 수집된 글 중 본문이 있는 상위 2개 저장
        few_shot_examples = []
        content_posts = [p for p in posts if p.get('content')]
        for post in content_posts[:2]:
            few_shot_examples.append({
                "title": post.get('title', ''),
                "excerpt": post['content'][:300]
            })
        if few_shot_examples:
            blog_dna["few_shot_examples"] = few_shot_examples
            logger.info(f"few_shot_examples 추출 완료: {len(few_shot_examples)}개")

        return blog_dna
    except Exception as e:
        # [MINOR-4] OK/FAILED 영문 -> 한국어 변환
        print(f" 실패")
        msg = _classify_error(e)
        print(f"  {msg}")
        logger.error(f"blog_dna 생성 실패: {type(e).__name__}: {e}")
        return None


def run_blog_dna_for_persona(client_id: str, blog_url: str, count: int = 15) -> dict | None:
    """
    블로그 스타일 분석 후 페르소나에 저장하고 통합 페르소나까지 생성.

    Args:
        client_id: 페르소나 client_id
        blog_url: 분석할 네이버 블로그 URL
        count: 수집할 글 수

    Returns:
        업데이트된 persona_data, 실패 시 None
    """
    from persona_version_manager import merge_dna

    # [MINOR-2] 구분선 통일: = * 60 기준 유지, 단계 구분선 추가
    print("=" * 60)
    print("[1/2] 블로그 글쓰기 스타일 분석 중...")
    print("=" * 60)
    blog_dna = analyze_blog_dna(blog_url, count)
    if not blog_dna:
        print("블로그 글쓰기 스타일 분석에 실패했습니다.")
        return None

    print("=" * 60)
    # [MINOR-1] "이중 DNA 병합" -> 사용자 친화적 표현으로 변경
    print("[2/2] 카톡 + 블로그 스타일 통합 중...")
    print("=" * 60)
    # [MINOR-1] "unified_persona 생성 중" -> 한국어 표현
    spinner = LoadingSpinner("통합 페르소나 생성 중")
    spinner.start()
    updated_persona = merge_dna(client_id, blog_dna)
    spinner.stop("통합 완료" if updated_persona else "통합 실패")

    return updated_persona


def main():
    print("=" * 60)
    # [MINOR-3] 프로그램명: "블로그 DNA 분석기" -> launcher.py의 "블로그 DNA 분석"과 일치
    print("블로그 글쓰기 스타일 분석")
    print("담당자 블로그 글 수집 -> 글쓰기 스타일 학습")
    print("=" * 60)

    # 페르소나 선택
    from persona_version_manager import load_latest_persona
    from run_blog_generator import list_personas

    personas = list_personas()
    if not personas:
        print("\n저장된 페르소나가 없습니다.")
        print("먼저 카카오톡 분석(메뉴 2)을 실행해주세요.")
        input("\n엔터를 누르면 종료합니다...")
        return

    print("\n사용 가능한 페르소나:")
    print("-" * 50)
    for i, p in enumerate(personas, 1):
        print(f"  {i}. {p['client_name']} ({p['organization']})")

    print("\n글쓰기 스타일을 추가할 페르소나 번호를 선택하세요:")
    try:
        choice = int(input(">>> ").strip())
        selected = personas[choice - 1]
        client_id = selected["client_id"]
        client_name = selected["client_name"]
    except (ValueError, IndexError):
        print("잘못된 선택입니다.")
        input("\n엔터를 누르면 종료합니다...")
        return

    print(f"\n선택: {client_name}")

    # 블로그 URL 입력 — 최대 3회 재입력 기회 제공 (티켓 #008)
    print("\n분석할 네이버 블로그 주소를 입력하세요:")
    print("예: https://blog.naver.com/example_blog")

    blog_url = None
    blog_id = None
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        url_input = input(">>> ").strip()

        if not url_input:
            if attempt < max_attempts:
                print(f"블로그 주소를 입력해주세요. ({attempt}/{max_attempts}회)")
            else:
                print("블로그 주소를 입력하지 않아 종료합니다.")
            continue

        resolved_id = get_blog_id(url_input)
        if resolved_id:
            blog_url = url_input
            blog_id = resolved_id
            break
        else:
            if attempt < max_attempts:
                print(f"올바른 블로그 주소가 아닙니다. 다시 입력해주세요. ({attempt}/{max_attempts}회)")
            else:
                print(f"올바른 블로그 주소가 아닙니다. ({attempt}/{max_attempts}회) 종료합니다.")

    if not blog_url or not blog_id:
        # [MINOR-7] URL 오류 후 즉시 return 대신 엔터 대기 후 종료로 통일
        input("\n엔터를 누르면 종료합니다...")
        return

    print(f"\n블로그 ID: {blog_id}")

    # 수집 글 수
    print("\n수집할 글 수를 입력하세요 (기본 15, 최소 5, 최대 20):")
    count_input = input(">>> ").strip()
    try:
        count = int(count_input) if count_input else 15
        count = max(5, min(count, MAX_BLOG_POSTS))
    except ValueError:
        count = 15

    print(f"\n{count}개 글 수집 예정")
    print("\n" + "=" * 60)

    # 분석 실행
    try:
        updated_persona = run_blog_dna_for_persona(client_id, blog_url, count)
    except Exception as e:
        msg = _classify_error(e)
        print(f"\n{msg}")
        logger.error(f"블로그 스타일 분석 오류: {type(e).__name__}: {e}")
        input("\n엔터를 누르면 종료합니다...")
        return

    if updated_persona:
        print("\n" + "=" * 60)
        # [MINOR-3] 완료 메시지도 일관된 명칭 사용
        print("블로그 글쓰기 스타일 분석 완료!")
        print("=" * 60)

        blog_dna = updated_persona.get("blog_dna", {})
        unified = updated_persona.get("unified_persona", {})

        print(f"\n[글쓰기 스타일 요약]")
        print(f"  수집 글 수: {blog_dna.get('collected_posts', 0)}개")
        print(f"  제목 스타일: {blog_dna.get('title_patterns', {}).get('dominant_style', '-')}")
        print(f"  단락 스타일: {blog_dna.get('structure_patterns', {}).get('paragraph_style', '-')}")
        print(f"  이미지 빈도: {blog_dna.get('image_placeholder_frequency', 0):.1f}회/단락")
        print(f"  해시태그: {blog_dna.get('hashtag_style', {}).get('position', '-')}, "
              f"{blog_dna.get('hashtag_style', {}).get('avg_count', 0)}개")

        if unified:
            # [MINOR-1] "통합 페르소나 (unified_persona)" -> 괄호 영문 변수명 제거
            print(f"\n[통합 페르소나 생성 완료]")
            print(f"  글쓰기 가이드: {unified.get('writing_guide', '-')[:80]}...")

        print(f"\n스키마 버전: {updated_persona.get('schema_version', '-')}")
        print("\n이제 블로그 생성(메뉴 3 또는 원클릭)에서 향상된 페르소나가 자동 적용됩니다.")
    else:
        print("\n블로그 글쓰기 스타일 분석에 실패했습니다.")

    input("\n엔터를 누르면 종료합니다...")


if __name__ == "__main__":
    main()
