# 🚀 PlantUML 환경 설정 가이드

PlantUML 다이어그램을 보고 편집할 수 있는 환경이 설정되었습니다!

## ✅ 설치 완료 항목

1. **VS Code Extension**: `jebbs.plantuml` ✅
2. **온라인 렌더링 서버**: PlantUML 공식 서버 사용 ✅
3. **프로젝트 설정**: `.vscode/settings.json` 생성 ✅

## 📖 사용 방법

### 1️⃣ 다이어그램 미리보기 (가장 쉬운 방법)

#### VS Code에서:
1. `.puml` 파일을 엽니다 (예: `class_diagram.puml`)
2. 아래 단축키 중 하나를 누릅니다:
   - **`Alt + D`** - 미리보기 창 열기 (추천)
   - **`Ctrl + Shift + P`** → `PlantUML: Preview Current Diagram` 입력

#### Cursor에서:
1. `.puml` 파일을 엽니다
2. **`Alt + D`** 또는 우클릭 → `Preview Current Diagram`

### 2️⃣ 다이어그램 이미지로 내보내기

#### 방법 1: 우클릭 메뉴
1. `.puml` 파일 우클릭
2. **`PlantUML: Export Current Diagram`** 선택
3. `diagrams/` 폴더에 SVG 파일 생성

#### 방법 2: 명령 팔레트
1. **`Ctrl + Shift + P`**
2. `PlantUML: Export Current File Diagrams` 입력
3. SVG/PNG/PDF 선택

### 3️⃣ 온라인 뷰어 (브라우저)

Java 설치 없이 바로 확인:

1. https://www.plantuml.com/plantuml/uml/ 접속
2. `.puml` 파일 내용 복사
3. 텍스트 박스에 붙여넣기
4. 자동으로 다이어그램 렌더링

## 🎨 다이어그램 편집 팁

### 실시간 미리보기
```
1. Alt + D로 미리보기 창 열기
2. 코드 수정하면 자동으로 업데이트됨
3. 저장 시 즉시 반영
```

### 내보내기 형식
- **SVG** (추천): 벡터, 확대해도 깨지지 않음
- **PNG**: 일반 이미지
- **PDF**: 문서용

### 단축키 모음
| 기능 | 단축키 |
|------|--------|
| 미리보기 열기 | `Alt + D` |
| 내보내기 | `Alt + E` |
| 명령 팔레트 | `Ctrl + Shift + P` |

## 📁 현재 프로젝트 다이어그램

### 사용 가능한 다이어그램:
1. **`class_diagram.puml`** 
   - 클래스 구조 및 관계
   - 📊 Alt + D로 미리보기

2. **`sequence_diagram.puml`**
   - 전체 프로세스 흐름
   - 🔄 Alt + D로 미리보기

3. **`architecture_diagram.puml`**
   - C4 모델 시스템 아키텍처
   - 🏗️ Alt + D로 미리보기

4. **`dataflow_diagram.puml`**
   - VectorDB 캐싱 데이터 플로우
   - 📈 Alt + D로 미리보기

## 🔧 트러블슈팅

### ❌ 미리보기가 안 보이는 경우

**해결 방법 1: 온라인 서버 확인**
```
설정이 이미 되어 있음:
- 서버: https://www.plantuml.com/plantuml
- 렌더링: PlantUMLServer
```

**해결 방법 2: Extension 재시작**
1. `Ctrl + Shift + P`
2. `Developer: Reload Window` 입력
3. Enter

**해결 방법 3: 온라인 뷰어 사용**
- https://www.plantuml.com/plantuml/uml/
- 파일 내용 복사 & 붙여넣기

### ❌ Java 관련 에러가 뜨는 경우

현재 설정은 **Java 없이** 온라인 서버를 사용합니다.
- Java 설치 불필요
- 인터넷 연결만 있으면 OK

만약 로컬 렌더링을 원한다면:
1. Java 다운로드: https://www.java.com/ko/download/
2. 설치 후 VS Code 재시작

### ❌ C4 다이어그램이 안 보이는 경우

`architecture_diagram.puml`은 C4 모델을 사용합니다:
- 온라인 서버가 자동으로 C4 라이브러리 로드
- 별도 설정 불필요

## 📸 스크린샷 예시

### 미리보기 화면:
```
┌─────────────────────────────────────┐
│ class_diagram.puml          [Alt+D] │
├─────────────────────────────────────┤
│ @startuml                           │
│                                     │
│ class CompanyAnalyzer {             │
│   +analyze_company()                │
│ }                                   │
│                                     │
│ @enduml                             │
└─────────────────────────────────────┘
         ⬇️ Alt + D
┌─────────────────────────────────────┐
│ Preview: class_diagram.puml    [X]  │
├─────────────────────────────────────┤
│                                     │
│    ┌─────────────────────┐          │
│    │ CompanyAnalyzer     │          │
│    ├─────────────────────┤          │
│    │ +analyze_company()  │          │
│    └─────────────────────┘          │
│                                     │
└─────────────────────────────────────┘
```

## 🌐 추가 리소스

### PlantUML 문법
- 공식 문서: https://plantuml.com/ko/
- 클래스 다이어그램: https://plantuml.com/ko/class-diagram
- 시퀀스 다이어그램: https://plantuml.com/ko/sequence-diagram

### 온라인 도구
- **PlantUML Editor**: https://www.plantuml.com/plantuml/uml/
- **PlantText**: https://www.planttext.com/
- **LiveUML**: https://liveuml.com/

## ✨ 시작하기

지금 바로 시도해보세요:

```bash
# VS Code에서 다이어그램 열기
code diagrams/class_diagram.puml

# 미리보기: Alt + D
# 내보내기: Alt + E
```

**축하합니다! 🎉 PlantUML 환경 설정이 완료되었습니다!**


