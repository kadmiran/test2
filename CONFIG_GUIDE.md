# ⚙️ Configuration Guide (설정 가이드)

## 📋 개요

`config.py` 파일은 모든 API 키와 설정을 한 곳에서 관리하는 중앙 설정 파일입니다.

## 🔑 API 키 설정 방법

### 방법 1: config.py 직접 수정 (간단)

`config.py` 파일을 열어서 API 키를 직접 입력:

```python
# config.py

DART_API_KEY: str = os.getenv(
    'DART_API_KEY',
    'YOUR_DART_API_KEY_HERE'  # 여기에 실제 키 입력
)

GEMINI_API_KEY: str = os.getenv(
    'GEMINI_API_KEY',
    'YOUR_GEMINI_API_KEY_HERE'  # 여기에 실제 키 입력
)
```

### 방법 2: 환경 변수 사용 (권장 - 보안)

1. **`.env` 파일 생성**

```bash
# 예시 파일을 복사
cp env.example .env
```

2. **`.env` 파일 편집**

```bash
# .env
DART_API_KEY=your_actual_dart_api_key_here
GEMINI_API_KEY=your_actual_gemini_api_key_here
```

3. **환경 변수 로드**

Python에서 자동으로 `.env` 파일을 로드하도록 `config.py` 상단에 추가:

```python
from dotenv import load_dotenv
load_dotenv()  # .env 파일의 환경 변수 로드
```

> ⚠️ **보안 주의**: `.env` 파일은 `.gitignore`에 추가하여 Git에 커밋되지 않도록 하세요!

## 📊 주요 설정 항목

### API Keys

```python
DART_API_KEY         # 금융감독원 전자공시 API 키
GEMINI_API_KEY       # Google Gemini AI API 키
```

### DART API Settings

```python
DART_BASE_URL        # DART API Base URL
DART_CORP_CODE_URL   # 기업 고유번호 조회 URL
DART_LIST_URL        # 보고서 목록 조회 URL
DART_DOCUMENT_URL    # 보고서 다운로드 URL
DART_COMPANY_URL     # 기업개황 조회 URL
```

### Vector Store Settings

```python
VECTOR_DB_DIR           # 벡터DB 저장 디렉토리 (기본: 'vector_db')
EMBEDDING_MODEL         # 임베딩 모델 (기본: 'jhgan/ko-sroberta-multitask')
CHUNK_SIZE              # 텍스트 청크 크기 (기본: 1000)
CHUNK_OVERLAP           # 청크 오버랩 (기본: 200)
```

### Report Settings

```python
MAX_MAIN_REPORT_CHARS      # 메인 보고서 최대 문자 수 (기본: 500,000)
MAX_ADDITIONAL_REPORTS     # 추가 DART 보고서 개수 (기본: 5)
MAX_COMPANY_REPORTS        # 증권사 종목분석 리포트 개수 (기본: 3)
MAX_INDUSTRY_REPORTS       # 증권사 산업분석 리포트 개수 (기본: 2)
DEFAULT_SEARCH_YEARS       # 기본 검색 기간(년) (기본: 3)
MAX_SEARCH_YEARS           # 최대 검색 기간(년) (기본: 10)
```

### Flask Server Settings

```python
FLASK_DEBUG         # 디버그 모드 (기본: True)
FLASK_HOST          # 서버 호스트 (기본: '0.0.0.0')
FLASK_PORT          # 서버 포트 (기본: 5000)
```

## 🛠️ 사용 방법

### 1. Config 불러오기

```python
from config import config

# API 키 사용
dart_key = config.DART_API_KEY
gemini_key = config.GEMINI_API_KEY

# 또는 헬퍼 메서드 사용
dart_key = config.get_dart_api_key()
gemini_key = config.get_gemini_api_key()
```

### 2. 설정 확인

```bash
# 현재 설정 확인 (API 키는 마스킹되어 출력)
python config.py
```

출력 예시:
```
==================================================
📋 Current Configuration
==================================================
DART API Key: 65684cef96...
Gemini API Key: AIzaSyB_0W...

Vector DB Dir: vector_db
Download Dir: downloads

Flask Host: 0.0.0.0
Flask Port: 5000
Flask Debug: True

Max Reports:
  - Main Report: 500,000 chars
  - Additional DART: 5 reports
  - Company Reports: 3 reports
  - Industry Reports: 2 reports
==================================================
```

### 3. API 키 유효성 검증

```python
from config import config

if config.validate_api_keys():
    print("✅ 모든 API 키가 설정되었습니다.")
else:
    print("❌ API 키를 확인해주세요.")
```

## 🔍 API 키 발급 방법

### DART API 키

1. [OpenDART](https://opendart.fss.or.kr) 접속
2. 회원가입 및 로그인
3. 인증키 신청
4. 승인 후 API 키 복사

### Gemini API 키

1. [Google AI Studio](https://aistudio.google.com/app/apikey) 접속
2. Google 계정으로 로그인
3. "Create API Key" 클릭
4. API 키 복사

## 📝 설정 커스터마이징

### 포트 변경

```python
# config.py
FLASK_PORT: int = 8080  # 5000 → 8080으로 변경
```

### 보고서 개수 조정

```python
# config.py
MAX_COMPANY_REPORTS: int = 5  # 3 → 5개로 증가
MAX_INDUSTRY_REPORTS: int = 3  # 2 → 3개로 증가
```

### 검색 기간 조정

```python
# config.py
DEFAULT_SEARCH_YEARS: int = 5  # 3년 → 5년
MAX_SEARCH_YEARS: int = 15     # 10년 → 15년
```

## ⚠️ 주의사항

### 1. API 키 보안

- **절대 Git에 커밋하지 마세요!**
- `.gitignore`에 `.env` 파일 추가
- 공개 저장소에 업로드 금지

### 2. 환경별 설정

개발/운영 환경을 분리하려면:

```bash
# .env.development
FLASK_DEBUG=True
FLASK_PORT=5000

# .env.production
FLASK_DEBUG=False
FLASK_PORT=80
```

### 3. 기본값 유지

특별한 이유가 없다면 기본 설정값을 유지하는 것을 권장합니다.

## 🔗 관련 파일

- `config.py` - 설정 클래스
- `env.example` - 환경 변수 예시
- `.gitignore` - Git 무시 파일 목록

## 📚 추가 자료

- [DART API 문서](https://opendart.fss.or.kr/guide/main.do)
- [Gemini API 문서](https://ai.google.dev/docs)
- [Flask 설정 가이드](https://flask.palletsprojects.com/en/2.3.x/config/)

