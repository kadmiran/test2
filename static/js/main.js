/**
 * 메인 초기화 및 유틸리티 모듈
 * DOM 로드 시 초기화 및 이벤트 리스너 등록
 */

// 다이어그램 표시 상태 확인 함수
function checkDiagramVisibility() {
    const diagramElement = document.getElementById('architectureDiagram');
    if (!diagramElement) {
        console.error('❌ 다이어그램 요소가 존재하지 않습니다.');
        return false;
    }
    
    const computedStyle = window.getComputedStyle(diagramElement);
    const isVisible = computedStyle.display !== 'none' && 
                     computedStyle.visibility !== 'hidden' && 
                     parseFloat(computedStyle.opacity) > 0 &&
                     diagramElement.offsetWidth > 0 &&
                     diagramElement.offsetHeight > 0;
    
    console.log('🔍 다이어그램 표시 상태 확인:');
    console.log('  - display:', computedStyle.display);
    console.log('  - visibility:', computedStyle.visibility);
    console.log('  - opacity:', computedStyle.opacity);
    console.log('  - width:', computedStyle.width);
    console.log('  - height:', computedStyle.height);
    console.log('  - offsetWidth:', diagramElement.offsetWidth);
    console.log('  - offsetHeight:', diagramElement.offsetHeight);
    console.log('  - clientWidth:', diagramElement.clientWidth);
    console.log('  - clientHeight:', diagramElement.clientHeight);
    console.log('  - scrollWidth:', diagramElement.scrollWidth);
    console.log('  - scrollHeight:', diagramElement.scrollHeight);
    console.log('  - isVisible:', isVisible);
    
    if (!isVisible) {
        console.warn('⚠️ 다이어그램이 보이지 않는 이유:');
        if (computedStyle.display === 'none') console.warn('  - display가 none입니다');
        if (computedStyle.visibility === 'hidden') console.warn('  - visibility가 hidden입니다');
        if (parseFloat(computedStyle.opacity) <= 0) console.warn('  - opacity가 0 이하입니다');
        if (diagramElement.offsetWidth <= 0) console.warn('  - offsetWidth가 0 이하입니다');
        if (diagramElement.offsetHeight <= 0) console.warn('  - offsetHeight가 0 이하입니다');
    }
    
    return isVisible;
}

// 예시 질문 설정
function setQuery(query) {
    document.getElementById('userQuery').value = query;
}

// 즉시 실행 (DOM 로드 전)
console.log('🚀 기업 분석 AI 초기화 중...');
console.log('📋 현재 DOM 상태:', document.readyState);
console.log('📋 document.body 존재 여부:', !!document.body);

// 다이어그램 즉시 표시 시도
console.log('🔍 다이어그램 요소 찾기 시도...');
const diagramElement = document.getElementById('architectureDiagram');
if (diagramElement) {
    console.log('✅ architectureDiagram 요소 발견:', diagramElement);
    console.log('📊 현재 스타일 상태:');
    console.log('  - display:', window.getComputedStyle(diagramElement).display);
    console.log('  - visibility:', window.getComputedStyle(diagramElement).visibility);
    console.log('  - opacity:', window.getComputedStyle(diagramElement).opacity);
    console.log('  - position:', window.getComputedStyle(diagramElement).position);
    console.log('  - z-index:', window.getComputedStyle(diagramElement).zIndex);
    console.log('  - 현재 클래스:', diagramElement.className);
    
    diagramElement.classList.add('show');
    console.log('✅ 다이어그램 show 클래스 추가 완료');
    console.log('  - 추가 후 클래스:', diagramElement.className);
    
    // HTML 인라인 스타일로 크기가 이미 설정되어 있음
    console.log('📋 HTML 인라인 스타일로 크기 설정됨');
    
    // 클래스 추가 후 다시 확인
    console.log('📊 클래스 추가 후 스타일 상태:');
    console.log('  - display:', window.getComputedStyle(diagramElement).display);
    console.log('  - visibility:', window.getComputedStyle(diagramElement).visibility);
    console.log('  - opacity:', window.getComputedStyle(diagramElement).opacity);
    console.log('  - position:', window.getComputedStyle(diagramElement).position);
    console.log('  - z-index:', window.getComputedStyle(diagramElement).zIndex);
    console.log('  - width:', window.getComputedStyle(diagramElement).width);
    console.log('  - height:', window.getComputedStyle(diagramElement).height);
    console.log('  - offsetWidth:', diagramElement.offsetWidth);
    console.log('  - offsetHeight:', diagramElement.offsetHeight);
    
    // 부모 요소 확인
    console.log('📋 부모 요소 확인:');
    console.log('  - parentElement:', diagramElement.parentElement);
    console.log('  - parentElement display:', diagramElement.parentElement ? window.getComputedStyle(diagramElement.parentElement).display : 'N/A');
    console.log('  - parentElement visibility:', diagramElement.parentElement ? window.getComputedStyle(diagramElement.parentElement).visibility : 'N/A');
} else {
    console.error('❌ architectureDiagram 요소를 찾을 수 없습니다.');
    console.log('📋 사용 가능한 모든 div 요소들:');
    const allDivs = document.querySelectorAll('div');
    allDivs.forEach((div, index) => {
        if (div.id) {
            console.log(`  [${index}] id="${div.id}" class="${div.className}"`);
        }
    });
}

// DOM 로드 시 초기화
document.addEventListener('DOMContentLoaded', function() {
    console.log('📄 DOM 로드 완료, 초기화 계속...');
    
    // 다이어그램 재확인 및 표시
    console.log('🔍 DOM 로드 후 다이어그램 재확인...');
    const diagramElement = document.getElementById('architectureDiagram');
    if (diagramElement) {
        console.log('✅ DOM 로드 후 architectureDiagram 요소 재발견:', diagramElement);
        console.log('📊 DOM 로드 후 스타일 상태:');
        console.log('  - display:', window.getComputedStyle(diagramElement).display);
        console.log('  - visibility:', window.getComputedStyle(diagramElement).visibility);
        console.log('  - opacity:', window.getComputedStyle(diagramElement).opacity);
        console.log('  - position:', window.getComputedStyle(diagramElement).position);
        console.log('  - z-index:', window.getComputedStyle(diagramElement).zIndex);
        console.log('  - classes:', diagramElement.className);
        console.log('  - offsetWidth:', diagramElement.offsetWidth);
        console.log('  - offsetHeight:', diagramElement.offsetHeight);
        console.log('  - clientWidth:', diagramElement.clientWidth);
        console.log('  - clientHeight:', diagramElement.clientHeight);
        
        // 다이어그램 컨테이너 확인
        const diagramContainer = diagramElement.querySelector('.diagram-container');
        if (diagramContainer) {
            console.log('📋 다이어그램 컨테이너 확인:');
            console.log('  - container display:', window.getComputedStyle(diagramContainer).display);
            console.log('  - container visibility:', window.getComputedStyle(diagramContainer).visibility);
            console.log('  - container opacity:', window.getComputedStyle(diagramContainer).opacity);
            console.log('  - container offsetWidth:', diagramContainer.offsetWidth);
            console.log('  - container offsetHeight:', diagramContainer.offsetHeight);
        } else {
            console.warn('⚠️ 다이어그램 컨테이너를 찾을 수 없습니다.');
        }
        
        diagramElement.classList.add('show');
        console.log('✅ DOM 로드 후 다이어그램 show 클래스 추가 완료');
        
        // HTML 인라인 스타일로 크기가 이미 설정되어 있음
        console.log('📋 DOM 로드 후 - HTML 인라인 스타일로 크기 설정됨');
        
        // 최종 상태 확인
        console.log('📊 최종 스타일 상태:');
        console.log('  - display:', window.getComputedStyle(diagramElement).display);
        console.log('  - visibility:', window.getComputedStyle(diagramElement).visibility);
        console.log('  - opacity:', window.getComputedStyle(diagramElement).opacity);
        console.log('  - position:', window.getComputedStyle(diagramElement).position);
        console.log('  - z-index:', window.getComputedStyle(diagramElement).zIndex);
        console.log('  - classes:', diagramElement.className);
        console.log('  - width:', window.getComputedStyle(diagramElement).width);
        console.log('  - height:', window.getComputedStyle(diagramElement).height);
        console.log('  - offsetWidth:', diagramElement.offsetWidth);
        console.log('  - offsetHeight:', diagramElement.offsetHeight);
        
        // 다이어그램 표시 상태 최종 확인
        console.log('🔍 다이어그램 표시 상태 최종 확인...');
        checkDiagramVisibility();
    } else {
        console.error('❌ DOM 로드 후에도 architectureDiagram 요소를 찾을 수 없습니다.');
        console.log('📋 사용 가능한 모든 요소들:');
        const allElements = document.querySelectorAll('*[id]');
        allElements.forEach((el, index) => {
            console.log(`  [${index}] <${el.tagName}> id="${el.id}" class="${el.className}"`);
        });
    }
    
    // 다이어그램 즉시 초기화
    if (typeof architectureDiagram !== 'undefined') {
        console.log('🏗️ 아키텍처 다이어그램 초기화 중...');
        console.log('📋 architectureDiagram 객체:', architectureDiagram);
        
        try {
            const success = architectureDiagram.init();
            if (success) {
                console.log('✅ 다이어그램 초기화 완료');
                
                // 초기화 후 컴포넌트 상태 확인
                console.log('🔍 초기화 후 컴포넌트 상태 확인...');
                const components = ['comp-frontend', 'comp-webserver', 'comp-dart', 'comp-naver', 'comp-vectordb', 'comp-midm', 'comp-gemini'];
                components.forEach(compId => {
                    const comp = document.getElementById(compId);
                    if (comp) {
                        const status = comp.querySelector('.component-status');
                        console.log(`  - ${compId}: ${status ? status.textContent : '상태 없음'}`);
                    } else {
                        console.warn(`  - ${compId}: 요소 없음`);
                    }
                });
                
                // 다이어그램 초기화 후 표시 상태 재확인
                console.log('🔍 다이어그램 초기화 후 표시 상태 재확인...');
                checkDiagramVisibility();
            } else {
                console.error('❌ 다이어그램 초기화 실패');
            }
        } catch (error) {
            console.error('❌ 다이어그램 초기화 중 오류:', error);
        }
    } else {
        console.warn('⚠️ architectureDiagram이 정의되지 않았습니다.');
        console.log('📋 사용 가능한 전역 객체들:', Object.keys(window).filter(key => key.includes('diagram') || key.includes('Diagram')));
    }
    
    // VectorDB 통계 자동 로드
    if (typeof loadVectorDBStats === 'function') {
        loadVectorDBStats();
    }
    
    // 폼 제출 이벤트 리스너 등록
    const form = document.getElementById('analysisForm');
    if (form) {
        form.addEventListener('submit', handleAnalysisSubmit);
    }
    
    console.log('✅ 초기화 완료');
});

// DOM 로드 전에도 실행 (즉시 실행)
(function() {
    console.log('⚡ 즉시 실행: 기업 분석 AI 준비 중...');
})();

