# 페르소나 기반 블로그 자동 생성 시스템

광고주 카카오톡 대화에서 페르소나를 추출하고, 보도자료를 페르소나 스타일 블로그 글로 자동 변환

---

## 빠른 시작 (CLI)

### 1단계: 페르소나 추출

카카오톡 대화에서 광고주의 커뮤니케이션 스타일을 분석합니다.

```bash
cd "G:/내 드라이브/01_work/hive-media/auto-blog"
python run_persona_test.py
```

**실행 흐름:**
1. 카카오톡 파일 목록에서 번호 선택
2. 담당자 이름/소속 입력 (엔터시 기본값)
3. AI 분석 (로딩바 표시)
4. 페르소나 저장 완료
5. 바로 블로그 작성으로 연결 (Y/n)

---

### 2단계: 블로그 글 생성

페르소나 스타일에 맞춰 보도자료를 블로그로 변환합니다.

```bash
python run_blog_generator.py
```

**실행 흐름:**
1. 페르소나 목록에서 번호 선택
2. 보도자료 파일 목록에서 번호 선택
3. SEO 키워드 입력 (선택)
4. AI 블로그 생성 (로딩바 표시)
5. Word/Markdown 파일 저장

---

## 폴더 구조

```
auto-blog/
├── input/
│   ├── 1_personas/          <- 카카오톡 .txt/.pdf 파일
│   └── 2_blog_writing/      <- 보도자료 .txt/.pdf/.hwp 파일
├── output/
│   ├── personas/            <- 페르소나 JSON
│   └── blog/                <- Word 파일
├── run_persona_test.py      <- 페르소나 추출기
├── run_blog_generator.py    <- 블로그 생성기
├── persona_version_manager.py <- 페르소나 버전 관리
├── launcher.py              <- CLI 메뉴 런처
├── utils.py                 <- 공통 유틸리티
├── persona-manager/         <- MCP 서버 (페르소나 관리)
├── mcp-servers/             <- 추가 MCP 서버들
└── blog_pull/               <- 네이버 블로그 크롤러
```

---

## 설치

```bash
python -m venv venv
.\venv\Scripts\activate  # Windows

pip install google-genai pdfplumber pillow python-dotenv python-docx mcp olefile
```

## 설정

1. `.env` 파일을 프로젝트 루트에 생성:
   ```
   GEMINI_API_KEY=your_gemini_api_key_here
   ```
2. 또는 `mcp_config.template.json`을 복사하여 `mcp_config.json` 생성 후 API 키 입력

## 보안

`.env`, `mcp_config.json` 파일은 `.gitignore`에 포함됨 (API 키 보호)
