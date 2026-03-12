# Review And Upgrades

## Review Summary

이번 점검은 `C:\work\mcp` 전체를 기준으로 CLI, 웹 대시보드, MCP 서버, 자료 추출 레이어를 병렬로 읽고 실제 실행까지 확인한 뒤 진행했다.

핵심 결론은 다음과 같았다.

1. 블로그 저장 포맷이 CLI와 웹에서 달라서 같은 산출물을 서로 다르게 해석하고 있었다.
2. JPG/PNG 홍보물은 사실상 텍스트가 되지 않아 "홍보물 받으면 블로그 작성" 요구를 충족하지 못했다.
3. 웹 생성기는 단일 파일만 받아서 PDF + 전단지 + 보조 자료를 한 번에 묶어 쓰기 어려웠다.
4. `GEMINI_API_KEY`가 없으면 페르소나 추출과 블로그 생성이 모두 멈춰 실사용성이 크게 떨어졌다.
5. `blog_pull`이 비어 있으면 `web/app.py` 자체 import가 실패해 핵심 기능까지 함께 죽었다.
6. MCP 서버 패키지 설정은 아직 `anthropic` 기준으로 남아 있었고, 엔트리포인트 `main()`도 빠져 있었다.

## What Was Tested

직접 확인한 실행 흐름:

1. `web /api/persona/extract`
   - 입력: `input/1_personas/부산항만공사_김철수주무관.txt`
   - 결과: `Busan_Port_Kim_Test_2.json` 생성 확인
   - 모드: `offline`

2. `web /api/blog/generate`
   - 입력: `input/2_blog_writing/진주시청/2026학년도 전문기술과정 모집요강(최종).pdf`
   - 추가 입력: `input/3_oneclick/모집안내.jpg`
   - 결과: 3버전 블로그 패키지 JSON 생성 확인
   - 모드: `offline`

3. `web /api/blog/save`
   - 생성된 첫 번째 버전 본문을 수정 저장
   - 결과: 기존 `BLOG_*.json` 패키지 내부 버전이 실제로 갱신되는 것 확인

4. `run_blog_generator.generate_blog_post`
   - 같은 PDF + 이미지 OCR 텍스트를 결합해 직접 호출
   - 결과: Markdown 및 DOCX 생성 확인

## Upgrades Applied

### 1. Storage Unified

- `blog_storage.py` 추가
- 단일 버전 `content`와 다중 버전 `versions`를 모두 정규화
- 웹/CLI/MCP 서버가 같은 블로그 패키지 구조를 저장하도록 통일
- 수정 저장 시 별도 임시 JSON을 남기지 않고 원본 패키지 내부 버전을 갱신하도록 변경

### 2. Multi-Material Pipeline Added

- `material_pipeline.py` 추가
- 여러 파일의 텍스트를 하나의 `source_bundle`로 통합
- 자료별 글자 수, 핵심 포인트, 일정/문의 라인을 함께 저장
- 웹 응답에도 어떤 자료가 사용됐는지 표시되도록 변경

### 3. Offline Fallback Added

- `offline_engines.py` 추가
- API 키가 없거나 AI 호출이 실패해도:
  - 페르소나를 휴리스틱으로 생성
  - 블로그 3버전 초안을 생성
- 결과적으로 시스템이 "아예 멈추는 상태"에서 "초안이라도 항상 나오는 상태"로 바뀜

### 4. OCR And Scanned Material Support Improved

- `utils.py` 확장
- 이미지 파일에 OCR 적용
- 텍스트가 거의 없는 스캔 PDF는 이미지 OCR로 보완
- 이 환경에서는 `rapidocr_onnxruntime` 설치 후 JPG 홍보물 추출을 확인함

### 5. Web Workflow Upgraded

- `web/index.html`
  - 여러 파일 업로드 가능하도록 수정
  - PDF, DOCX, HWP, JPG, PNG 지원 문구 반영

- `web/app.js`
  - 여러 파일 drag/drop 및 선택 지원
  - 업로드 파일 목록 표시
  - 생성 결과에 입력 자료와 생성 모드 표시
  - 저장 시 `output_id`를 넘겨 원본 패키지 업데이트 가능하게 수정

- `web/app.py`
  - 페르소나 추출 오프라인 fallback 적용
  - 블로그 생성 다중 파일 처리 적용
  - 저장 패키지 통일
  - `blog_pull`이 없어도 앱이 뜨도록 optional import 처리

### 6. CLI And MCP Consistency Improved

- `run_persona_test.py`
  - 오프라인 페르소나 분석 지원

- `run_blog_generator.py`
  - 오프라인 초안 생성 지원
  - 공통 블로그 패키지 저장 구조 적용

- `mcp-servers/content-automation/server.py`
  - 공통 저장 구조 적용
  - 오프라인 초안 fallback 적용

- `persona-manager/server.py`
- `mcp-servers/visual-persona-extractor/server.py`
- `mcp-servers/design-guide/server.py`
  - `main()` 엔트리포인트 추가

- `persona-manager/pyproject.toml`
- `mcp-servers/content-automation/pyproject.toml`
- `mcp-servers/visual-persona-extractor/pyproject.toml`
  - `anthropic` 의존성을 `google-genai` 기준으로 정리

## Residual Risks

1. 이미지 OCR은 동작하지만, 글자가 작거나 복잡한 전단지는 추출 품질이 거칠 수 있다.
2. `blog_pull` 수집 기능은 현재 폴더가 비어 있어 이번 업그레이드에서 "앱 전체 다운 방지"까지만 처리했다.
3. 오프라인 생성기는 실사용 가능한 초안을 만드는 수준이며, API 키가 연결되면 완성도는 더 높아진다.
