# Quote Detection Backend

신문 인용 왜곡 탐지를 위한 백엔드 API 서버입니다. 기사 텍스트에서 인용문을 추출하고, 원문을 검색하여 인용 왜곡을 탐지합니다.

## 📋 목차

- [개요](#개요)
- [프로젝트 구조](#프로젝트-구조)
- [설치 및 설정](#설치-및-설정)
- [사용 방법](#사용-방법)
- [API 문서](#api-문서)
- [개발 가이드](#개발-가이드)

## 🎯 개요

이 프로젝트는 다음과 같은 기능을 제공합니다:

- **인용문 추출**: 기사 텍스트에서 인용문 자동 추출
- **엔티티 및 키워드 추출**: NER 기반 엔티티 추출 및 키워드 추출
- **검색 쿼리 생성**: 한국어/영어 검색 쿼리 자동 생성
- **원문 탐색**: Google CSE 및 Rollcall.com을 통한 원문 검색
- **유사도 매칭**: SBERT 기반 유사도 계산으로 최적 원문 매칭

## 📁 프로젝트 구조

```
quote_backend/
├── config/           # 환경설정 및 상수
│   └── __init__.py
├── models/           # 모델 로더 (NER, KeyBERT, Translation, SBERT)
│   ├── __init__.py
│   └── loaders.py
├── core/             # 핵심 비즈니스 로직
│   ├── entities.py      # NER 엔티티 추출
│   ├── keywords.py      # 키워드 추출 및 재순위화
│   ├── pipeline.py      # 파이프라인 오케스트레이션
│   └── query_builder.py # 검색 쿼리 생성
├── utils/            # 공통 유틸리티
│   ├── text_utils.py    # 텍스트 처리 (정규화, 문장 분리, 인용문 추출)
│   └── translation.py   # 한국어→영어 번역
├── services/         # 서비스 계층
│   ├── quote_service.py  # 인용문 처리 서비스
│   └── search_service.py # 검색 및 매칭 서비스
└── api/              # REST API
    └── main.py          # FastAPI 애플리케이션

qdd2/                 # 호환성 래퍼 (기존 코드와의 호환성 유지)
├── __init__.py
├── search_client.py
├── snippet_matcher.py
└── ...
```

## 🚀 설치 및 설정

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 환경변수 설정

`.env` 파일을 생성하거나 환경변수를 설정합니다:

```bash
# Google Custom Search API
GOOGLE_API_KEY=your_google_api_key_here
GOOGLE_CSE_CX=your_cse_cx_here

# API 서버 설정
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=False

# 로깅
LOG_LEVEL=INFO

# 모델 설정
DEFAULT_DEVICE=0  # 0: CPU, >0: GPU
```

### 3. 모델 다운로드

첫 실행 시 필요한 모델이 자동으로 다운로드됩니다:
- NER 모델: `monologg/koelectra-base-v3-naver-ner`
- KeyBERT 모델: `snunlp/KR-SBERT-V40K-klueNLI-augSTS`
- 번역 모델: `Helsinki-NLP/opus-mt-ko-en`
- SBERT 모델: `sentence-transformers/all-mpnet-base-v2`

## 💻 사용 방법

### CLI 모드 (기존 방식)

```bash
python main.py --text "트럼프가 베네수엘라 상공을 전면 폐쇄하겠다고 발표했다." \
  --quote "베네수엘라 상공 전면폐쇄" \
  --date 2024-11-29 \
  --search
```

옵션:
- `--text`: 분석할 텍스트
- `--file`: 텍스트 파일 경로
- `--quote`: 특정 인용문 (선택)
- `--date`: 기사 날짜 (YYYY-MM-DD)
- `--top-n`: 추출할 키워드 수 (기본: 15)
- `--top-k`: 쿼리에 사용할 키워드 수 (기본: 3)
- `--rollcall`: Rollcall.com 모드 사용
- `--search`: 웹 검색 실행
- `--debug`: 디버그 모드

### Python API 사용

```python
from quote_backend.core.pipeline import build_queries_from_text
from quote_backend.services.quote_service import QuoteService
from quote_backend.services.search_service import SearchService

# 인용문 추출
quotes = QuoteService.extract_quotes(article_text)

# 파이프라인 실행
result = build_queries_from_text(
    text=article_text,
    quote_sentence=quote,
    article_date="2024-11-29",
    top_n_keywords=15,
    top_k_for_query=3,
)

# 검색 및 매칭
search_items = SearchService.search(
    query=result["queries"]["en"],
    is_trump_context=True,
    rollcall=True,
)
best_match = SearchService.find_best_match(
    quote_text=quote,
    search_items=search_items,
)
```

### API 서버 모드

#### 서버 실행

```bash
# 방법 1: 직접 실행
python -m quote_backend.api.main

# 방법 2: uvicorn 사용
uvicorn quote_backend.api.main:app --host 0.0.0.0 --port 8000 --reload
```

#### API 사용 예시

```bash
# 헬스 체크
curl http://localhost:8000/health

# 인용문 분석
curl -X POST "http://localhost:8000/api/v1/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "트럼프가 베네수엘라 상공을 전면 폐쇄하겠다고 발표했다.",
    "quote": "베네수엘라 상공 전면폐쇄",
    "date": "2024-11-29",
    "search": true,
    "rollcall": true
  }'
```

## 📚 API 문서

### 엔드포인트

#### `GET /`
루트 엔드포인트

**응답:**
```json
{
  "message": "Quote Detection Backend API",
  "version": "1.0.0",
  "status": "running"
}
```

#### `GET /health`
헬스 체크

**응답:**
```json
{
  "status": "healthy"
}
```

#### `POST /api/v1/analyze`
인용문 분석

**요청 본문:**
```json
{
  "text": "기사 텍스트",
  "quote": "인용문 (선택)",
  "date": "2024-11-29",
  "top_n": 15,
  "top_k": 3,
  "rollcall": false,
  "search": true,
  "device": 0
}
```

**응답:**
```json
{
  "pipeline_result": {
    "entities": [...],
    "keywords": [...],
    "entities_by_type": {...},
    "queries": {
      "ko": "...",
      "en": "..."
    }
  },
  "search_items": [...],
  "best_span": {
    "url": "...",
    "best_score": 0.85,
    "best_sentence": "...",
    "span_text": "..."
  },
  "is_trump_context": false
}
```

API 문서는 서버 실행 후 `http://localhost:8000/docs`에서 확인할 수 있습니다.

## 🛠 개발 가이드

### 코드 구조

- **config/**: 환경설정 및 상수 관리
- **models/**: 모델 로더 (lazy loading)
- **core/**: 핵심 비즈니스 로직
- **utils/**: 공통 유틸리티 함수
- **services/**: 서비스 계층 (비즈니스 로직 캡슐화)
- **api/**: REST API 엔드포인트

### 호환성

기존 `qdd2` 패키지를 사용하는 코드는 자동으로 새 구조로 리다이렉트됩니다:

```python
# 기존 코드 (여전히 동작)
from qdd2.pipeline import build_queries_from_text
from qdd2.translation import translate_ko_to_en

# 새 코드 (권장)
from quote_backend.core.pipeline import build_queries_from_text
from quote_backend.utils.translation import translate_ko_to_en
```

### 테스트

```bash
# CLI 테스트
python main.py --text "테스트 텍스트" --debug

# API 테스트
python -m quote_backend.api.main
curl http://localhost:8000/health
```

## 📝 변경 사항

자세한 변경 사항은 [CHANGES.md](CHANGES.md)를 참조하세요.

## 🔮 향후 계획

- [ ] 모델 학습/추론 기능 추가
- [ ] Chrome Extension 완전 연동
- [ ] 단위 테스트 추가
- [ ] 성능 최적화
- [ ] 배포 자동화

## 📄 라이선스

이 프로젝트의 라이선스 정보는 별도로 명시되지 않았습니다.

## 🤝 기여

이슈 및 풀 리퀘스트를 환영합니다.
