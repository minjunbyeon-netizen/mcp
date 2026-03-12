"""
네이버 블로그 크롤러 — run_crawler.py
app.py에서 import하여 사용:
  get_blog_id(blog_input) -> str | None
  get_post_list(blog_id, count) -> list[dict]
  get_post_content(blog_id, log_no) -> str
  save_results(blog_id, posts) -> str (folder path)
"""

import os
import re
import json
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# app.py에서 외부 주입: _run_crawler.OUTPUT_DIR = ...
OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "mcp-data", "blog-collections")

BASE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "application/json, text/plain, */*",
}


def _make_session(blog_id: str) -> requests.Session:
    s = requests.Session()
    s.headers.update(BASE_HEADERS)
    s.headers["Referer"] = f"https://m.blog.naver.com/{blog_id}"
    # 쿠키 획득
    try:
        s.get(f"https://m.blog.naver.com/{blog_id}", timeout=10)
    except Exception:
        pass
    return s


# ──────────────────────────────────────────
# 1. 블로그 ID 추출
# ──────────────────────────────────────────

def get_blog_id(blog_input: str) -> str | None:
    """
    URL 또는 블로그 ID 문자열에서 순수 블로그 ID만 추출.
    예) https://blog.naver.com/example123  →  example123
        m.blog.naver.com/example123        →  example123
        example123                         →  example123
    """
    blog_input = blog_input.strip().rstrip("/")
    m = re.search(r"(?:m\.)?blog\.naver\.com/([A-Za-z0-9_]+)", blog_input)
    if m:
        return m.group(1)
    if re.fullmatch(r"[A-Za-z0-9_]+", blog_input):
        return blog_input
    return None


# ──────────────────────────────────────────
# 2. 글 목록 가져오기
# ──────────────────────────────────────────

def get_post_list(blog_id: str, count: int = 10) -> list[dict]:
    """
    네이버 블로그 포스트 목록 반환.
    반환 형식: [{"title": ..., "logNo": ..., "addDate": ..., "url": ...}, ...]
    """
    session = _make_session(blog_id)
    posts = []
    page = 1

    while len(posts) < count:
        url = (
            f"https://m.blog.naver.com/api/blogs/{blog_id}/post-list"
            f"?categoryNo=0&page={page}"
        )
        try:
            resp = session.get(url, timeout=12)
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            break

        if not data.get("isSuccess"):
            break

        items = data.get("result", {}).get("items", [])
        if not items:
            break

        for item in items:
            log_no = str(item.get("logNo", ""))
            title = item.get("titleWithInspectMessage", "").strip() or "(제목 없음)"
            real_blog_id = item.get("domainIdOrBlogId") or blog_id
            add_date_ms = item.get("addDate")
            if add_date_ms:
                try:
                    dt = datetime.fromtimestamp(int(add_date_ms) / 1000, tz=timezone.utc)
                    add_date = dt.strftime("%Y-%m-%d")
                except Exception:
                    add_date = ""
            else:
                add_date = ""
            post_url = f"https://blog.naver.com/{real_blog_id}/{log_no}"
            posts.append({
                "title": title,
                "logNo": log_no,
                "addDate": add_date,
                "url": post_url,
            })
            if len(posts) >= count:
                break

        # 다음 페이지 없으면 종료
        if len(items) == 0:
            break
        page += 1
        time.sleep(0.3)

    return posts[:count]


# ──────────────────────────────────────────
# 3. 본문 추출
# ──────────────────────────────────────────

def get_post_content(blog_id: str, log_no: str) -> str:
    """
    네이버 블로그 포스트 본문 텍스트 반환.
    모바일 뷰 우선, PC 뷰 폴백.
    """
    result = get_post_content_with_style(blog_id, log_no)
    return result.get("text", "")


def get_post_content_with_style(blog_id: str, log_no: str) -> dict:
    """
    본문 텍스트 + 시각적 스타일 메타데이터 반환.
    반환: {"text": str, "style_meta": dict}
    """
    session = _make_session(blog_id)
    soup = None

    for fetch_url in [
        f"https://m.blog.naver.com/{blog_id}/{log_no}",
        (
            "https://blog.naver.com/PostView.naver"
            f"?blogId={blog_id}&logNo={log_no}&redirect=Dlog&widgetTypeCall=true"
        ),
    ]:
        try:
            resp = session.get(fetch_url, timeout=12)
            resp.raise_for_status()
            candidate = BeautifulSoup(resp.text, "html.parser")
            div = (
                candidate.select_one(".se-main-container")
                or candidate.select_one(".post-view")
                or candidate.select_one("#postViewArea")
                or candidate.select_one(".se_doc_viewer")
            )
            if div:
                soup = div
                break
        except Exception:
            continue

    if not soup:
        return {"text": "", "style_meta": {}}

    text = _clean_text(soup.get_text(separator="\n", strip=True))
    style_meta = _extract_style_meta(soup)
    return {"text": text, "style_meta": style_meta}


def _extract_style_meta(content_div) -> dict:
    """네이버 Smart Editor HTML에서 시각적 스타일 패턴 추출."""
    all_styles = []
    all_classes = []

    for el in content_div.find_all(style=True):
        s = el.get("style", "").strip()
        if s:
            all_styles.append(s)

    for el in content_div.find_all(class_=True):
        for c in el.get("class", []):
            if c.startswith("se-"):
                all_classes.append(c)

    combined_style = " ".join(all_styles)

    # 색상 추출
    colors = re.findall(r'(?<!background-)color\s*:\s*(#[0-9a-fA-F]{3,8})', combined_style)
    bg_colors = re.findall(r'background-color\s*:\s*(#[0-9a-fA-F]{3,8})', combined_style)

    # 자주 쓰는 텍스트 색상 (흰/검 제외)
    accent_colors = [c for c in colors if c.lower() not in ("#ffffff", "#000000", "#fff", "#000")]
    highlight_colors = [c for c in bg_colors if c.lower() not in ("#ffffff", "#fff")]

    # 정렬 패턴
    center_count = all_classes.count("se-text-paragraph-align-center") + all_classes.count("se-section-align-center")
    total_para = all_classes.count("se-text-paragraph")
    center_ratio = round(center_count / total_para, 2) if total_para else 0

    # 폰트 패턴
    fonts = [c for c in all_classes if c.startswith("se-ff-") and c != "se-ff-"]
    font_counter = Counter(fonts)

    # 폰트 크기 패턴
    sizes = [c for c in all_classes if c.startswith("se-fs-")]
    size_counter = Counter(sizes)

    # 굵기 (볼드)
    bold_count = len(re.findall(r'font-weight\s*:\s*(bold|700|800|900)', combined_style))

    # 인용구/특수 구조
    quote_els = content_div.select(".se-quote, .se-quotation, blockquote")
    has_quote = len(quote_els) > 0

    # 이탤릭
    italic_count = len(re.findall(r'font-style\s*:\s*italic', combined_style))

    return {
        "center_align_ratio": center_ratio,         # 0~1, 높을수록 중앙정렬 많이 씀
        "accent_colors": list(Counter(accent_colors).most_common(5)),   # [(색상, 빈도)]
        "highlight_colors": list(Counter(highlight_colors).most_common(3)),
        "dominant_fonts": [f[0].replace("se-ff-", "") for f in font_counter.most_common(3)],
        "font_sizes": [s[0].replace("se-fs-", "") for s in size_counter.most_common(3)],
        "bold_count": bold_count,
        "italic_count": italic_count,
        "has_quote_block": has_quote,
        "total_styled_elements": len(all_styles),
    }


def _clean_text(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    result, prev = [], None
    for line in lines:
        if line != prev:
            result.append(line)
        prev = line
    return "\n".join(result)


# ──────────────────────────────────────────
# 4. 저장
# ──────────────────────────────────────────

def save_results(blog_id: str, posts: list[dict]) -> str:
    """
    수집 결과를 OUTPUT_DIR/{blog_id}_{YYYYMMDD_HHMMSS}/ 에 저장.
    app.py가 기대하는 _data.json 형식으로 저장:
      {"blog_id": ..., "collected_at": ..., "posts": [...]}
    반환값: 저장 폴더 경로 (str)
    """
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    folder = Path(OUTPUT_DIR) / f"{blog_id}_{timestamp}"
    folder.mkdir(parents=True, exist_ok=True)

    # app.py가 읽는 _data.json 형식
    data = {
        "blog_id": blog_id,
        "collected_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "posts": posts,
    }
    with open(folder / "_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # 개별 txt (사람이 읽기용)
    for post in posts:
        log_no = post.get("logNo", "unknown")
        title = re.sub(r'[\\/:*?"<>|]', "_", post.get("title", ""))[:60]
        filename = f"{log_no}_{title}.txt"
        with open(folder / filename, "w", encoding="utf-8") as f:
            f.write(f"제목: {post.get('title', '')}\n")
            f.write(f"날짜: {post.get('addDate', '')}\n")
            f.write(f"URL:  {post.get('url', '')}\n")
            f.write("=" * 60 + "\n\n")
            f.write(post.get("content", ""))

    return str(folder)
