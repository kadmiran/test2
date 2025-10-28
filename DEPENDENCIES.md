# 📦 의존성 패키지 설명

프로젝트에서 사용하는 모든 Python 패키지에 대한 상세 설명입니다.

---

## 🌐 Web Framework

### Flask 3.0.0+
- **용도**: 웹 서버 및 REST API
- **사용 위치**: `app.py`
- **주요 기능**:
  - REST API 엔드포인트
  - Server-Sent Events (SSE) 스트리밍
  - 템플릿 렌더링
  - 파일 다운로드

---

## 🔗 HTTP & Web Scraping

### requests 2.31.0+
- **용도**: HTTP 요청 처리
- **사용 위치**: 
  - `company_analyzer.py` - DART API 호출
  - `naver_finance.py` - 네이버 금융 크롤링
  - `llm_orchestrator.py` - Friendli API 호출
- **주요 기능**:
  - DART Open API 통신
  - PDF 파일 다운로드
  - 증권사 리포트 수집

### beautifulsoup4 4.12.0+
- **용도**: HTML 파싱 및 스크래핑
- **사용 위치**: 
  - `company_analyzer.py` - DART XML 파싱
  - `naver_finance.py` - 네이버 금융 HTML 파싱
- **주요 기능**:
  - 증권사 리포트 목록 추출
  - HTML 테이블 데이터 파싱

### lxml 5.1.0+
- **용도**: XML/HTML 파서 (BeautifulSoup 백엔드)
- **설명**: BeautifulSoup의 고성능 파서로 사용

---

## 🤖 AI & LLM

### google-generativeai 0.4.0+
- **용도**: Google Gemini AI 연동
- **사용 위치**: 
  - `llm_orchestrator.py` - GeminiProvider
  - `company_analyzer.py` - 질문 분석 및 보고서 분석
- **주요 기능**:
  - Gemini 2.5 Pro 모델 사용
  - 1M 토큰 컨텍스트 처리
  - 스트리밍 응답

### langchain 0.1.10+
- **용도**: LLM 애플리케이션 프레임워크
- **사용 위치**: `vector_store.py`
- **주요 기능**:
  - 텍스트 청크 분할
  - Document 객체 관리
  - VectorStore 추상화

### langchain-community 0.0.20+
- **용도**: LangChain 커뮤니티 패키지
- **사용 위치**: `vector_store.py`
- **주요 기능**:
  - HuggingFace Embeddings
  - FAISS VectorStore 래퍼

---

## 💾 Vector Database & Embeddings

### faiss-cpu 1.8.0+
- **용도**: 벡터 유사도 검색
- **사용 위치**: `vector_store.py`
- **주요 기능**:
  - 고속 벡터 검색
  - 보고서 캐싱
  - RAG (Retrieval Augmented Generation)

### sentence-transformers 2.3.0+
- **용도**: 텍스트 임베딩 생성
- **사용 위치**: `vector_store.py`
- **사용 모델**: `jhgan/ko-sroberta-multitask` (한국어 특화)
- **주요 기능**:
  - 텍스트 → 벡터 변환
  - 의미론적 유사도 계산

---

## 📄 Document Processing

### PyMuPDF 1.23.0+
- **용도**: PDF 파일 읽기 및 텍스트 추출
- **사용 위치**: 
  - `company_analyzer.py`
  - `naver_finance.py`
- **import 이름**: `fitz`
- **주요 기능**:
  - 증권사 리포트 PDF → 텍스트 변환
  - 페이지별 텍스트 추출

### reportlab 4.0.0+
- **용도**: PDF 파일 생성
- **사용 위치**: `app.py`
- **주요 기능**:
  - 분석 결과 PDF 다운로드
  - 한글 폰트 지원 (맑은 고딕)
  - Markdown → PDF 변환

### markdown 3.5.0+
- **용도**: Markdown 텍스트 → HTML 변환
- **사용 위치**: `app.py`
- **주요 기능**:
  - AI 분석 결과 렌더링
  - 테이블, 코드 블록 지원

---

## ⚙️ Configuration

### python-dotenv 1.0.0+
- **용도**: `.env` 파일 지원 (선택사항)
- **설명**: 환경 변수를 `.env` 파일에서 로드
- **사용법**:
  ```python
  from dotenv import load_dotenv
  load_dotenv()  # .env 파일 로드
  ```

---

## 📊 패키지 의존성 그래프

```
Flask App (app.py)
    ├── Flask
    ├── markdown
    ├── reportlab
    └── CompanyAnalyzer
            ├── requests (DART API)
            ├── beautifulsoup4 (XML 파싱)
            ├── PyMuPDF (PDF 처리)
            ├── google-generativeai (Gemini)
            ├── VectorStore
            │       ├── faiss-cpu
            │       ├── sentence-transformers
            │       ├── langchain
            │       └── langchain-community
            └── NaverFinanceCrawler
                    ├── requests
                    ├── beautifulsoup4
                    └── PyMuPDF
```

---

## 🚀 설치 방법

### 1. 가상환경 생성 (권장)
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### 2. 패키지 설치
```bash
pip install -r requirements.txt
```

### 3. 설치 확인
```bash
pip list
```

---

## 🔧 개발 환경 추가 패키지

프로덕션에는 필요 없지만 개발 시 유용한 패키지:

```bash
# 코드 포맷팅
pip install black

# Linting
pip install flake8 pylint

# 타입 체킹
pip install mypy

# 테스팅
pip install pytest pytest-cov
```

---

## 📝 버전 업데이트 가이드

### 패키지 버전 확인
```bash
pip list --outdated
```

### 특정 패키지 업그레이드
```bash
pip install --upgrade google-generativeai
```

### 전체 패키지 업그레이드
```bash
pip install --upgrade -r requirements.txt
```

### 현재 설치된 버전 고정
```bash
pip freeze > requirements-lock.txt
```

---

## ⚠️ 주의사항

### FAISS 설치 이슈
- **Windows**: `faiss-cpu` 사용 (CUDA 불필요)
- **Mac (Apple Silicon)**: 일부 버전 호환성 이슈 가능
  ```bash
  # Apple Silicon
  conda install -c pytorch faiss-cpu
  ```

### PyMuPDF 이름 차이
- **패키지명**: `PyMuPDF`
- **import명**: `fitz`
- 혼동 주의!

### LangChain 버전
- `langchain`과 `langchain-community`는 별도 패키지
- 둘 다 필요함

---

## 🔍 패키지 크기

대략적인 설치 용량:
- **Flask**: ~5 MB
- **requests**: ~0.5 MB
- **beautifulsoup4**: ~0.5 MB
- **google-generativeai**: ~2 MB
- **langchain**: ~50 MB
- **faiss-cpu**: ~20 MB
- **sentence-transformers**: ~500 MB (모델 다운로드 포함)
- **PyMuPDF**: ~15 MB
- **reportlab**: ~5 MB

**총 예상 용량**: ~600 MB

---

## 📚 참고 문서

- [Flask 공식 문서](https://flask.palletsprojects.com/)
- [Gemini API 문서](https://ai.google.dev/docs)
- [LangChain 문서](https://python.langchain.com/)
- [FAISS 문서](https://github.com/facebookresearch/faiss)
- [Sentence Transformers](https://www.sbert.net/)

---

**업데이트**: 2025-10-28  
**버전**: 2.0

