/**
 * 시스템 아키텍처 다이어그램 관리 모듈
 * 실시간으로 컴포넌트 간 상호작용을 시각화
 */

const architectureDiagram = {
    components: {
        'frontend': document.getElementById('comp-frontend'),
        'webserver': document.getElementById('comp-webserver'),
        'dart': document.getElementById('comp-dart'),
        'naver': document.getElementById('comp-naver'),
        'vectordb': document.getElementById('comp-vectordb'),
        'midm': document.getElementById('comp-midm'),
        'gemini': document.getElementById('comp-gemini')
    },
    
    activate(componentName, status = '처리중') {
        const comp = this.components[componentName];
        if (comp) {
            comp.classList.add('active');
            const statusEl = comp.querySelector('.component-status');
            if (statusEl) statusEl.textContent = status;
        }
    },
    
    deactivate(componentName, status = '완료') {
        const comp = this.components[componentName];
        if (comp) {
            comp.classList.remove('active');
            const statusEl = comp.querySelector('.component-status');
            if (statusEl) statusEl.textContent = status;
        }
    },
    
    reset() {
        Object.keys(this.components).forEach(key => {
            const comp = this.components[key];
            comp.classList.remove('active');
            const statusEl = comp.querySelector('.component-status');
            if (statusEl) statusEl.textContent = '대기중';
        });
    },
    
    drawConnection(from, to) {
        // SVG 연결선 그리기 (선택적으로 구현)
        // 복잡성을 줄이기 위해 CSS 애니메이션으로 대체
    }
};

function updateDiagramFromMessage(message) {
    const msg = message.toLowerCase();
    
    // 1단계: 분석 시작
    if (msg.includes('분석 시작') || msg.includes('서버에서 분석 시작')) {
        architectureDiagram.activate('frontend', '요청 전송');
        architectureDiagram.activate('webserver', '요청 수신');
    }
    
    // 2단계: 회사 정보 조회
    if (msg.includes('회사 정보 조회 중') || msg.includes('1단계')) {
        architectureDiagram.activate('webserver', '처리중');
        architectureDiagram.activate('dart', '회사 검색');
    }
    
    if (msg.includes('회사 정보 조회 완료')) {
        architectureDiagram.deactivate('dart', '회사 확인');
    }
    
    // 3단계: 보고서 검색
    if (msg.includes('보고서 검색 중') || msg.includes('2단계')) {
        architectureDiagram.activate('dart', '보고서 검색');
        architectureDiagram.activate('midm', '질문 분석');
    }
    
    if (msg.includes('보고서를 찾았습니다')) {
        architectureDiagram.deactivate('midm', '분석 완료');
    }
    
    // 4단계: 보고서 다운로드
    if (msg.includes('보고서 다운로드 중') || msg.includes('3단계')) {
        architectureDiagram.activate('dart', '다운로드중');
    }
    
    // VectorDB 캐시 확인
    if (msg.includes('vectordb 캐시 확인') || msg.includes('캐시 확인 중')) {
        architectureDiagram.activate('vectordb', '캐시 검색');
    }
    
    if (msg.includes('vectordb에서 로드')) {
        architectureDiagram.deactivate('vectordb', '캐시 적중');
    }
    
    if (msg.includes('캐시 없음')) {
        architectureDiagram.deactivate('vectordb', '캐시 없음');
    }
    
    if (msg.includes('다운로드 완료') && !msg.includes('네이버')) {
        architectureDiagram.deactivate('dart', '다운로드 완료');
    }
    
    // 네이버 금융 크롤링
    if (msg.includes('네이버 금융') || msg.includes('증권사 리포트')) {
        architectureDiagram.activate('naver', '리포트 수집');
    }
    
    if (msg.includes('종목분석 리포트') && msg.includes('수집 완료')) {
        architectureDiagram.deactivate('naver', '종목분석 완료');
    }
    
    if (msg.includes('산업분석 리포트') && msg.includes('수집 완료')) {
        architectureDiagram.deactivate('naver', '산업분석 완료');
    }
    
    // VectorDB 저장
    if (msg.includes('vectordb에 리포트 저장')) {
        architectureDiagram.activate('vectordb', '저장 중');
    }
    
    if (msg.includes('vectordb 저장 완료')) {
        architectureDiagram.deactivate('vectordb', '저장 완료');
    }
    
    // 5단계: AI 분석
    if (msg.includes('gemini ai 분석 중') || msg.includes('4단계')) {
        architectureDiagram.activate('gemini', 'AI 분석중');
        architectureDiagram.activate('vectordb', '데이터 제공');
    }
    
    if (msg.includes('관련 청크 발견')) {
        architectureDiagram.activate('vectordb', '검색 완료');
    }
    
    if (msg.includes('ai 분석 완료')) {
        architectureDiagram.deactivate('gemini', '분석 완료');
        architectureDiagram.deactivate('vectordb', '완료');
        architectureDiagram.activate('webserver', '결과 생성');
    }
    
    // 최종: 결과 전달
    if (msg.includes('분석 완료! 결과를 가져오는 중')) {
        architectureDiagram.deactivate('webserver', '완료');
        architectureDiagram.activate('frontend', '결과 표시');
        setTimeout(() => {
            architectureDiagram.deactivate('frontend', '표시 완료');
        }, 2000);
    }
}

