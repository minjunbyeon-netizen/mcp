# 페르소나 기반 블로그 생성 시스템

## 🎯 주요 기능

### 1. 페르소나별 독립적인 학습 시스템
- 각 페르소나마다 **독립적인 버전 관리**
- 사용자 피드백 기반 **자동 업그레이드**
- 페르소나별 **맞춤형 블로그 작성 설정**

### 2. 버전 관리
```
output/personas/
├── 남구청_박미혜_주무관_v1.json    # 초기 버전
├── 남구청_박미혜_주무관_v2.json    # 1차 업그레이드
├── 남구청_박미혜_주무관_v3.json    # 2차 업그레이드
└── 남구청_박미혜_주무관_feedback.json  # 피드백 히스토리
```

### 3. 자동 학습 프로세스
```
블로그 생성 → 사용자 평가 (1-5점) → 문제점 파악 → 자동 조정 → 새 버전 생성
```

---

## 📝 사용 방법

### 1️⃣ 페르소나 생성
```bash
python run_persona_test.py
```
- 카카오톡 대화 내용 분석
- 페르소나 자동 생성 (격식도, 말투, 이모티콘 사용 등)
- `blog_writing_config` 자동 생성

### 2️⃣ 블로그 글 생성
```bash
python run_blog_generator.py
```

**프로세스:**
1. 페르소나 선택 (최신 버전 자동 로드)
2. 보도자료 선택
3. SEO 키워드 입력 (선택)
4. AI가 페르소나 스타일로 블로그 작성
5. **피드백 수집**
   - 평점 입력 (1-5점)
   - 문제점 선택 (말투, 길이, 이모티콘 등)
   - 자동 조정 및 새 버전 생성

### 3️⃣ 학습 리포트 확인
```bash
python run_persona_report.py
```

**확인 가능한 정보:**
- 총 생성 블로그 수
- 평균 만족도
- 개선 추세 (최근 5개 vs 전체 평균)
- 주요 피드백 이슈
- 버전별 변경 내역
- 현재 블로그 설정

---

## 🔧 피드백 시스템

### 평가 항목
1. **완벽해요!** ⭐⭐⭐⭐⭐ → 현재 설정 유지
2. **좋아요** ⭐⭐⭐⭐ → 피드백 기록
3. **괜찮아요** ⭐⭐⭐ → 문제점 파악
4. **아쉬워요** ⭐⭐ → 자동 조정 제안
5. **다시 써주세요** ⭐ → 즉시 개선 필요

### 자동 조정 항목
| 피드백 | 자동 조정 |
|--------|----------|
| 말투/어미가 안 맞아요 | 격식도 +1 |
| 너무 길어요 | max_length: 1500, paragraph: short |
| 너무 짧아요 | max_length: 2500, paragraph: medium |
| 이모티콘 과다 | emoji_positions: [intro, outro] |
| 이모티콘 부족 | emoji_positions: [intro, body, outro] |
| 문장이 너무 길어요 | sentence_length: short |
| 전문용어가 어려워요 | technical_terms: avoid |

---

## 📊 blog_writing_config 구조

```json
{
  "structure": {
    "intro_style": "polite_question",
    "body_sections": 3,
    "use_subsections": true,
    "outro_cta": "engagement"
  },
  "formatting": {
    "header_format": "bracket",
    "emphasis_markers": ["**bold**", "『quote』"],
    "use_dividers": true,
    "divider_style": "• • • • •",
    "image_placeholders": true,
    "emoji_positions": ["intro", "outro"]
  },
  "tone_details": {
    "sentence_ending_examples": ["~해요", "~이에요", "~네요"],
    "prohibited_endings": ["~한다", "~이다"],
    "punctuation_style": "friendly",
    "emoji_examples": ["^^", "😊", "~"]
  },
  "content_rules": {
    "min_length": 1500,
    "max_length": 2000,
    "paragraph_length": "short",
    "keyword_density": "natural",
    "technical_terms": "simplify",
    "examples_required": true,
    "statistics_format": "bold_highlight"
  },
  "seo_preferences": {
    "title_format": "balanced",
    "title_max_length": 60,
    "meta_description_style": "summary",
    "tag_count": 5,
    "tag_style": "specific"
  }
}
```

---

## 🚀 고급 기능

### 수동 설정 조정
페르소나 JSON 파일을 직접 편집하여 `blog_writing_config` 수정 가능

### 버전 비교
```bash
python run_persona_report.py
```
- 모든 버전의 변경 내역 확인
- 버전별 만족도 비교
- 개선 추세 분석

### 마이그레이션
기존 페르소나 파일에 버전 정보 추가:
```bash
python migrate_personas.py
```

---

## 📁 파일 구조

```
03_mcp_test/
├── run_persona_test.py          # 페르소나 생성
├── run_blog_generator.py        # 블로그 생성 + 피드백
├── run_persona_report.py        # 학습 리포트
├── persona_version_manager.py   # 버전 관리 시스템
├── migrate_personas.py          # 마이그레이션 도구
│
├── output/
│   ├── personas/
│   │   ├── {client_id}_v1.json
│   │   ├── {client_id}_v2.json
│   │   ├── {client_id}_v3.json
│   │   └── {client_id}_feedback.json
│   │
│   └── blog/
│       └── {persona}_{title}_{date}.docx
│
└── input/
    └── 2_blog_writhing/
        └── [보도자료 파일들]
```

---

## 💡 사용 예시

### 시나리오: 박미혜 주무관 페르소나

**1차 블로그 생성 (v1)**
- 격식도: 7/10
- 이모티콘: 모든 위치
- 평가: 3점 (이모티콘 너무 많음)

**자동 업그레이드 → v2**
- emoji_positions: [intro, outro]만 사용
- 다음 블로그부터 적용

**2차 블로그 생성 (v2)**
- 개선된 설정으로 작성
- 평가: 5점 (완벽!)

**결과**
- v2 설정 유지
- 평균 만족도: 4.0 → 개선 추세 확인

---

## 🎓 학습 통계 예시

```
📊 박미혜 주무관 학습 리포트
============================================================
📈 학습 통계:
   총 생성 블로그: 10개
   평균 만족도: 4.3/5 ⭐
   개선 추세: +0.8 📈 (최근 5개가 전체 평균보다 높음)

🔧 주요 피드백 이슈:
   - 이모티콘 과다: 3회
   - 글이 너무 깁: 2회
   - 말투/어미: 1회

📝 버전 히스토리:
   v1 (2026-01-05) - 초기 버전
   v2 (2026-01-10) - 이모티콘 과다, 글이 너무 깁
   v3 (2026-01-15) - 말투/어미
```

---

## ⚙️ 설정 가이드

### 격식도별 기본 설정

**격식도 8-10 (매우 공식적)**
- 말투: ~습니다, ~입니다
- 이모티콘: 사용 안 함
- 문장: 중간 길이
- 전문용어: 유지

**격식도 6-7 (정중하고 친근함)**
- 말투: ~해요 70% + ~습니다 30%
- 이모티콘: 시작/끝
- 문장: 짧음
- 전문용어: 쉽게 풀어쓰기

**격식도 4-5 (편안함)**
- 말투: ~해요
- 이모티콘: 자유롭게
- 문장: 짧음
- 전문용어: 피하기

**격식도 1-3 (매우 캐주얼)**
- 말투: 반말 가능
- 이모티콘: ㅋㅋ, ㅎㅎ 포함
- 문장: 짧음
- 전문용어: 피하기

---

## 🔄 업데이트 로그

### v2.0 (2026-01-20)
- ✅ 페르소나별 독립적인 버전 관리 시스템
- ✅ 피드백 기반 자동 업그레이드
- ✅ blog_writing_config 자동 생성
- ✅ 학습 리포트 기능
- ✅ 버전 비교 기능

### v1.0 (2026-01-05)
- 페르소나 기반 블로그 생성
- 기본 프롬프트 시스템
