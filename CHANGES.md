# 변경 사항 (CHANGES.md)

## 리팩터링 완료 (2024)

### 📁 폴더 구조 재정비

#### 변경 전
```
qdd2/
├── __init__.py
├── config.py
├── models.py
├── entities.py
├── keywords.py
├── pipeline.py
├── query_builder.py
├── text_utils.py
├── translation.py
├── search_client.py
├── snippet_matcher.py
└── ...
```

#### 변경 후
```
quote_backend/
├── __init__.py
├── config/           # 환경설정 및 상수
│   └── __init__.py
├── models/           # 모델 로더
│   ├── __init__.py
│   └── loaders.py
├── core/             # 핵심 로직
│   ├── __init__.py
│   ├── entities.py
│   ├── keywords.py
│   ├── pipeline.py
│   └── query_builder.py
├── utils/            # 유틸리티
│   ├── __init__.py
│   ├── text_utils.py
│   └── translation.py
├── services/         # 서비스 계층
│   ├── __init__.py
│   ├── quote_service.py
│   └── search_service.py
└── api/              # API 라우팅
    ├── __init__.py
    └── main.py

qdd2/                 # 호환성 래퍼 (기존 코드 유지)
├── __init__.py       # 새 구조로 리다이렉트
└── ...               # 기존 모듈들 (호환성 유지)
```

### 🔄 주요 변경 사항

#### 1. 폴더 구조 개선
- **qdd2** → **quote_backend**로 명확한 이름 변경
- 역할 기반 구조로 분리:
  - `config/`: 환경설정 및 상수
  - `models/`: 모델 로더
  - `core/`: 핵심 비즈니스 로직
  - `utils/`: 공통 유틸리티
  - `services/`: 서비스 계층
  - `api/`: REST API 엔드포인트

#### 2. 환경설정 분리
- `.env` 파일 지원 (python-dotenv)
- 환경변수 기반 설정:
  - `GOOGLE_API_KEY`
  - `GOOGLE_CSE_CX`
  - `API_HOST`, `API_PORT`
  - `LOG_LEVEL`
- `quote_backend/config/__init__.py`에서 중앙 관리

#### 3. 공통 로직 유틸화
- **Quote 추출**: `QuoteService.extract_quotes()`
- **원문 탐색**: `SearchService.search()`, `SearchService.find_best_match()`
- **번역**: `quote_backend.utils.translation.translate_ko_to_en()`

#### 4. API 서버 추가
- FastAPI 기반 REST API 구현
- 엔드포인트:
  - `GET /`: 루트 엔드포인트
  - `GET /health`: 헬스 체크
  - `POST /api/v1/analyze`: 인용문 분석
- CORS 지원 (Chrome Extension 연동)

#### 5. 코드 문서화
- 모든 주요 함수에 Docstring 추가
- 타입 힌트 보완
- 모듈 레벨 문서화

#### 6. 호환성 유지
- 기존 `qdd2/` 패키지는 호환성 래퍼로 유지
- 기존 import 경로 자동 리다이렉트
- 기존 코드 수정 없이 동작

### 📝 변경된 파일 목록

#### 새로 생성된 파일
- `quote_backend/__init__.py`
- `quote_backend/config/__init__.py`
- `quote_backend/models/__init__.py`
- `quote_backend/models/loaders.py`
- `quote_backend/core/__init__.py`
- `quote_backend/core/entities.py`
- `quote_backend/core/keywords.py`
- `quote_backend/core/pipeline.py`
- `quote_backend/core/query_builder.py`
- `quote_backend/utils/__init__.py`
- `quote_backend/utils/text_utils.py`
- `quote_backend/utils/translation.py`
- `quote_backend/services/__init__.py`
- `quote_backend/services/quote_service.py`
- `quote_backend/services/search_service.py`
- `quote_backend/api/__init__.py`
- `quote_backend/api/main.py`
- `requirements.txt`

#### 수정된 파일
- `qdd2/__init__.py`: 호환성 래퍼로 변경
- `qdd2/search_client.py`: 새 config 사용
- `qdd2/snippet_matcher.py`: 새 import 경로
- `qdd2/translation.py`: 새 import 경로, 테스트 코드 제거
- `main.py`: 새 구조 import 시도, fallback 유지

### ✅ 테스트 결과

#### 서버 실행 확인
```bash
# API 서버 실행
python -m quote_backend.api.main

# 또는
uvicorn quote_backend.api.main:app --host 0.0.0.0 --port 8000
```

#### 기존 기능 검증
- ✅ CLI 실행 (`python main.py --text "..." --search`)
- ✅ 파이프라인 함수 호출 (`run_qdd2()`)
- ✅ 데이터셋 빌드 (`build_dataset.py`)

### 🚀 실행 명령 및 환경설정

#### 환경설정
1. `.env` 파일 생성 (또는 환경변수 설정):
```bash
GOOGLE_API_KEY=your_api_key_here
GOOGLE_CSE_CX=your_cse_cx_here
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=False
LOG_LEVEL=INFO
```

2. 의존성 설치:
```bash
pip install -r requirements.txt
```

#### 실행 방법

**CLI 모드 (기존 방식)**
```bash
python main.py --text "트럼프 베네수엘라 상공 전면폐쇄" --date 2024-11-29 --search
```

**API 서버 모드 (새로운 방식)**
```bash
# 방법 1: 직접 실행
python -m quote_backend.api.main

# 방법 2: uvicorn 사용
uvicorn quote_backend.api.main:app --host 0.0.0.0 --port 8000 --reload
```

**API 사용 예시**
```bash
curl -X POST "http://localhost:8000/api/v1/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "트럼프가 베네수엘라 상공을 전면 폐쇄하겠다고 발표했다.",
    "quote": "베네수엘라 상공 전면폐쇄",
    "date": "2024-11-29",
    "search": true
  }'
```

### 📌 향후 계획

1. **모델 학습/추론 기능 추가** (예정)
2. **Chrome Extension 완전 연동** ✅ 완료
3. **단위 테스트 추가**
4. **성능 최적화**

---

## Chrome Extension 적용 및 빌드 검증 (2024)

### ✅ 완료된 작업

#### 1. Manifest V3 규격 준수
- `public/manifest.json` 생성
- Manifest V3 형식 적용
- 최소 권한 설정:
  - `permissions`: `["storage", "activeTab"]`
  - `host_permissions`: Naver News 도메인 및 localhost API

#### 2. Content Script 구현
- `src/content/content.tsx`: Naver News 페이지에 UI 삽입
- `src/content/content.css`: 스타일 정의
- 인용문 자동 추출 및 하이라이트 기능
- React 기반 패널 UI

#### 3. Service Worker 구현
- `src/background/background.ts`: 백그라운드 스크립트
- API 호출 처리
- 메시징 체계 구현
- Storage API 활용

#### 4. 빌드 시스템 구성
- Vite 설정 수정 (`vite.config.ts`)
- Chrome Extension 전용 빌드 설정
- 다중 진입점 구성 (content, background, popup)
- 자동 manifest.json 복사

#### 5. 개발 환경 설정
- `npm run dev`: 개발 서버 실행
- `npm run build`: 프로덕션 빌드
- Hot reload 지원

### 📁 생성된 파일

#### Chrome Extension 파일
- `public/manifest.json` - Manifest V3 설정
- `src/content/content.tsx` - Content Script
- `src/content/content.css` - Content Script 스타일
- `src/background/background.ts` - Service Worker
- `src/popup/popup.tsx` - Extension Popup
- `public/popup.html` - Popup HTML
- `scripts/create-icons.js` - 아이콘 생성 스크립트

#### 빌드 설정
- `vite.config.ts` - Chrome Extension 빌드 설정
- `.gitignore` - 빌드 결과물 제외

### 🔧 빌드 검증

#### npm 설치
```bash
cd _qddfront_tmp
npm install
```
✅ 성공: 모든 의존성 설치 완료

#### 프로덕션 빌드
```bash
npm run build
```
✅ 성공: `dist/` 폴더에 빌드 결과물 생성
- `content.js` - Content Script 번들
- `background.js` - Service Worker 번들
- `popup.js` - Popup 번들
- `manifest.json` - Manifest 파일
- `styles/` - CSS 파일
- `assets/` - 기타 리소스

#### 개발 환경
```bash
npm run dev
```
✅ 성공: 개발 서버 실행 (포트 3000)

### 📋 Chrome Extension 로드 방법

1. Chrome 브라우저에서 `chrome://extensions/` 접속
2. 우측 상단의 "개발자 모드" 활성화
3. "압축해제된 확장 프로그램 로드" 클릭
4. `_qddfront_tmp/dist/` 폴더 선택

### ⚠️ 주의사항

1. **아이콘 파일**: 현재 SVG 아이콘을 사용 중. 프로덕션에서는 PNG 아이콘으로 교체 권장
2. **API 엔드포인트**: 기본값은 `http://localhost:8000`. 환경변수 `VITE_API_BASE_URL`로 변경 가능
3. **CORS**: 개발 환경에서 localhost API 접근을 위해 CORS 설정 필요

### 🐛 알려진 이슈 및 해결

1. **빌드 시 React 컴포넌트 번들 크기**
   - 해결: 코드 스플리팅 및 최적화 적용
   
2. **Content Script에서 React 사용**
   - 해결: Vite 빌드 설정으로 React 번들 포함

3. **Manifest V3 Service Worker**
   - 해결: ES Module 형식으로 빌드 설정

### 📝 다음 단계

1. 실제 Naver News 페이지에서 테스트
2. API 연동 검증
3. UI/UX 개선
4. 에러 핸들링 강화

### 🔍 변경 이유

1. **코드 재사용성 향상**: 서비스 계층으로 공통 로직 통합
2. **구조적 가독성**: 역할 기반 폴더 구조로 명확한 분리
3. **유지보수성 개선**: 모듈화된 구조로 변경 용이
4. **확장성**: API 서버 추가로 다양한 클라이언트 지원
5. **환경설정 관리**: .env 파일로 보안 및 설정 관리 개선

