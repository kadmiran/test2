# 🏗️ 프로젝트 아키텍처 문서

## 📋 목차

1. [전체 아키텍처](#전체-아키텍처)
2. [레이어별 구조](#레이어별-구조)
3. [디자인 패턴 분석](#디자인-패턴-분석)
4. [파일별 상세 분석](#파일별-상세-분석)
5. [패턴 간 상호작용](#패턴-간-상호작용)
6. [아키텍처 특징](#아키텍처-특징)

---

## 🎯 전체 아키텍처

### Layered Architecture (계층형 아키텍처)

```
┌─────────────────────────────────────────────────────┐
│  Presentation Layer (app.py)                        │
│  - Flask Web Server                                 │
│  - REST API Endpoints                               │
│  - Server-Sent Events (SSE)                         │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│  Business Logic Layer (company_analyzer.py)         │
│  - 회사 분석 오케스트레이션                            │
│  - DART API 통합                                    │
│  - 분석 워크플로우 관리                               │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│  Integration Layer                                  │
│  ├─ llm_orchestrator.py (LLM 통합 관리)             │
│  ├─ naver_finance.py (외부 데이터 수집)              │
│  └─ DART API (공시 데이터)                          │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│  Data Access Layer (vector_store.py)                │
│  - FAISS Vector Database                            │
│  - HuggingFace Embeddings                           │
│  - 보고서 저장/검색                                   │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│  Configuration Layer (config.py)                    │
│  - 전역 설정 관리                                     │
│  - API 키 관리                                       │
│  - 환경 변수 처리                                     │
└─────────────────────────────────────────────────────┘
```

---

## 📂 레이어별 구조

### 1. **Presentation Layer**
- **파일**: `app.py`, `templates/index.html`
- **책임**: HTTP 요청 처리, 사용자 인터페이스, 실시간 상태 업데이트
- **의존성**: Business Logic Layer

### 2. **Business Logic Layer**
- **파일**: `company_analyzer.py`
- **책임**: 비즈니스 로직 구현, 분석 워크플로우 오케스트레이션
- **의존성**: Integration Layer, Data Access Layer

### 3. **Integration Layer**
- **파일**: `llm_orchestrator.py`, `naver_finance.py`
- **책임**: 외부 서비스 통합, API 래핑
- **의존성**: Configuration Layer

### 4. **Data Access Layer**
- **파일**: `vector_store.py`
- **책임**: 데이터 영속성, 벡터 검색
- **의존성**: Configuration Layer

### 5. **Configuration Layer**
- **파일**: `config.py`
- **책임**: 전역 설정 관리
- **의존성**: None (최하위 레이어)

---

## 🎨 디자인 패턴 분석

### 📊 패턴 사용 통계

| 패턴 | 위치 | 목적 | 중요도 |
|-----|------|-----|-------|
| **Strategy** | llm_orchestrator.py | LLM Provider 교체 가능 | ⭐⭐⭐⭐⭐ |
| **Registry** | llm_orchestrator.py | Provider 중앙 관리 | ⭐⭐⭐⭐ |
| **Factory Method** | llm_orchestrator.py | Provider 자동 선택 | ⭐⭐⭐⭐ |
| **Dependency Injection** | app.py, company_analyzer.py | 느슨한 결합 | ⭐⭐⭐⭐⭐ |
| **Facade** | company_analyzer.py, vector_store.py | 복잡도 숨김 | ⭐⭐⭐⭐⭐ |
| **Repository** | vector_store.py | 데이터 접근 추상화 | ⭐⭐⭐⭐ |
| **Adapter** | naver_finance.py | 외부 API 통합 | ⭐⭐⭐ |
| **Template Method** | company_analyzer.py, naver_finance.py | 알고리즘 스켈레톤 | ⭐⭐⭐ |
| **Lazy Initialization** | company_analyzer.py | 필요시 생성 | ⭐⭐⭐ |
| **Singleton** | config.py | 전역 설정 관리 | ⭐⭐⭐ |
| **Observer** | app.py (SSE) | 실시간 상태 업데이트 | ⭐⭐⭐ |
| **Front Controller** | app.py | 중앙 요청 처리 | ⭐⭐⭐⭐ |

---

## 📁 파일별 상세 분석

### 1. `app.py` - Presentation Layer

#### 🎨 적용된 패턴

##### **Front Controller Pattern**
```python
@app.route('/')
def index():
    """모든 요청의 진입점"""
    return render_template('index.html')

@app.route('/analyze_stream', methods=['POST'])
def analyze_stream():
    """분석 요청 중앙 처리"""
    # 모든 분석 요청을 이 엔드포인트로 집중
```

**목적**: 
- 모든 요청을 중앙에서 처리
- 공통 로직(로깅, 인증 등) 일괄 적용 가능

##### **Dependency Injection**
```python
# LLM Orchestrator 생성
llm_orchestrator = LLMOrchestrator()
gemini_provider = GeminiProvider(
    api_key=config.get_gemini_api_key(),
    model_candidates=config.GEMINI_MODEL_CANDIDATES
)
llm_orchestrator.register_provider(gemini_provider, is_default=True)

# CompanyAnalyzer에 주입
analyzer = CompanyAnalyzer(
    config.get_dart_api_key(), 
    llm_orchestrator  # DI
)
```

**장점**:
- 느슨한 결합
- 테스트 용이성 (Mock 객체 주입 가능)
- 런타임 설정 변경 가능

##### **Observer Pattern (변형) - SSE**
```python
def generate():
    """실시간 상태 업데이트 스트림"""
    while True:
        if not status_queue.empty():
            message = status_queue.get()
            yield f"data: {json.dumps(message)}\n\n"
        
        if message.get('type') == 'complete':
            break

return Response(
    stream_with_context(generate()),
    mimetype='text/event-stream'
)
```

**특징**:
- 서버 → 클라이언트 단방향 푸시
- 실시간 진행 상황 업데이트
- 긴 작업에 대한 사용자 경험 개선

---

### 2. `llm_orchestrator.py` - Integration Layer

#### 🎨 적용된 패턴

##### **Strategy Pattern** (핵심)
```python
# 추상 전략
class LLMProvider(ABC):
    """모든 LLM Provider가 따라야 할 인터페이스"""
    
    @abstractmethod
    def generate_content(self, prompt: str, **kwargs) -> str:
        """텍스트 생성 (각 Provider가 구현)"""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Provider 이름 반환"""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> dict:
        """Provider 능력 반환"""
        pass

# 구체적 전략 1: Gemini
class GeminiProvider(LLMProvider):
    def generate_content(self, prompt: str, **kwargs) -> str:
        response = self.model.generate_content(prompt)
        return response.text
    
    def get_name(self) -> str:
        return "gemini"
    
    def get_capabilities(self) -> dict:
        return {
            'context_window': 1_000_000,
            'supports_long_context': True,
            'supports_korean': True,
            'cost': 'medium',
            'speed': 'fast'
        }

# 구체적 전략 2: OpenAI (향후 추가 가능)
class OpenAIProvider(LLMProvider):
    def generate_content(self, prompt: str, **kwargs) -> str:
        # OpenAI API 호출
        pass
```

**목적**:
- 런타임에 LLM Provider 교체 가능
- 새로운 LLM 추가 시 기존 코드 수정 불필요 (Open-Closed Principle)
- 각 Provider의 구현 세부사항 캡슐화

##### **Registry Pattern**
```python
class LLMOrchestrator:
    def __init__(self):
        self.providers = {}  # name → LLMProvider 매핑
        self.default_provider = None
        self.task_routing = {}  # task_type → provider_name
    
    def register_provider(self, provider: LLMProvider, is_default: bool = False):
        """Provider 등록"""
        name = provider.get_name()
        self.providers[name] = provider
        print(f"✅ LLM Provider 등록: {name}")
        
        if is_default or self.default_provider is None:
            self.default_provider = name
    
    def select_provider(self, task_type: str) -> LLMProvider:
        """등록된 Provider 중에서 선택"""
        if task_type in self.task_routing:
            provider_name = self.task_routing[task_type]
            return self.providers[provider_name]
        
        return self.providers[self.default_provider]
```

**특징**:
- Provider들을 중앙에서 관리
- 이름으로 Provider 조회
- 런타임에 Provider 추가/제거 가능

##### **Factory Method Pattern**
```python
def select_provider(self, task_type: Optional[str] = None) -> LLMProvider:
    """작업 유형에 따라 적절한 Provider 선택"""
    
    # 1. 명시적 라우팅 (설정 기반)
    if task_type and task_type in self.task_routing:
        provider_name = self.task_routing[task_type]
        return self.providers[provider_name]
    
    # 2. 자동 선택 (Capabilities 기반)
    if task_type == 'long_context_analysis':
        for name, provider in self.providers.items():
            if provider.get_capabilities().get('supports_long_context'):
                return provider
    
    elif task_type == 'quick_analysis':
        # 속도 우선 Provider 선택
        pass
    
    # 3. 기본 Provider
    return self.providers[self.default_provider]
```

**장점**:
- 복잡한 선택 로직을 한 곳에서 관리
- 클라이언트는 구체적인 Provider를 몰라도 됨
- 선택 전략 변경 시 한 곳만 수정

---

### 3. `company_analyzer.py` - Business Logic Layer

#### 🎨 적용된 패턴

##### **Facade Pattern** (핵심)
```python
class CompanyAnalyzer:
    """복잡한 분석 프로세스를 단순한 인터페이스로 제공"""
    
    def analyze_company(self, company_name, user_query, status_callback=None):
        """
        하나의 메서드로 전체 분석 프로세스 실행
        
        내부적으로:
        1. DART API 호출
        2. 네이버 금융 크롤링
        3. VectorDB 저장
        4. LLM 분석
        5. 파일 정리
        등 복잡한 작업을 모두 처리
        """
        # 1. 회사 고유번호 조회
        corp_info = self.get_corp_code(company_name)
        
        # 2. 질문 분석
        years = self._extract_time_range(user_query)
        
        # 3. 보고서 검색
        reports = self.get_reports(corp_code, ...)
        
        # 4. 추가 보고서 수집
        additional_reports = self.get_analyst_reports(...)
        
        # 5. 네이버 리포트 수집
        naver_reports = self.naver_crawler.search_company_reports(...)
        
        # 6. VectorDB 저장
        self.vector_store.add_report(...)
        
        # 7. AI 분석
        analysis = self.analyze_with_llm_rag(...)
        
        # 8. 정리
        self.cleanup_downloads()
        
        return result
```

**목적**:
- 복잡한 하위 시스템들을 간단한 인터페이스로 래핑
- 클라이언트는 `analyze_company()` 하나만 호출하면 됨
- 하위 시스템 변경이 클라이언트에 영향 없음

##### **Template Method Pattern**
```python
def analyze_company(self, company_name, user_query, status_callback=None):
    """
    고정된 알고리즘 스켈레톤
    
    각 단계는 변경 가능하지만, 순서는 고정
    """
    try:
        # Step 1: 회사 정보 조회 (필수)
        corp_info = self.get_corp_code(company_name)
        if not corp_info:
            return error_result
        
        # Step 2: 질문 분석 (필수)
        years = self._extract_time_range(user_query)
        
        # Step 3: 보고서 검색 (필수)
        reports = self.get_reports(...)
        
        # Step 4: 추가 데이터 수집 (선택적)
        additional_reports = self.get_analyst_reports(...)
        naver_reports = self.naver_crawler.search_company_reports(...)
        
        # Step 5: 데이터 저장 (필수)
        self.vector_store.add_report(...)
        
        # Step 6: AI 분석 (필수)
        analysis = self.analyze_with_llm_rag(...)
        
        # Step 7: 정리 (필수)
        self.cleanup_downloads()
        
        return success_result
        
    except Exception as e:
        return error_result
```

**특징**:
- 알고리즘의 구조(스켈레톤)는 고정
- 각 단계의 구현은 변경 가능
- 일관된 처리 흐름 보장

##### **Lazy Initialization**
```python
class CompanyAnalyzer:
    def __init__(self, dart_api_key, llm_orchestrator):
        self.dart_api_key = dart_api_key
        self.llm_orchestrator = llm_orchestrator
        
        # 초기화 시점에는 생성하지 않음
        self._vector_store = None
        self._naver_crawler = None
    
    @property
    def vector_store(self):
        """VectorStore는 처음 사용할 때만 생성"""
        if self._vector_store is None:
            print("📦 벡터 데이터베이스 초기화 중...")
            self._vector_store = VectorStore()
            print("✅ 벡터 데이터베이스 초기화 완료")
        return self._vector_store
    
    @property
    def naver_crawler(self):
        """NaverFinanceCrawler는 처음 사용할 때만 생성"""
        if self._naver_crawler is None:
            print("📊 네이버 금융 크롤러 초기화 중...")
            self._naver_crawler = NaverFinanceCrawler(
                llm_orchestrator=self.llm_orchestrator
            )
            print("✅ 네이버 금융 크롤러 초기화 완료")
        return self._naver_crawler
```

**장점**:
- 초기 로딩 시간 단축
- 사용하지 않는 리소스 생성 방지
- 메모리 효율적

---

### 4. `vector_store.py` - Data Access Layer

#### 🎨 적용된 패턴

##### **Repository Pattern**
```python
class VectorStore:
    """벡터 데이터베이스에 대한 추상화된 인터페이스"""
    
    def add_report(self, rcept_no, report_name, company_name, 
                   report_date, content, **kwargs):
        """보고서 추가"""
        # 내부적으로 FAISS, 임베딩 등 복잡한 작업 수행
        pass
    
    def search_similar_reports(self, query, company_name=None, 
                              k=20, score_threshold=0.7):
        """유사 보고서 검색"""
        # 벡터 유사도 검색 수행
        pass
    
    def check_report_exists(self, rcept_no):
        """보고서 존재 확인"""
        return rcept_no in self.metadata.get('reports', {})
    
    def get_report_from_cache(self, rcept_no):
        """캐시된 보고서 가져오기"""
        pass
    
    def reset_database(self):
        """데이터베이스 초기화"""
        pass
```

**특징**:
- 데이터 접근 로직을 비즈니스 로직에서 분리
- 데이터 저장소 변경 시 Repository만 수정
- 일관된 데이터 접근 인터페이스 제공

##### **Facade Pattern**
```python
class VectorStore:
    def __init__(self, persist_directory: Optional[str] = None):
        """
        여러 복잡한 라이브러리를 통합
        - HuggingFace Embeddings
        - FAISS Vector Store
        - LangChain Text Splitter
        """
        # 임베딩 모델
        self.embeddings = HuggingFaceEmbeddings(
            model_name=config.EMBEDDING_MODEL,
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        
        # 텍스트 분할기
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.CHUNK_SIZE,
            chunk_overlap=config.CHUNK_OVERLAP,
            separators=["\n\n", "\n", "。", ".", " ", ""]
        )
        
        # FAISS 벡터스토어
        self.vectorstore = self._load_or_create_vectorstore()
        
        # 메타데이터
        self.metadata = self._load_metadata()
```

**목적**:
- 복잡한 벡터 DB 라이브러리들을 간단한 인터페이스로 제공
- 클라이언트는 FAISS, HuggingFace 등을 몰라도 됨

---

### 5. `naver_finance.py` - Integration Layer

#### 🎨 적용된 패턴

##### **Adapter Pattern**
```python
class NaverFinanceCrawler:
    """네이버 금융 웹사이트 → 표준화된 데이터 형식"""
    
    def search_company_reports(self, company_name, max_reports=5):
        """
        네이버 금융 HTML → 표준 딕셔너리 형식
        
        반환 형식:
        [
            {
                'name': str,      # 리포트명
                'date': str,      # 발행일
                'content': str,   # 텍스트 내용
                'url': str        # PDF URL
            },
            ...
        ]
        """
        # 1. HTML 페이지 크롤링
        html = self._fetch_html(search_url)
        
        # 2. BeautifulSoup으로 파싱
        soup = BeautifulSoup(html, 'html.parser')
        
        # 3. 리포트 정보 추출
        reports = self._parse_report_table(soup)
        
        # 4. PDF 다운로드 및 텍스트 추출
        for report in reports:
            pdf_content = self._download_and_extract_pdf(report['url'])
            report['content'] = pdf_content
        
        # 5. 표준 형식으로 반환
        return reports
    
    def search_industry_reports(self, keywords, max_reports=2):
        """
        다른 형식의 데이터도 동일한 형식으로 변환
        """
        # 동일한 형식으로 반환
        return [{
            'name': ...,
            'date': ...,
            'content': ...,
            'url': ...
        }]
```

**목적**:
- 외부 시스템(네이버 금융)의 인터페이스를 내부 표준에 맞게 변환
- 클라이언트는 데이터 출처를 신경 쓰지 않아도 됨
- 외부 API 변경 시 Adapter만 수정

##### **Template Method Pattern**
```python
def _download_and_extract_pdf(self, pdf_url, pdf_filename):
    """PDF 처리의 고정된 흐름"""
    
    # Step 1: PDF 다운로드
    pdf_content = self._download_pdf(pdf_url)
    
    # Step 2: 파일 저장
    pdf_path = self._save_pdf(pdf_content, pdf_filename)
    
    # Step 3: 텍스트 추출
    text_content = self._extract_text_from_pdf(pdf_path)
    
    # Step 4: 정리
    self._cleanup_temp_file(pdf_path)
    
    return text_content
```

---

### 6. `config.py` - Configuration Layer

#### 🎨 적용된 패턴

##### **Singleton Pattern (변형)**
```python
class Config:
    """전역 설정 클래스"""
    
    # 클래스 레벨 속성 (모든 인스턴스가 공유)
    DART_API_KEY: str = os.getenv('DART_API_KEY', 'default_key')
    GEMINI_API_KEY: str = os.getenv('GEMINI_API_KEY', 'default_key')
    
    # 설정 메서드
    def validate_api_keys(self) -> bool:
        """API 키 검증"""
        return bool(self.DART_API_KEY and self.GEMINI_API_KEY)
    
    def get_dart_api_key(self) -> str:
        """DART API 키 반환"""
        return self.DART_API_KEY

# 모듈 레벨에서 싱글톤 인스턴스 생성
config = Config()

# 다른 모듈에서 import
from config import config  # 모두 같은 인스턴스 사용
```

**특징**:
- 전역적으로 하나의 설정 객체만 존재
- 어디서든 동일한 설정에 접근
- 환경 변수 우선순위 관리

---

## 🔗 패턴 간 상호작용

### 호출 흐름 다이어그램

```
HTTP Request
    ↓
┌─────────────────────────────────────┐
│ app.py (Front Controller)           │
│ - @app.route() 엔드포인트            │
└─────────────────────────────────────┘
    ↓ DI (Dependency Injection)
┌─────────────────────────────────────┐
│ company_analyzer.py (Facade)        │
│ - analyze_company()                 │
│   → 복잡한 프로세스를 단순 인터페이스로│
└─────────────────────────────────────┘
    ↓ 사용
┌────────┬─────────────┬──────────────┐
↓        ↓             ↓              ↓
LLM      VectorStore   NaverFinance   Config
Orch.    (Repo)        (Adapter)      (Singleton)
│        │             │              │
Strategy Repository    Template       전역설정
Registry Facade        Method
Factory
```

### 데이터 흐름

```
1. 사용자 요청
   ↓
2. Front Controller (app.py)
   ↓
3. Facade (company_analyzer.py)
   ├→ DART API 호출
   ├→ Adapter (naver_finance.py) → 네이버 금융 크롤링
   ├→ Repository (vector_store.py) → 데이터 저장
   └→ Strategy (llm_orchestrator.py) → LLM 분석
   ↓
4. 결과 반환 (SSE 스트리밍)
   ↓
5. 사용자에게 표시
```

---

## 🎯 아키텍처 특징

### 1. **관심사의 분리** (Separation of Concerns)
- 각 레이어가 명확한 책임
- Presentation ↔ Business ↔ Data Access 분리
- 수정 시 영향 범위 최소화

### 2. **확장성** (Extensibility)
- 새로운 LLM Provider 추가 용이 (Strategy Pattern)
- 새로운 데이터 소스 추가 용이 (Adapter Pattern)
- 새로운 비즈니스 로직 추가 용이 (Facade Pattern)

### 3. **테스트 용이성** (Testability)
```python
# Mock 객체로 테스트 가능
mock_orchestrator = MockLLMOrchestrator()
analyzer = CompanyAnalyzer(dart_api_key, mock_orchestrator)
analyzer.analyze_company("테스트회사", "테스트질문")
```

### 4. **유지보수성** (Maintainability)
- 디자인 패턴을 통한 명확한 코드 구조
- 각 모듈의 책임이 명확
- 변경 시 영향 범위 예측 가능

### 5. **성능 최적화**
- Lazy Initialization (필요시에만 리소스 생성)
- Repository 패턴으로 캐싱 구현
- VectorDB로 빠른 검색

---

## 📈 확장 시나리오

### 새로운 LLM Provider 추가

```python
# 1. llm_orchestrator.py에 새로운 Provider 추가
class ClaudeProvider(LLMProvider):
    def generate_content(self, prompt: str, **kwargs) -> str:
        # Claude API 구현
        pass
    
    def get_name(self) -> str:
        return "claude"
    
    def get_capabilities(self) -> dict:
        return {
            'context_window': 200_000,
            'supports_long_context': True,
            'supports_korean': True,
            'cost': 'high',
            'speed': 'medium'
        }

# 2. app.py에서 등록
claude_provider = ClaudeProvider(config.CLAUDE_API_KEY)
llm_orchestrator.register_provider(claude_provider)

# 3. config.py에서 라우팅 설정
LLM_TASK_ROUTING = {
    'query_analysis': 'claude',  # 빠른 분석은 Claude
    'long_context_analysis': 'gemini',  # 긴 컨텍스트는 Gemini
}

# 기존 코드 수정 불필요! ✅
```

### 새로운 데이터 소스 추가

```python
# 1. naver_finance.py를 참고하여 새로운 Adapter 생성
class DartAnalysisAdapter:
    def search_reports(self, company_name):
        # DART 분석 리포트 크롤링
        return [{'name': ..., 'date': ..., 'content': ...}]

# 2. company_analyzer.py에서 사용
dart_adapter = DartAnalysisAdapter()
dart_reports = dart_adapter.search_reports(company_name)

# 동일한 형식으로 반환되므로 기존 코드와 통합 가능! ✅
```

---

## 🔍 코드 품질 지표

### SOLID 원칙 준수

| 원칙 | 적용 예시 | 파일 |
|-----|----------|------|
| **S** (단일 책임) | 각 클래스가 하나의 책임만 | 모든 파일 |
| **O** (개방-폐쇄) | 새 LLM 추가 시 기존 코드 수정 불필요 | llm_orchestrator.py |
| **L** (리스코프 치환) | LLMProvider 인터페이스 준수 | llm_orchestrator.py |
| **I** (인터페이스 분리) | Provider별 독립적 인터페이스 | llm_orchestrator.py |
| **D** (의존성 역전) | 추상화에 의존 (DI) | app.py, company_analyzer.py |

### 디자인 원칙

- ✅ **DRY** (Don't Repeat Yourself): 공통 로직을 Facade, Repository로 추상화
- ✅ **KISS** (Keep It Simple, Stupid): 각 레이어가 명확한 역할
- ✅ **YAGNI** (You Aren't Gonna Need It): 필요한 기능만 구현 (Lazy Initialization)

---

## 📚 참고 자료

### 디자인 패턴
- **Gang of Four Design Patterns**: Strategy, Factory Method, Template Method, Facade, Adapter, Singleton, Observer
- **Enterprise Application Patterns**: Repository, Dependency Injection, Layered Architecture

### 아키텍처 스타일
- **Layered Architecture**: 계층형 구조로 관심사 분리
- **Plugin Architecture**: LLM Provider를 플러그인처럼 추가/제거

---

## 🎓 학습 포인트

이 프로젝트에서 배울 수 있는 것:

1. **다양한 디자인 패턴의 실전 적용**
   - 12개의 패턴이 유기적으로 결합

2. **확장 가능한 아키텍처 설계**
   - 새로운 기능 추가가 쉬움
   - 기존 코드 수정 최소화

3. **관심사의 분리**
   - Presentation, Business, Data, Integration 레이어
   - 각 레이어의 독립적 발전 가능

4. **실전 Python 아키텍처**
   - ABC (Abstract Base Class) 활용
   - Property decorator로 Lazy Initialization
   - Dependency Injection 구현

---

**작성일**: 2025-10-21  
**버전**: 1.0  
**작성자**: AI Architecture Documentation

