/**
 * 메인 초기화 및 유틸리티 모듈
 * DOM 로드 시 초기화 및 이벤트 리스너 등록
 */

// 예시 질문 설정
function setQuery(query) {
    document.getElementById('userQuery').value = query;
}

// 즉시 실행 (DOM 로드 전)
console.log('🚀 기업 분석 AI 초기화 중...');
// 다이어그램 즉시 표시
const diagramElement = document.getElementById('architectureDiagram');
if (diagramElement) {
    diagramElement.classList.add('show');
    console.log('✅ 다이어그램 show 클래스 추가 완료');
} else {
    console.warn('⚠️ architectureDiagram 요소를 찾을 수 없습니다.');
}

// DOM 로드 시 초기화
document.addEventListener('DOMContentLoaded', function() {
    console.log('📄 DOM 로드 완료, 초기화 계속...');
    
    // 다이어그램 즉시 표시
    const diagramElement = document.getElementById('architectureDiagram');
    if (diagramElement) {
        diagramElement.classList.add('show');
        console.log('✅ 다이어그램 show 클래스 추가 완료');
    } else {
        console.warn('⚠️ architectureDiagram 요소를 찾을 수 없습니다.');
    }
    
    // 다이어그램 즉시 초기화
    if (typeof architectureDiagram !== 'undefined') {
        console.log('🏗️ 아키텍처 다이어그램 초기화 중...');
        const success = architectureDiagram.init();
        if (success) {
            console.log('✅ 다이어그램 초기화 완료');
        } else {
            console.error('❌ 다이어그램 초기화 실패');
        }
    } else {
        console.warn('⚠️ architectureDiagram이 정의되지 않았습니다.');
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

