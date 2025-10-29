#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
회사 분석 웹 애플리케이션
Flask를 사용한 로컬 서버
"""

from flask import Flask, render_template, request, jsonify, Response, stream_with_context, send_file
from company_analyzer import CompanyAnalyzer
from llm_orchestrator import LLMOrchestrator, GeminiProvider, MidmProvider, PerplexityProvider
from config import config
import os
import json
import time
from queue import Queue
import logging
import zipfile
import markdown
import tempfile
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_LEFT, TA_CENTER
import re

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

print("=" * 60)
print("🚀 기업 분석 AI 애플리케이션 시작")
print("=" * 60)

# API 키 유효성 검증
print("🔑 API 키 유효성 검증 중...")
if not config.validate_api_keys():
    logger.error("API 키가 제대로 설정되지 않았습니다. config.py를 확인하세요.")
    raise ValueError("API 키 설정 오류")
print("✅ API 키 검증 완료")

# LLM Orchestrator 초기화
print("🤖 LLM Orchestrator 초기화 중...")
llm_orchestrator = LLMOrchestrator()
print("✅ LLM Orchestrator 초기화 완료")

# Gemini Provider 등록
print("✨ Gemini Provider 등록 중...")
gemini_provider = GeminiProvider(
    api_key=config.get_gemini_api_key(),
    model_candidates=config.GEMINI_MODEL_CANDIDATES
)
llm_orchestrator.register_provider(gemini_provider)
print("✅ Gemini Provider 등록 완료")

# Midm Provider 등록 (검색어 제안용)
print("🤖 Midm Provider 등록 중...")
if config.FRIENDLI_TOKEN and config.FRIENDLI_ENDPOINT_ID:
    midm_provider = MidmProvider(
        api_token=config.FRIENDLI_TOKEN,
        base_url=config.FRIENDLI_BASE_URL,
        endpoint_id=config.FRIENDLI_ENDPOINT_ID
    )
    llm_orchestrator.register_provider(midm_provider)
    print("✅ Midm Provider 등록 완료")
else:
    print("⚠️  Friendli 설정이 없어 Midm Provider를 건너뜁니다.")

# Perplexity Provider 등록 (질문 분석용)
print("🔍 Perplexity Provider 등록 중...")
if config.PERPLEXITY_API_KEY:
    perplexity_provider = PerplexityProvider(
        api_key=config.get_perplexity_api_key()
    )
    llm_orchestrator.register_provider(perplexity_provider, is_default=True)
    print("✅ Perplexity Provider 등록 완료 (기본 Provider)")
else:
    print("⚠️  Perplexity API 키가 설정되지 않았습니다.")
    print("   질문 분석에는 기본 Provider(Gemini)가 사용됩니다.")

# 작업별 라우팅 설정
print("🔀 LLM 작업별 라우팅 설정 중...")
for task_type, provider_name in config.LLM_TASK_ROUTING.items():
    try:
        llm_orchestrator.set_task_routing(task_type, provider_name)
        print(f"   ✅ {task_type} → {provider_name}")
    except ValueError as e:
        print(f"   ❌ 라우팅 설정 실패: {e}")
print("✅ 라우팅 설정 완료")

print("✅ LLM Orchestrator 초기화 완료")

# CompanyAnalyzer 인스턴스 생성 (LLM Orchestrator 주입)
print("🏢 CompanyAnalyzer 초기화 중...")
analyzer = CompanyAnalyzer(config.get_dart_api_key(), llm_orchestrator)
print("✅ CompanyAnalyzer 초기화 완료")

# 상태 업데이트를 위한 큐 및 결과 저장
print("📊 상태 관리 시스템 초기화 중...")
status_queues = {}
analysis_results = {}
print("✅ 상태 관리 시스템 초기화 완료")

print("=" * 60)
print("🎉 모든 초기화 완료! 서버를 시작합니다...")
print("=" * 60)

@app.route('/')
def index():
    """메인 페이지"""
    return render_template('index.html')

@app.route('/analyze_stream', methods=['POST'])
def analyze_stream():
    """회사 분석 API - 실시간 스트리밍"""
    try:
        data = request.json
        company_name = data.get('company_name', '').strip()
        user_query = data.get('user_query', '').strip()
        session_id = data.get('session_id', str(time.time()))
        exclude_opinions = data.get('exclude_opinions', False)
        
        logger.info(f"분석 요청 시작 - 회사: {company_name}, 세션: {session_id}")
        
        if not company_name:
            return jsonify({
                'success': False,
                'error': '회사명을 입력해주세요.'
            })
        
        if not user_query:
            return jsonify({
                'success': False,
                'error': '분석하고 싶은 내용을 입력해주세요.'
            })
        
        # 상태 큐 생성
        status_queue = Queue()
        status_queues[session_id] = status_queue
        
        def status_callback(message):
            """상태 업데이트 콜백"""
            logger.info(f"[{session_id}] {message}")
            status_queue.put(message)
        
        # 백그라운드에서 분석 수행
        import threading
        result_container = {}
        
        def run_analysis():
            try:
                result = analyzer.analyze_company(company_name, user_query, status_callback, exclude_opinions)
                analysis_results[session_id] = result  # 결과 저장
                status_queue.put('__DONE__')
                logger.info(f"분석 완료 - 세션: {session_id}")
            except Exception as e:
                logger.error(f"분석 오류 - 세션: {session_id}, 오류: {e}", exc_info=True)
                analysis_results[session_id] = {
                    'success': False,
                    'error': str(e)
                }
                status_queue.put('__ERROR__')
        
        thread = threading.Thread(target=run_analysis)
        thread.start()
        
        return jsonify({
            'success': True,
            'session_id': session_id
        })
        
    except Exception as e:
        logger.error(f"서버 오류: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'서버 오류: {str(e)}'
        })

@app.route('/status/<session_id>')
def status_stream(session_id):
    """상태 업데이트 스트리밍"""
    logger.info(f"상태 스트림 연결 - 세션: {session_id}")
    
    def generate():
        queue = status_queues.get(session_id)
        if not queue:
            yield f"data: {json.dumps({'type': 'error', 'message': '세션을 찾을 수 없습니다.'})}\n\n"
            return
        
        while True:
            try:
                message = queue.get(timeout=1)
                if message == '__DONE__' or message == '__ERROR__':
                    yield f"data: {json.dumps({'type': 'done'})}\n\n"
                    break
                yield f"data: {json.dumps({'type': 'status', 'message': message})}\n\n"
            except:
                # 타임아웃 - 연결 유지를 위한 heartbeat
                yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
    
    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@app.route('/result/<session_id>')
def get_result(session_id):
    """분석 결과 조회"""
    logger.info(f"결과 조회 - 세션: {session_id}")
    
    result = analysis_results.get(session_id)
    if not result:
        return jsonify({
            'success': False,
            'error': '결과를 찾을 수 없습니다. 분석이 완료되지 않았거나 세션이 만료되었습니다.'
        })
    
    # Markdown을 HTML로 변환
    if result.get('success') and result.get('analysis'):
        analysis_text = result['analysis']
        # Markdown 확장 기능 활성화
        html_content = markdown.markdown(
            analysis_text,
            extensions=['extra', 'nl2br', 'sane_lists', 'tables']
        )
        result['analysis_html'] = html_content
        logger.info(f"Markdown → HTML 변환 완료: {len(html_content)}자")
    
    # 결과 반환 후 정리
    if session_id in status_queues:
        del status_queues[session_id]
    
    return jsonify(result)

def register_korean_font():
    """한글 폰트 등록 (Windows 맑은 고딕)"""
    try:
        # Windows 맑은 고딕 폰트 등록
        font_path = "C:/Windows/Fonts/malgun.ttf"
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont('MalgunGothic', font_path))
            return 'MalgunGothic'
        
        # 폰트를 찾지 못한 경우 기본 폰트 사용
        logger.warning("한글 폰트를 찾지 못했습니다. 기본 폰트를 사용합니다.")
        return 'Helvetica'
    except Exception as e:
        logger.error(f"폰트 등록 오류: {e}")
        return 'Helvetica'

def markdown_to_pdf(markdown_text, company_name, user_query):
    """Markdown을 PDF로 변환"""
    try:
        # 한글 폰트 등록
        korean_font = register_korean_font()
        
        # 임시 PDF 파일 생성
        temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        temp_pdf.close()
        
        # PDF 문서 생성
        doc = SimpleDocTemplate(
            temp_pdf.name,
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=20*mm,
            bottomMargin=20*mm
        )
        
        # 스타일 정의
        styles = getSampleStyleSheet()
        
        # 한글 폰트 스타일 추가
        title_style = ParagraphStyle(
            'KoreanTitle',
            parent=styles['Heading1'],
            fontName=korean_font,
            fontSize=18,
            alignment=TA_CENTER,
            spaceAfter=12
        )
        
        heading2_style = ParagraphStyle(
            'KoreanHeading2',
            parent=styles['Heading2'],
            fontName=korean_font,
            fontSize=14,
            spaceAfter=10
        )
        
        heading3_style = ParagraphStyle(
            'KoreanHeading3',
            parent=styles['Heading3'],
            fontName=korean_font,
            fontSize=12,
            spaceAfter=8
        )
        
        body_style = ParagraphStyle(
            'KoreanBody',
            parent=styles['BodyText'],
            fontName=korean_font,
            fontSize=10,
            leading=14,
            spaceAfter=6
        )
        
        # PDF 콘텐츠 생성
        story = []
        
        # 제목 추가
        story.append(Paragraph(f"기업 분석 보고서: {company_name}", title_style))
        story.append(Spacer(1, 6*mm))
        
        # 질문 추가
        story.append(Paragraph("분석 질문", heading2_style))
        story.append(Paragraph(user_query, body_style))
        story.append(Spacer(1, 6*mm))
        
        # 생성 시간 추가
        story.append(Paragraph(f"생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", body_style))
        story.append(Spacer(1, 10*mm))
        
        # Markdown 텍스트 파싱 및 추가
        lines = markdown_text.split('\n')
        
        for line in lines:
            line = line.strip()
            
            if not line:
                story.append(Spacer(1, 3*mm))
                continue
            
            # 제목 처리 (### 형식)
            if line.startswith('### '):
                text = line.replace('### ', '').strip()
                # XML 특수 문자 이스케이프
                text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                story.append(Paragraph(text, heading3_style))
            
            # 제목 처리 (## 형식)
            elif line.startswith('## '):
                text = line.replace('## ', '').strip()
                text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                story.append(Paragraph(text, heading2_style))
            
            # 제목 처리 (# 형식)
            elif line.startswith('# '):
                text = line.replace('# ', '').strip()
                text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                story.append(Paragraph(text, heading2_style))
            
            # 리스트 항목 처리
            elif line.startswith('- ') or line.startswith('* '):
                text = '• ' + line[2:].strip()
                text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                story.append(Paragraph(text, body_style))
            
            # 일반 텍스트
            else:
                # XML 특수 문자 이스케이프
                text = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                # **굵게** 처리
                text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
                # 링크 제거 또는 처리
                text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
                
                story.append(Paragraph(text, body_style))
        
        # PDF 생성
        doc.build(story)
        
        return temp_pdf.name
        
    except Exception as e:
        logger.error(f"PDF 생성 오류: {e}", exc_info=True)
        raise

@app.route('/download/<session_id>/<file_type>')
def download_file(session_id, file_type):
    """보고서 파일 다운로드"""
    logger.info(f"파일 다운로드 요청 - 세션: {session_id}, 타입: {file_type}")
    
    result = analysis_results.get(session_id)
    if not result:
        return jsonify({
            'success': False,
            'error': '다운로드할 파일을 찾을 수 없습니다.'
        }), 404
    
    try:
        # PDF 다운로드
        if file_type == 'pdf':
            if not result.get('analysis'):
                return jsonify({'error': '분석 결과가 없습니다.'}), 404
            
            company_name = result.get('company_name', 'Unknown')
            user_query = result.get('user_query', '')
            markdown_text = result['analysis']
            
            # PDF 생성
            pdf_path = markdown_to_pdf(markdown_text, company_name, user_query)
            
            # 파일명 생성
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            download_name = f"{company_name}_분석보고서_{timestamp}.pdf"
            
            # PDF 전송 후 삭제
            response = send_file(pdf_path, as_attachment=True, download_name=download_name)
            
            # 임시 파일 삭제 (응답 후)
            @response.call_on_close
            def cleanup():
                try:
                    if os.path.exists(pdf_path):
                        os.remove(pdf_path)
                except Exception as e:
                    logger.error(f"임시 PDF 파일 삭제 오류: {e}")
            
            return response
        
        # 기존 ZIP/XML 다운로드
        files = result.get('downloaded_files')
        if not files:
            return jsonify({
                'success': False,
                'error': '다운로드할 파일을 찾을 수 없습니다.'
            }), 404
        
        if file_type == 'zip':
            file_path = files.get('zip_path')
            download_name = f"{files['report_name']}.zip"
        elif file_type == 'xml':
            file_path = files.get('xml_path')
            download_name = f"{files['report_name']}.xml"
        else:
            return jsonify({'error': '잘못된 파일 타입'}), 400
        
        if not file_path or not os.path.exists(file_path):
            return jsonify({'error': '파일을 찾을 수 없습니다.'}), 404
        
        logger.info(f"파일 전송: {file_path}")
        return send_file(file_path, as_attachment=True, download_name=download_name)
        
    except Exception as e:
        logger.error(f"파일 다운로드 오류: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health():
    """헬스 체크"""
    return jsonify({'status': 'ok'})

@app.route('/reset_vectordb', methods=['POST'])
def reset_vectordb():
    """VectorDB 초기화 API"""
    try:
        logger.info("VectorDB 초기화 요청 받음")
        
        # VectorStore의 reset_database 메서드 호출
        success = analyzer.vector_store.reset_database()
        
        if success:
            logger.info("VectorDB 초기화 성공")
            return jsonify({
                'success': True,
                'message': 'VectorDB가 성공적으로 초기화되었습니다.'
            })
        else:
            logger.error("VectorDB 초기화 실패")
            return jsonify({
                'success': False,
                'error': 'VectorDB 초기화에 실패했습니다.'
            }), 500
            
    except Exception as e:
        logger.error(f"VectorDB 초기화 오류: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'오류 발생: {str(e)}'
        }), 500

@app.route('/vectordb_stats', methods=['GET'])
def vectordb_stats():
    """VectorDB 통계 조회 API"""
    try:
        stats = analyzer.vector_store.get_stats()
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        logger.error(f"VectorDB 통계 조회 오류: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'오류 발생: {str(e)}'
        }), 500

if __name__ == '__main__':
    # templates 폴더 생성
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    # Flask reloader가 메인 프로세스에서만 메시지 출력
    if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        print(f"📍 접속 URL: http://localhost:{config.FLASK_PORT}")
        print(f"\n브라우저에서 http://localhost:{config.FLASK_PORT} 으로 접속하세요.\n")
        print("종료하려면 Ctrl+C 를 누르세요.\n")
    
    # Flask 앱 실행 (config에서 설정 가져오기)
    app.run(debug=config.FLASK_DEBUG, host=config.FLASK_HOST, port=config.FLASK_PORT)

