# MCP 콘텐츠 자동화 서버

광고주 페르소나 기반 콘텐츠 자동 생성 MCP 서버 3종 세트

## 🎯 서버 구성

| 서버 | 역할 | 주요 도구 |
|------|------|----------|
| **persona-manager** | 카톡 대화 분석 → 페르소나 생성 | `onboard_new_client`, `list_all_clients` |
| **visual-persona-extractor** | 이미지 분석 → 시각 스타일 추출 | `extract_visual_persona_from_images` |
| **content-automation** | 페르소나 기반 콘텐츠 생성 | `generate_blog_post`, `generate_cardnews_script` |

## 📦 설치

```bash
# 가상환경 생성 및 활성화
python -m venv venv
.\venv\Scripts\activate  # Windows

# 의존성 설치
pip install mcp anthropic pillow python-dotenv
```

## ⚙️ 설정

1. `mcp_config.template.json`을 복사하여 `mcp_config.json` 생성
2. `YOUR_ANTHROPIC_API_KEY_HERE`를 실제 API 키로 교체
3. Cursor/Claude Desktop 설정에 `mcp_config.json` 내용 추가

## 🧪 테스트

```bash
$env:PYTHONIOENCODING='utf-8'
.\venv\Scripts\python.exe test_servers.py
```

## 📁 데이터 저장 위치

모든 데이터는 `~/mcp-data/` 에 저장됨:
- `personas/` - 텍스트 페르소나
- `visual-personas/` - 시각 페르소나
- `outputs/` - 생성된 콘텐츠

## 🔒 보안

`.env`, `mcp_config.json` 파일은 `.gitignore`에 포함됨 (API 키 보호)
