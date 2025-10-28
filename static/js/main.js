/**
 * 메인 초기화 및 유틸리티 모듈
 * DOM 로드 시 초기화 및 이벤트 리스너 등록
 */

// 예시 질문 설정
function setQuery(query) {
    document.getElementById('userQuery').value = query;
}

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 기업 분석 AI 초기화 중...');
    
    // VectorDB 통계 자동 로드
    loadVectorDBStats();
    
    // 폼 제출 이벤트 리스너 등록
    const form = document.getElementById('analysisForm');
    if (form) {
        form.addEventListener('submit', handleAnalysisSubmit);
    }
    
    console.log('✅ 초기화 완료');
});

