# 📐 UML 다이어그램

이 폴더에는 기업 분석 AI 시스템의 UML 다이어그램들이 포함되어 있습니다.

## 📄 파일 목록

### 1. `class_diagram.puml` - 클래스 다이어그램
- 시스템의 주요 클래스와 관계
- 메서드 및 속성 정의
- 패키지 구조

**주요 클래스:**
- `FlaskApp` - 웹 서버
- `CompanyAnalyzer` - 핵심 분석 엔진
- `NaverFinanceCrawler` - 증권사 리포트 크롤러
- `VectorStore` - 벡터 데이터베이스

### 2. `sequence_diagram.puml` - 시퀀스 다이어그램
- 전체 분석 프로세스의 흐름
- 각 컴포넌트 간 상호작용
- VectorDB 캐싱 로직

**주요 단계:**
1. 회사 정보 조회
2. DART 공시 보고서 수집
3. 증권사 리포트 수집 (종목분석 + 산업분석)
4. VectorDB 캐싱 체크
5. Gemini AI 종합 분석
6. 결과 반환

### 3. `architecture_diagram.puml` - 아키텍처 다이어그램
- C4 모델 기반 시스템 아키텍처
- 컨테이너 레벨 구조
- 외부 시스템 연동

**계층 구조:**
- Web Layer (Flask)
- Analysis Layer (CompanyAnalyzer)
- Crawler Layer (NaverFinanceCrawler)
- Storage Layer (VectorStore)
- External Services (DART, Naver, Gemini)

### 4. `dataflow_diagram.puml` - 데이터 플로우 다이어그램
- VectorDB 캐싱 중심의 데이터 흐름
- 캐시 HIT/MISS 시나리오
- 성능 최적화 전략

**주요 포인트:**
- ✅ 캐시 HIT → 즉시 사용 (1~2분)
- ❌ 캐시 MISS → API/크롤링 (3~5분)
- 🔍 산업분석 리포트 → 키워드 매칭 ⭐

## 🖼️ 다이어그램 렌더링 방법

### ✅ 환경 설정 완료!

PlantUML 환경이 이미 설정되어 있습니다:
- ✅ VS Code Extension 설치됨
- ✅ 온라인 서버 설정됨
- ✅ 프로젝트 설정 완료

**자세한 사용법은 [`SETUP_GUIDE.md`](SETUP_GUIDE.md)를 참조하세요.**

### 빠른 시작

#### 1. VS Code/Cursor에서 미리보기
```
1. .puml 파일 열기 (예: class_diagram.puml)
2. Alt + D 누르기
3. 미리보기 창에서 다이어그램 확인
```

#### 2. 이미지로 내보내기
```
1. .puml 파일 우클릭
2. "PlantUML: Export Current Diagram" 선택
3. SVG 파일 생성
```

#### 3. 온라인 뷰어 (Java 불필요)
```
1. https://www.plantuml.com/plantuml/uml/ 접속
2. .puml 파일 내용 복사 & 붙여넣기
3. 자동 렌더링
```

## 📊 다이어그램 설명

### 클래스 다이어그램
```
┌─────────────────┐
│   FlaskApp      │  ← 웹 서버
└────────┬────────┘
         │ uses
         ▼
┌─────────────────┐
│ CompanyAnalyzer │  ← 핵심 엔진
└────┬────────┬───┘
     │        │
     │ lazy   │ lazy
     ▼        ▼
┌──────────┐ ┌─────────────────────┐
│VectorStore│ │NaverFinanceCrawler│
└──────────┘ └─────────────────────┘
```

### 시퀀스 다이어그램
```
User → UI → Flask → Analyzer
                    ├─→ VectorDB (캐시 확인)
                    ├─→ DART API (공시)
                    ├─→ Crawler → Naver (증권사)
                    ├─→ Gemini (AI 분석)
                    └─→ Result
```

### 데이터 플로우
```
                ┌─────────────┐
                │ VectorDB    │
                │ 캐시 확인   │
                └──────┬──────┘
                       │
           ┌───────────┴───────────┐
           │ HIT?                  │
           ├───────────┬───────────┤
           ▼           ▼           ▼
    ┌──────────┐  ┌──────────┐  ┌──────────┐
    │ DART     │  │ 종목분석 │  │ 산업분석 │
    │ (rcept_no)│  │(company) │  │(keywords)│
    └──────────┘  └──────────┘  └──────────┘
```

## 💡 주요 특징

### 산업분석 리포트 키워드 매칭 ⭐
```
질문: "삼성전자의 AI 사업 전망은?"

1. Gemini 키워드 추출
   → ["AI", "LLM", "인공지능"]

2. VectorDB에서 검색
   for each report in NAVER_INDUSTRY:
       if "AI" in report_name or "AI" in industry_keywords:
           ✅ 매칭!

3. 결과
   → [NH투자증권] AI 산업 전망 (25.10.10)
   → [미래에셋] 인공지능 기술 동향 (25.09.25)
```

## 🔍 캐싱 전략 비교

| 보고서 타입 | 캐시 키 | 매칭 방식 | 예시 |
|------------|---------|----------|------|
| DART 공시 | `rcept_no` | 정확 일치 | `20250324000901` |
| 종목분석 | `company_name` | 회사명 일치 | `"삼성전자"` |
| 산업분석 | `industry_keywords` | 키워드 포함 | `["AI", "LLM"]` ⭐ |

## 📝 노트

- 모든 다이어그램은 PlantUML 형식으로 작성됨
- 텍스트 기반이므로 Git으로 버전 관리 가능
- 코드 변경 시 다이어그램도 함께 업데이트 필요

