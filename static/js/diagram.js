/**
 * 시스템 아키텍처 다이어그램 관리 모듈
 * 실시간으로 컴포넌트 간 상호작용을 시각화
 */

const architectureDiagram = {
    components: {},
    arrows: {},
    svgNS: 'http://www.w3.org/2000/svg',
    
    init() {
        // 컴포넌트 참조 저장
        this.components = {
            'frontend': document.getElementById('comp-frontend'),
            'webserver': document.getElementById('comp-webserver'),
            'dart': document.getElementById('comp-dart'),
            'naver': document.getElementById('comp-naver'),
            'vectordb': document.getElementById('comp-vectordb'),
            'midm': document.getElementById('comp-midm'),
            'gemini': document.getElementById('comp-gemini')
        };
        
        // SVG 화살표 그리기
        this.drawAllConnections();
    },
    
    drawAllConnections() {
        const svg = document.getElementById('flowLines');
        if (!svg) return;
        
        // 연결 관계 정의 (from -> to)
        const connections = [
            // 1행: Frontend <-> Server <-> DART
            { from: 'frontend', to: 'webserver', id: 'arrow-frontend-webserver' },
            { from: 'webserver', to: 'dart', id: 'arrow-webserver-dart' },
            
            // 2행: Server -> Midm, VectorDB, Naver
            { from: 'webserver', to: 'midm', id: 'arrow-webserver-midm' },
            { from: 'webserver', to: 'vectordb', id: 'arrow-webserver-vectordb' },
            { from: 'webserver', to: 'naver', id: 'arrow-webserver-naver' },
            
            // DART -> VectorDB (캐시 확인)
            { from: 'dart', to: 'vectordb', id: 'arrow-dart-vectordb' },
            
            // Midm -> VectorDB (질문 분석 결과)
            { from: 'midm', to: 'vectordb', id: 'arrow-midm-vectordb' },
            
            // Naver -> VectorDB (리포트 저장)
            { from: 'naver', to: 'vectordb', id: 'arrow-naver-vectordb' },
            
            // VectorDB -> Gemini (데이터 제공)
            { from: 'vectordb', to: 'gemini', id: 'arrow-vectordb-gemini' },
            
            // Gemini -> Server (결과 반환)
            { from: 'gemini', to: 'webserver', id: 'arrow-gemini-webserver' }
        ];
        
        connections.forEach(conn => {
            const arrow = this.createArrow(conn.from, conn.to, conn.id);
            if (arrow) {
                svg.appendChild(arrow);
                this.arrows[conn.id] = arrow;
            }
        });
    },
    
    createArrow(fromId, toId, arrowId) {
        const fromComp = this.components[fromId];
        const toComp = this.components[toId];
        
        if (!fromComp || !toComp) return null;
        
        const fromRect = fromComp.getBoundingClientRect();
        const toRect = toComp.getBoundingClientRect();
        const containerRect = document.querySelector('.diagram-container').getBoundingClientRect();
        
        // 컴포넌트 중심점 계산
        const fromX = fromRect.left - containerRect.left + fromRect.width / 2;
        const fromY = fromRect.top - containerRect.top + fromRect.height / 2;
        const toX = toRect.left - containerRect.left + toRect.width / 2;
        const toY = toRect.top - containerRect.top + toRect.height / 2;
        
        // 경로 생성
        let pathD;
        
        // 같은 행에 있는 경우 (수평선)
        if (Math.abs(fromY - toY) < 20) {
            pathD = `M ${fromX},${fromY} L ${toX},${toY}`;
        } 
        // 수직 또는 대각선 연결
        else {
            // 부드러운 곡선 경로
            const dx = toX - fromX;
            const dy = toY - fromY;
            const midY = fromY + dy / 2;
            
            // S 곡선 생성
            pathD = `M ${fromX},${fromY} C ${fromX},${midY} ${toX},${midY} ${toX},${toY}`;
        }
        
        const path = document.createElementNS(this.svgNS, 'path');
        path.setAttribute('d', pathD);
        path.setAttribute('class', 'connection-arrow');
        path.setAttribute('id', arrowId);
        path.setAttribute('marker-end', 'url(#arrowhead)');
        path.setAttribute('stroke-dasharray', '5,5');
        
        return path;
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
            if (comp) {
                comp.classList.remove('active');
                const statusEl = comp.querySelector('.component-status');
                if (statusEl) statusEl.textContent = '대기중';
            }
        });
        
        // 모든 화살표 비활성화
        Object.values(this.arrows).forEach(arrow => {
            if (arrow) arrow.classList.remove('active');
        });
    },
    
    activateArrow(arrowId) {
        const arrow = this.arrows[arrowId];
        if (arrow) {
            arrow.classList.add('active');
            setTimeout(() => {
                arrow.classList.remove('active');
            }, 2000);
        }
    },
    
    showConnection(from, to) {
        const arrowId = `arrow-${from}-${to}`;
        this.activateArrow(arrowId);
    }
};

function updateDiagramFromMessage(message) {
    const msg = message.toLowerCase();
    
    // 분석 시작
    if (msg.includes('분석 시작') || msg.includes('분석 요청')) {
        architectureDiagram.activate('frontend', '요청 전송');
        architectureDiagram.showConnection('frontend', 'webserver');
        setTimeout(() => {
            architectureDiagram.activate('webserver', '요청 수신');
        }, 300);
    }
    
    if (msg.includes('서버에서 분석 시작')) {
        architectureDiagram.activate('webserver', '분석 시작');
    }
    
    // 1단계: 회사 정보 조회
    if (msg.includes('1단계') || msg.includes('회사 정보 조회 중')) {
        architectureDiagram.activate('webserver', '처리중');
        architectureDiagram.activate('dart', '회사 검색');
        architectureDiagram.showConnection('webserver', 'dart');
    }
    
    if (msg.includes('회사 정보 조회 완료')) {
        architectureDiagram.deactivate('dart', '회사 확인');
    }
    
    // 2단계: 보고서 검색 (AI 질문 분석)
    if (msg.includes('2단계') || msg.includes('보고서 검색 중')) {
        architectureDiagram.activate('dart', '보고서 검색');
        architectureDiagram.activate('midm', '질문 분석');
        architectureDiagram.showConnection('webserver', 'midm');
    }
    
    if (msg.includes('ai가 추천한') || msg.includes('보고서를 찾았습니다')) {
        architectureDiagram.deactivate('midm', '분석 완료');
    }
    
    // 3단계: 보고서 다운로드
    if (msg.includes('3단계') || msg.includes('보고서 다운로드 중')) {
        architectureDiagram.activate('dart', '다운로드중');
    }
    
    // VectorDB 캐시 확인
    if (msg.includes('vectordb') && msg.includes('캐시 확인')) {
        architectureDiagram.activate('vectordb', '캐시 검색');
        architectureDiagram.showConnection('webserver', 'vectordb');
    }
    
    if (msg.includes('vectordb에서 로드')) {
        architectureDiagram.activate('vectordb', '캐시 적중');
        setTimeout(() => {
            architectureDiagram.deactivate('vectordb', '로드 완료');
        }, 1000);
    }
    
    if (msg.includes('캐시 없음')) {
        architectureDiagram.deactivate('vectordb', '캐시 없음');
        architectureDiagram.activate('dart', 'API 다운로드');
    }
    
    if (msg.includes('다운로드 완료') && !msg.includes('네이버')) {
        architectureDiagram.deactivate('dart', '다운로드 완료');
    }
    
    // 네이버 금융 크롤링
    if (msg.includes('네이버 금융') || msg.includes('증권사 리포트')) {
        architectureDiagram.activate('naver', '크롤링중');
        architectureDiagram.showConnection('webserver', 'naver');
    }
    
    if (msg.includes('종목분석 리포트') && msg.includes('수집 완료')) {
        architectureDiagram.activate('naver', '종목분석 완료');
    }
    
    if (msg.includes('산업분석 리포트') && msg.includes('수집 완료')) {
        architectureDiagram.deactivate('naver', '산업분석 완료');
    }
    
    // VectorDB 저장
    if (msg.includes('vectordb에 리포트 저장') || msg.includes('vectordb 저장 중')) {
        architectureDiagram.activate('vectordb', '저장 중');
        architectureDiagram.showConnection('webserver', 'vectordb');
    }
    
    if (msg.includes('vectordb 저장 완료')) {
        architectureDiagram.deactivate('vectordb', '저장 완료');
    }
    
    // 4단계: AI 분석
    if (msg.includes('4단계') || msg.includes('ai 분석 중')) {
        architectureDiagram.activate('gemini', 'AI 분석중');
        architectureDiagram.activate('vectordb', '데이터 제공');
        architectureDiagram.showConnection('vectordb', 'gemini');
    }
    
    if (msg.includes('관련 청크 발견') || msg.includes('vectordb에서') && msg.includes('검색')) {
        architectureDiagram.activate('vectordb', '검색 완료');
    }
    
    if (msg.includes('gemini') && msg.includes('분석 중')) {
        architectureDiagram.activate('gemini', 'AI 분석중');
    }
    
    if (msg.includes('ai 분석 완료') || msg.includes('분석 완료!')) {
        architectureDiagram.deactivate('gemini', '분석 완료');
        architectureDiagram.deactivate('vectordb', '완료');
        architectureDiagram.activate('webserver', '결과 생성');
        architectureDiagram.showConnection('gemini', 'webserver');
    }
    
    // 최종: 결과 전달
    if (msg.includes('결과를 가져오는 중')) {
        architectureDiagram.deactivate('webserver', '완료');
        architectureDiagram.activate('frontend', '결과 표시');
        architectureDiagram.showConnection('webserver', 'frontend');
        
        setTimeout(() => {
            architectureDiagram.deactivate('frontend', '표시 완료');
        }, 2000);
    }
    
    // 파일 정리
    if (msg.includes('다운로드 파일 정리') || msg.includes('파일 정리')) {
        architectureDiagram.activate('webserver', '정리 중');
        setTimeout(() => {
            architectureDiagram.deactivate('webserver', '정리 완료');
        }, 1000);
    }
}

// DOM 로드 후 다이어그램 초기화
document.addEventListener('DOMContentLoaded', function() {
    // 약간의 지연을 두고 초기화 (컴포넌트가 렌더링된 후)
    setTimeout(() => {
        architectureDiagram.init();
    }, 100);
});
