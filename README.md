# MCP 콘텐츠 자동화 서버

광고주 페르소나 기반 콘텐츠 자동 생성 시스템

---

## 🚀 빠른 시작 (CLI 도구)

### 1단계: 페르소나 추출
카카오톡 대화에서 광고주의 커뮤니케이션 스타일을 분석합니다.

```bash
cd c:\xampp\htdocs\00_dev\03_mcp_test
python run_persona_test.py
```

**실행 흐름:**
1. 📂 카카오톡 파일 목록에서 번호 선택
2. 📝 담당자 이름/소속 입력 (엔터시 기본값)
3. ⏳ AI 분석 (로딩바 표시)
4. ✅ 페르소나 저장 완료
5. 📂 폴더 열기 옵션
6. 📝 **바로 블로그 작성으로 연결** (Y/n)

---

### 2단계: 블로그 글 생성
페르소나 스타일에 맞춰 보도자료를 블로그로 변환합니다.

```bash
python run_blog_generator.py
```

**실행 흐름:**
1. 📋 페르소나 목록에서 번호 선택
2. 📂 보도자료 파일 목록에서 번호 선택
3. 🔑 SEO 키워드 입력 (선택)
4. ⏳ AI 블로그 생성 (로딩바 표시)
5. ✅ Word/Markdown 파일 저장
6. 📂 폴더 열기 옵션

---

## 📂 폴더 구조

```
03_mcp_test/
├── input/
│   ├── 1_personas/          ← 카카오톡 .txt 파일
│   └── 2_blog_writhing/     ← 보도자료 .txt 파일
├── output/
│   ├── personas/            ← 페르소나 JSON
│   └── blog/                ← Word 파일
├── run_persona_test.py      ← 페르소나 추출기
└── run_blog_generator.py    ← 블로그 생성기
```

---

## 📦 설치

```bash
# 가상환경 생성 및 활성화
python -m venv venv
.\venv\Scripts\activate  # Windows

# 의존성 설치
pip install mcp anthropic pillow python-dotenv python-docx
```

## ⚙️ 설정

1. `mcp_config.template.json`을 복사하여 `mcp_config.json` 생성
2. `YOUR_ANTHROPIC_API_KEY_HERE`를 실제 API 키로 교체

## 🔒 보안

`.env`, `mcp_config.json` 파일은 `.gitignore`에 포함됨 (API 키 보호)
