# 📁 Static 파일 구조

리팩토링된 프론트엔드 파일 구조입니다.

## 📂 디렉토리 구조

```
static/
├── css/
│   └── styles.css          # 메인 스타일시트 (640줄)
│
├── js/
│   ├── diagram.js          # 시스템 아키텍처 다이어그램 (160줄)
│   ├── vectordb.js         # VectorDB 관리 (60줄)
│   ├── analysis.js         # 기업 분석 메인 로직 (200줄)
│   └── main.js             # 초기화 및 유틸리티 (20줄)
│
└── [이미지 파일들]
    ├── 01_KT Wordmark (Standard)_01.png
    ├── KT VI White_1.png
    ├── KT VI White_2.png
    ├── KT VI White_3.png
    └── KT VI White_4.png
```

## 📄 파일 설명

### 🎨 CSS

#### `styles.css` (640줄)
- **용도**: 전체 애플리케이션의 스타일 정의
- **주요 섹션**:
  - 기본 레이아웃 및 타이포그래피
  - KT 브랜드 색상 (#E30613)
  - 폼 및 버튼 스타일
  - 로딩 애니메이션
  - 결과 표시 (Markdown 렌더링)
  - 아키텍처 다이어그램 스타일
  - 반응형 디자인 (모바일)

---

### 💻 JavaScript 모듈

#### `diagram.js` (160줄)
**용도**: 시스템 아키텍처 실시간 모니터링

**주요 기능**:
- `architectureDiagram`: 컴포넌트 관리 객체
  - `activate()`: 컴포넌트 활성화
  - `deactivate()`: 컴포넌트 비활성화
  - `reset()`: 모든 컴포넌트 초기화
- `updateDiagramFromMessage()`: 로그 메시지 파싱 후 다이어그램 업데이트

**관리 컴포넌트**:
- Frontend, Flask Server, DART API, Naver Finance
- VectorDB, Midm AI, Gemini AI

---

#### `vectordb.js` (60줄)
**용도**: VectorDB 관리 기능

**주요 함수**:
- `loadVectorDBStats()`: VectorDB 통계 조회 및 표시
  - 총 보고서 수
  - 총 청크 수
  - 총 데이터 크기
  - 저장된 회사 목록
- `resetVectorDB()`: VectorDB 초기화 (확인 후)

---

#### `analysis.js` (200줄)
**용도**: 기업 분석 메인 로직

**주요 함수**:
- `handleAnalysisSubmit()`: 분석 폼 제출 처리
  - POST 요청 전송
  - SSE 스트림 연결
  - 실시간 상태 업데이트
- `fetchAnalysisResult()`: 분석 결과 조회
- `displayAnalysisResult()`: 결과 화면 표시
- `displayReportsList()`: 보고서 목록 렌더링
  - DART 공시 보고서
  - 추가 DART 보고서
  - 네이버 종목분석 리포트
  - 네이버 산업분석 리포트
- `addStatusMessage()`: 상태 로그 메시지 추가
- `downloadPDF()`: PDF 다운로드

**전역 변수**:
- `currentSessionId`: 현재 분석 세션 ID

---

#### `main.js` (20줄)
**용도**: 애플리케이션 초기화

**주요 기능**:
- DOM 로드 시 초기화
- 이벤트 리스너 등록
- VectorDB 통계 자동 로드
- `setQuery()`: 예시 질문 입력 헬퍼

---

## 🔄 데이터 흐름

```
1. 사용자 입력 (main.js)
   ↓
2. 폼 제출 (analysis.js - handleAnalysisSubmit)
   ↓
3. Flask 서버로 POST 요청
   ↓
4. SSE 스트림 연결 (분석 진행상황 수신)
   ↓
5. 상태 로그 업데이트 (analysis.js - addStatusMessage)
   ↓
6. 다이어그램 업데이트 (diagram.js - updateDiagramFromMessage)
   ↓
7. 분석 완료 후 결과 조회
   ↓
8. 결과 화면 표시 (analysis.js - displayAnalysisResult)
```

---

## 🎯 리팩토링 효과

### Before (1,283줄)
```
templates/index.html  (1,283줄)
├── <style>           (640줄)
└── <script>          (600줄)
```

### After (214줄)
```
templates/
└── index.html        (214줄) ✨ 83% 감소

static/
├── css/
│   └── styles.css    (640줄)
└── js/
    ├── diagram.js    (160줄)
    ├── vectordb.js   (60줄)
    ├── analysis.js   (200줄)
    └── main.js       (20줄)
```

### 장점
✅ **가독성 향상**: HTML이 214줄로 간소화
✅ **유지보수 용이**: 기능별로 모듈 분리
✅ **재사용성**: 독립적인 JavaScript 모듈
✅ **캐싱**: 브라우저가 CSS/JS 파일 캐시 가능
✅ **협업**: 팀원이 각 파일 독립적으로 작업 가능
✅ **확장성**: 새로운 기능 추가 시 해당 모듈만 수정

---

## 🚀 사용법

### HTML에서 파일 로드
```html
<!-- CSS -->
<link rel="stylesheet" href="/static/css/styles.css">

<!-- JavaScript (순서 중요!) -->
<script src="/static/js/diagram.js"></script>
<script src="/static/js/vectordb.js"></script>
<script src="/static/js/analysis.js"></script>
<script src="/static/js/main.js"></script>
```

### 의존성 관계
```
main.js (초기화)
  ↓ 호출
vectordb.js (통계 로드)

main.js (이벤트 등록)
  ↓ 호출
analysis.js (분석 로직)
  ↓ 호출
diagram.js (다이어그램 업데이트)
```

---

## 📝 추가 개선 사항 (향후)

- [ ] ES6 모듈 시스템 사용 (`import`/`export`)
- [ ] TypeScript 변환
- [ ] Webpack 번들링
- [ ] 단위 테스트 추가
- [ ] JSDoc 주석 보강
- [ ] Linter 설정 (ESLint)

---

**작성일**: 2025-10-28
**버전**: 2.0 (리팩토링)

