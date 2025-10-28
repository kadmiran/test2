/**
 * VectorDB 관리 모듈
 * VectorDB 통계 로드 및 초기화 기능
 */

// VectorDB 통계 로드
async function loadVectorDBStats() {
    try {
        const response = await fetch('/vectordb_stats');
        const data = await response.json();
        
        if (data.success) {
            const stats = data.stats;
            const statsDiv = document.getElementById('vectordbStats');
            statsDiv.innerHTML = `
                <div class="stat-item">📊 총 보고서: ${stats.total_reports}개</div>
                <div class="stat-item">📝 총 청크: ${stats.total_chunks.toLocaleString()}개</div>
                <div class="stat-item">💾 총 데이터: ${stats.total_size_chars.toLocaleString()}자</div>
                <div class="stat-item">🏢 회사 수: ${stats.num_companies}개</div>
                ${stats.companies.length > 0 ? `<div class="stat-item">📋 회사 목록: ${stats.companies.join(', ')}</div>` : ''}
            `;
        } else {
            document.getElementById('vectordbStats').innerHTML = 
                '<div class="stat-item">⚠️ 통계 로딩 실패</div>';
        }
    } catch (error) {
        console.error('VectorDB 통계 로딩 오류:', error);
        document.getElementById('vectordbStats').innerHTML = 
            '<div class="stat-item">❌ 통계 로딩 오류</div>';
    }
}

// VectorDB 초기화
async function resetVectorDB() {
    if (!confirm('⚠️ VectorDB의 모든 데이터가 삭제됩니다.\n\n캐시된 모든 보고서가 제거되며, 다음 분석 시 처음부터 다시 다운로드됩니다.\n\n정말 초기화하시겠습니까?')) {
        return;
    }

    const resetBtn = document.getElementById('resetVectorDbBtn');
    const originalText = resetBtn.innerHTML;
    
    try {
        resetBtn.disabled = true;
        resetBtn.innerHTML = '🔄 초기화 중...';
        
        const response = await fetch('/reset_vectordb', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert('✅ VectorDB가 성공적으로 초기화되었습니다.');
            // 통계 다시 로드
            await loadVectorDBStats();
        } else {
            alert('❌ VectorDB 초기화 실패: ' + (data.error || '알 수 없는 오류'));
        }
    } catch (error) {
        console.error('VectorDB 초기화 오류:', error);
        alert('❌ 오류 발생: ' + error.message);
    } finally {
        resetBtn.disabled = false;
        resetBtn.innerHTML = originalText;
    }
}

