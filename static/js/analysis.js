/**
 * 기업 분석 메인 로직 모듈
 * 분석 요청, 상태 스트리밍, 결과 표시 기능
 */

let currentSessionId = null;

// 상태 메시지 추가
function addStatusMessage(message, type = 'info') {
    const statusMessages = document.getElementById('statusMessages');
    const statusLog = document.getElementById('statusLog');
    
    const div = document.createElement('div');
    div.className = `status-item ${type}`;
    div.textContent = `${new Date().toLocaleTimeString()} - ${message}`;
    statusMessages.appendChild(div);
    statusLog.scrollTop = statusLog.scrollHeight;
    
    // 다이어그램 업데이트
    updateDiagramFromMessage(message);
}

// 분석 폼 제출 핸들러
async function handleAnalysisSubmit(e) {
    e.preventDefault();

    const companyName = document.getElementById('companyName').value;
    const userQuery = document.getElementById('userQuery').value;
    const sessionId = Date.now().toString();
    currentSessionId = sessionId;

    const loading = document.getElementById('loading');
    const statusLog = document.getElementById('statusLog');
    const statusMessages = document.getElementById('statusMessages');
    const result = document.getElementById('result');
    const error = document.getElementById('error');
    const submitBtn = document.getElementById('submitBtn');

    // UI 초기화
    loading.classList.add('show');
    statusLog.style.display = 'block';
    statusMessages.innerHTML = '';
    result.classList.remove('show');
    error.classList.remove('show');
    submitBtn.disabled = true;

    // 다이어그램 리셋 및 표시
    architectureDiagram.reset();
    document.getElementById('architectureDiagram').classList.add('show');

    addStatusMessage('분석 시작...', 'info');

    try {
        // 1. 분석 요청 시작
        const response = await fetch('/analyze_stream', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                company_name: companyName,
                user_query: userQuery,
                session_id: sessionId
            })
        });

        const startData = await response.json();

        if (!startData.success) {
            throw new Error(startData.error || '분석 시작 실패');
        }

        addStatusMessage('서버에서 분석 시작됨', 'success');

        // 2. SSE로 상태 업데이트 수신
        const eventSource = new EventSource(`/status/${sessionId}`);

        eventSource.onmessage = function(event) {
            const data = JSON.parse(event.data);
            
            if (data.type === 'status') {
                addStatusMessage(data.message, 'info');
            } else if (data.type === 'done') {
                addStatusMessage('분석 완료! 결과를 가져오는 중...', 'success');
                eventSource.close();
                
                // 3. 결과 가져오기
                fetchAnalysisResult(sessionId, loading, submitBtn, result, error);
            } else if (data.type === 'error') {
                addStatusMessage('오류 발생', 'error');
                eventSource.close();
                loading.classList.remove('show');
                submitBtn.disabled = false;
                error.textContent = data.message || '분석 중 오류가 발생했습니다.';
                error.classList.add('show');
            }
        };

        eventSource.onerror = function(err) {
            console.error('EventSource 오류:', err);
            addStatusMessage('연결 오류 발생', 'error');
            eventSource.close();
        };

    } catch (err) {
        loading.classList.remove('show');
        submitBtn.disabled = false;
        error.textContent = '서버와 통신 중 오류가 발생했습니다: ' + err.message;
        error.classList.add('show');
        addStatusMessage(`오류: ${err.message}`, 'error');
    }
}

// 분석 결과 가져오기
async function fetchAnalysisResult(sessionId, loading, submitBtn, result, error) {
    try {
        const res = await fetch(`/result/${sessionId}`);
        const data = await res.json();
        
        loading.classList.remove('show');
        submitBtn.disabled = false;

        if (data.success) {
            displayAnalysisResult(data);
        } else {
            error.textContent = data.error || '분석 중 오류가 발생했습니다.';
            error.classList.add('show');
        }
    } catch (err) {
        loading.classList.remove('show');
        submitBtn.disabled = false;
        error.textContent = '결과를 가져오는 중 오류가 발생했습니다: ' + err.message;
        error.classList.add('show');
    }
}

// 분석 결과 표시
function displayAnalysisResult(data) {
    const result = document.getElementById('result');
    
    // 회사명 및 메타 정보
    document.getElementById('resultCompanyName').textContent = `${data.company_name} 분석 결과`;
    document.getElementById('resultMeta').textContent = `종목코드: ${data.stock_code || 'N/A'}`;

    // 발견된 보고서 목록
    displayReportsList(data);

    // 분석 결과 (HTML 렌더링)
    const resultContent = document.getElementById('resultContent');
    if (data.analysis_html) {
        resultContent.innerHTML = data.analysis_html;
    } else {
        resultContent.textContent = data.analysis;
    }

    // PDF 다운로드 버튼 표시
    const downloadPdfBtn = document.getElementById('downloadPdfBtn');
    if (data.analysis || data.analysis_html) {
        downloadPdfBtn.style.display = 'inline-block';
    }

    result.classList.add('show');
    result.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// 보고서 목록 표시
function displayReportsList(data) {
    // DART 공시 보고서
    if (data.reports_found && data.reports_found.length > 0) {
        const reportsFound = document.getElementById('reportsFound');
        const reportsList = document.getElementById('reportsList');
        reportsList.innerHTML = '';
        
        data.reports_found.forEach(report => {
            const li = document.createElement('li');
            li.textContent = `📄 ${report.report_nm} (${report.rcept_dt})`;
            reportsList.appendChild(li);
        });
        
        reportsFound.style.display = 'block';
    }

    // 추가 DART 보고서
    if (data.additional_reports && data.additional_reports.length > 0) {
        const additionalReports = document.getElementById('additionalReports');
        const additionalReportsList = document.getElementById('additionalReportsList');
        additionalReportsList.innerHTML = '';
        
        data.additional_reports.forEach((report) => {
            const li = document.createElement('li');
            li.textContent = `📊 ${report.name} (${report.date})`;
            li.style.color = '#22543d';
            additionalReportsList.appendChild(li);
        });
        
        additionalReports.style.display = 'block';
    }

    // 네이버 종목분석 리포트
    if (data.naver_reports && data.naver_reports.company_reports && data.naver_reports.company_reports.length > 0) {
        const naverCompanyReports = document.getElementById('naverCompanyReports');
        const naverCompanyReportsList = document.getElementById('naverCompanyReportsList');
        naverCompanyReportsList.innerHTML = '';
        
        data.naver_reports.company_reports.forEach((report) => {
            const li = document.createElement('li');
            li.innerHTML = `📈 ${report.name} (${report.date})<br><span style="font-size: 0.85em; color: #999;">   URL: ${report.url.substring(0, 60)}...</span>`;
            li.style.color = '#9c4221';
            naverCompanyReportsList.appendChild(li);
        });
        
        naverCompanyReports.style.display = 'block';
    }

    // 네이버 산업분석 리포트
    if (data.naver_reports && data.naver_reports.industry_reports && data.naver_reports.industry_reports.length > 0) {
        const naverIndustryReports = document.getElementById('naverIndustryReports');
        const naverIndustryReportsList = document.getElementById('naverIndustryReportsList');
        naverIndustryReportsList.innerHTML = '';
        
        data.naver_reports.industry_reports.forEach((report) => {
            const li = document.createElement('li');
            li.innerHTML = `🏭 ${report.name} (${report.date})<br><span style="font-size: 0.85em; color: #999;">   URL: ${report.url.substring(0, 60)}...</span>`;
            li.style.color = '#2c5282';
            naverIndustryReportsList.appendChild(li);
        });
        
        naverIndustryReports.style.display = 'block';
    }
}

// PDF 다운로드
function downloadPDF() {
    if (!currentSessionId) {
        alert('⚠️ 다운로드할 세션이 없습니다.');
        return;
    }

    const downloadBtn = document.getElementById('downloadPdfBtn');
    const originalText = downloadBtn.innerHTML;
    
    try {
        downloadBtn.disabled = true;
        downloadBtn.innerHTML = '⏳ PDF 생성 중...';
        
        window.location.href = `/download/${currentSessionId}/pdf`;
        
        setTimeout(() => {
            downloadBtn.disabled = false;
            downloadBtn.innerHTML = originalText;
        }, 3000);
        
    } catch (err) {
        alert('❌ PDF 다운로드 중 오류가 발생했습니다: ' + err.message);
        downloadBtn.disabled = false;
        downloadBtn.innerHTML = originalText;
    }
}

