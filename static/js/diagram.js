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
            // 1행: Frontend → Server
            { from: 'frontend', to: 'webserver', id: 'arrow-frontend-webserver' },
            
            // Server → 2행 (VectorDB, DART, Naver)
            { from: 'webserver', to: 'vectordb', id: 'arrow-webserver-vectordb' },
            { from: 'webserver', to: 'dart', id: 'arrow-webserver-dart' },
            { from: 'webserver', to: 'naver', id: 'arrow-webserver-naver' },
            
            // 2행 → VectorDB
            { from: 'dart', to: 'vectordb', id: 'arrow-dart-vectordb' },
            { from: 'naver', to: 'vectordb', id: 'arrow-naver-vectordb' },
            
            // VectorDB → 3행 (Midm, Gemini)
            { from: 'vectordb', to: 'midm', id: 'arrow-vectordb-midm' },
            { from: 'vectordb', to: 'gemini', id: 'arrow-vectordb-gemini' },
            
            // 3행 내부
            { from: 'midm', to: 'gemini', id: 'arrow-midm-gemini' },
            
            // Gemini → Server (결과 반환)
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
    
    activateArrow(arrowId, duration = 3000) {
        const arrow = this.arrows[arrowId];
        if (arrow) {
            arrow.classList.add('active');
            // duration이 0이면 계속 켜둠, 아니면 지정된 시간 후에 비활성화
            if (duration > 0) {
                setTimeout(() => {
                    arrow.classList.remove('active');
                }, duration);
            }
            // duration이 0이면 아무 것도 안 함 = 계속 active 상태 유지
        }
    },
    
    deactivateArrow(arrowId) {
        const arrow = this.arrows[arrowId];
        if (arrow) {
            arrow.classList.remove('active');
        }
    },
    
    showConnection(from, to, duration = 3000) {
        const arrowId = `arrow-${from}-${to}`;
        this.activateArrow(arrowId, duration);
    }
};

// 컴포넌트 상태 매핑 (로그 키워드 → 컴포넌트)
const componentMap = {
    'dart': { name: 'dart', connections: ['webserver', 'dart'] },
    'midm': { name: 'midm', connections: ['webserver', 'vectordb', 'midm'] },
    'naver': { name: 'naver', connections: ['webserver', 'naver'] },
    'vectordb': { name: 'vectordb', connections: ['webserver', 'vectordb'] },
    'gemini': { name: 'gemini', connections: ['vectordb', 'gemini'] }
};

function updateDiagramFromMessage(message) {
    const msg = message.toLowerCase();
    
    // 분석 시작
    if (msg.includes('분석 시작') || msg.includes('분석 요청')) {
        architectureDiagram.activate('frontend', '요청 전송');
        architectureDiagram.showConnection('frontend', 'webserver', 2000);
        setTimeout(() => {
            architectureDiagram.activate('webserver', '요청 수신');
            architectureDiagram.deactivate('frontend', '대기중');
        }, 500);
    }
    
    // 🔵 시작 로그 처리 (통합)
    const startMatch = msg.match(/🔵\s*(dart|midm|naver|vectordb|gemini)/);
    if (startMatch) {
        const component = startMatch[1];
        const statusMap = {
            'dart': '처리중',
            'midm': '질문 분석',
            'naver': '크롤링중',
            'vectordb': '처리중',
            'gemini': 'AI 분석중'
        };
        
        // midm 로그는 gemini로 처리 (실제로는 Gemini 사용)
        const actualComponent = component === 'midm' ? 'gemini' : component;
        architectureDiagram.activate(actualComponent, statusMap[component]);
        
        // 연결 화살표 표시
        if (component === 'midm' || component === 'gemini') {
            architectureDiagram.showConnection('webserver', 'vectordb', 0);
            architectureDiagram.showConnection('vectordb', 'gemini', 0);
        } else {
            architectureDiagram.showConnection('webserver', component, 0);
        }
    }
    
    // ⚪ 완료 로그 처리 (통합)
    const endMatch = msg.match(/⚪\s*(dart|midm|naver|vectordb|gemini)/);
    if (endMatch) {
        const component = endMatch[1];
        // midm 로그는 gemini로 처리 (실제로는 Gemini 사용)
        const actualComponent = component === 'midm' ? 'gemini' : component;
        setTimeout(() => {
            architectureDiagram.deactivate(actualComponent, '완료');
            
            // Gemini 완료 시 결과 반환
            if (component === 'gemini' || component === 'midm') {
                architectureDiagram.showConnection('gemini', 'webserver', 2000);
            }
        }, 800);
    }
    
    // 전체 분석 완료
    if (msg.includes('전체 분석 완료') || msg.includes('분석이 완료되었습니다')) {
        setTimeout(() => {
            ['frontend', 'webserver', 'dart', 'naver', 'vectordb', 'midm', 'gemini'].forEach(comp => {
                architectureDiagram.deactivate(comp, '대기중');
            });
        }, 2000);
    }
}

// DOM 로드 후 다이어그램 초기화
document.addEventListener('DOMContentLoaded', function() {
    // 약간의 지연을 두고 초기화 (컴포넌트가 렌더링된 후)
    setTimeout(() => {
        architectureDiagram.init();
    }, 100);
});
