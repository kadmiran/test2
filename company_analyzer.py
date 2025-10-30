#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
회사 보고서 분석기
오픈다트 API로 보고서를 다운로드하고 Gemini API로 분석합니다.
"""

import requests
import zipfile
import xml.etree.ElementTree as ET
import os
import re
from datetime import datetime, timedelta
import fitz  # PyMuPDF for PDF processing
from vector_store import VectorStore
from naver_finance import NaverFinanceCrawler
from config import config
import shutil
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote
import time
import logging
from prompt_manager import get_prompt_manager

# Logger 설정
logger = logging.getLogger(__name__)

class CompanyAnalyzer:
    """회사 보고서 분석 클래스"""
    
    def __init__(self, dart_api_key, llm_orchestrator):
        """
        초기화
        
        Args:
            dart_api_key: 오픈다트 API 키
            llm_orchestrator: LLMOrchestrator 인스턴스 (Dependency Injection)
        """
        self.dart_api_key = dart_api_key
        self.llm_orchestrator = llm_orchestrator
        self.base_url = config.DART_BASE_URL
        
        # Prompt Manager
        self.prompt_manager = get_prompt_manager()
        
        # VectorStore는 lazy initialization (필요할 때 생성)
        self._vector_store = None
        
        # 네이버 금융 크롤러 (lazy initialization)
        self._naver_crawler = None
        
        # 상태 업데이트 콜백 (다이어그램 업데이트용)
        self.status_callback = None
    
    @property
    def vector_store(self):
        """VectorStore lazy initialization - 처음 접근할 때만 생성"""
        if self._vector_store is None:
            self._vector_store = VectorStore()
        return self._vector_store
    
    @property
    def naver_crawler(self):
        """NaverFinanceCrawler lazy initialization - 처음 접근할 때만 생성"""
        if self._naver_crawler is None:
            self._naver_crawler = NaverFinanceCrawler(llm_orchestrator=self.llm_orchestrator)
        return self._naver_crawler
        
    def _get_company_name_variations(self, company_name):
        """
        Gemini를 사용하여 회사명의 다양한 표기 가져오기
        
        Args:
            company_name: 입력된 회사명
            
        Returns:
            list: 가능한 회사명 표기 리스트
        """
        try:
            prompt = self.prompt_manager.get_prompt('name_variation', company_name=company_name)
            
            # Full prompt 로그 출력
            logger.info("=" * 60)
            logger.info("📝 FULL PROMPT (Name Variation)")
            logger.info("=" * 60)
            logger.info(prompt)
            logger.info("=" * 60)
            
            variations_text = self.llm_orchestrator.generate(
                prompt=prompt,
                task_type='name_variation'
            ).strip()
            
            # 쉼표로 분리하여 리스트 생성
            variations = [v.strip() for v in variations_text.split(',')]
            
            # 원래 입력값도 포함
            if company_name not in variations:
                variations.insert(0, company_name)
            
            # 사용된 LLM 표시
            used_llm = self.llm_orchestrator.select_provider('name_variation').get_name().upper()
            logger.info(f"   ✅ {used_llm} 추천 검색어: {variations}")
            return variations
            
        except Exception as e:
            logger.warning(f"   ⚠️  LLM 검색어 추천 실패: {e}")
            # 기본 변형만 반환
            return [company_name]
    
    def get_corp_code(self, company_name):
        """
        회사명으로 고유번호 조회
        
        Args:
            company_name: 회사명
            
        Returns:
            tuple: (corp_code, corp_name, stock_code)
        """
        logger.info(f"🔍 '{company_name}' 회사 고유번호 조회 중...")
        
        # 1. LLM으로 회사명 변형 가져오기 (항상 실행)
        logger.info(f"🤖 LLM에게 '{company_name}'의 다양한 표기 확인 요청 중...")
        search_variations = self._get_company_name_variations(company_name)
        
        try:
            # 기업 고유번호 파일 다운로드
            corp_code_url = f'{self.base_url}/corpCode.xml?crtfc_key={self.dart_api_key}'
            response = requests.get(corp_code_url, timeout=30)
            response.raise_for_status()
            
            # ZIP 파일 저장 및 압축 해제
            with open('corp_code.zip', 'wb') as f:
                f.write(response.content)
            
            with zipfile.ZipFile('corp_code.zip', 'r') as zip_ref:
                zip_ref.extractall()
            
            # XML 파일 파싱
            tree = ET.parse('CORPCODE.xml')
            root = tree.getroot()
            
            # 회사 검색 - LLM 추천 검색어로 다단계 검색
            
            logger.info(f"🔍 검색 시작: 총 {len(search_variations)}개 표기로 검색")
            exact_matches = []
            
            # 모든 변형에 대해 정확히 일치하는 회사 검색 (모든 동명 회사 수집)
            for variation in search_variations:
                logger.info(f"   📌 검색어: '{variation}'")
                
                found_count = 0
                for child in root:
                    corp_name_elem = child.find('corp_name')
                    corp_code_elem = child.find('corp_code')
                    stock_code_elem = child.find('stock_code')
                    
                    if corp_name_elem is not None and corp_code_elem is not None:
                        name = corp_name_elem.text
                        code = corp_code_elem.text
                        stock = stock_code_elem.text if stock_code_elem is not None and stock_code_elem.text else ''
                        
                        # 정확히 일치 (대소문자 무시)
                        if name.upper() == variation.upper():
                            # 중복 방지
                            if not any(c[0] == code for c in exact_matches):
                                exact_matches.append((code, name, stock))
                                stock_display = stock if stock else '없음'
                                logger.info(f"      ✅ 발견: {name} (고유번호: {code}, 종목: {stock_display})")
                                found_count += 1
                
                # 이 검색어로 찾았으면 다음 검색어는 시도 안 함
                if found_count > 0:
                    break
            
            # 정확히 일치하는 회사가 있으면 바로 반환
            if exact_matches:
                logger.info(f"\n   ✅ 총 {len(exact_matches)}개의 동명 회사 발견")
                
                # 종목코드가 있는 것만 필터링
                with_stock = [c for c in exact_matches if c[2] and c[2].strip()]
                
                if with_stock:
                    # 종목코드가 있는 것 중 첫 번째
                    result = with_stock[0]
                    logger.info(f"최종 선택 (종목코드 있음): {result[1]} (고유번호: {result[0]}, 종목: {result[2]})")
                else:
                    # 종목코드가 없어도 첫 번째 선택
                    result = exact_matches[0]
                    logger.info(f"최종 선택 (종목코드 없음): {result[1]} (고유번호: {result[0]})")
                
                # 임시 파일 정리
                for file in ['corp_code.zip', 'CORPCODE.xml']:
                    if os.path.exists(file):
                        os.remove(file)
                
                return result
            
            # 2단계: 정확히 일치하는 것이 없으면 포함되는 경우 검색
            logger.info("2단계: 변형 검색어를 포함하는 회사 검색 중...")
            contains_matches = []
            
            # 모든 변형에 대해 포함 검색
            for variation in search_variations:
                for child in root:
                    corp_name_elem = child.find('corp_name')
                    corp_code_elem = child.find('corp_code')
                    stock_code_elem = child.find('stock_code')
                    
                    if corp_name_elem is not None and corp_code_elem is not None:
                        name = corp_name_elem.text
                        code = corp_code_elem.text
                        stock = stock_code_elem.text if stock_code_elem is not None else ''
                        
                        # 검색어가 포함된 경우
                        if variation.upper() in name.upper():
                            # 중복 방지
                            if not any(c[0] == code for c in contains_matches):
                                contains_matches.append((code, name, stock))
            
            # 임시 파일 정리
            for file in ['corp_code.zip', 'CORPCODE.xml']:
                if os.path.exists(file):
                    os.remove(file)
            
            if contains_matches:
                logger.warning(f"정확히 일치하는 '{company_name}'는 없습니다.")
                logger.info(f"유사한 회사 {len(contains_matches)}개 발견")
                
                # 종목코드가 있는 것 우선
                with_stock = [c for c in contains_matches if c[2] and c[2].strip()]
                if with_stock:
                    result = with_stock[0]
                else:
                    result = contains_matches[0]
                
                logger.info(f"첫 번째 후보 선택: {result[1]}")
                return result
            else:
                logger.error(f"'{company_name}' 회사를 찾을 수 없습니다.")
                return None
                
        except Exception as e:
            logger.error(f"회사 검색 오류: {e}")
            return None
    
    def _extract_time_range(self, user_query):
        """
        Gemini를 사용하여 사용자 질문에서 시간 범위 추출
        
        Args:
            user_query: 사용자 질문
            
        Returns:
            int: 검색할 연수 (기본값: 3년)
        """
        try:
            logger.info("Gemini에게 시간 범위 분석 요청 중...")
            
            prompt = self.prompt_manager.get_prompt('time_range_extraction', user_query=user_query)
            
            # Full prompt 로그 출력
            logger.info("=" * 60)
            logger.info("📝 FULL PROMPT (Time Range Extraction)")
            logger.info("=" * 60)
            logger.info(prompt)
            logger.info("=" * 60)
            
            response_text = self.llm_orchestrator.generate(
                prompt=prompt,
                task_type='query_analysis'
            ).strip()
            
            # JSON 파싱
            import json
            import re
            
            # JSON 부분만 추출
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                json_text = json_match.group(0)
                result = json.loads(json_text)
                
                years = result.get('years', 3)
                reason = result.get('reason', '')
                
                # 최대 10년으로 제한
                years = min(years, 10)
                years = max(years, 1)  # 최소 1년
                
                logger.info(f"추출된 기간: {years}년 - {reason}")
                
                return years
            else:
                logger.warning(f"JSON 파싱 실패, 기본값 3년 사용 - 응답: {response_text[:200]}")
                return 3
                
        except Exception as e:
            logger.warning(f"시간 범위 추출 실패: {e}")
            return 3  # 기본값
    
    def _recommend_report_types(self, user_query, years=3):
        """
        Gemini를 사용하여 사용자 질문에 적합한 보고서 타입 추천
        
        Args:
            user_query: 사용자 질문
            years: 검색 연수 (장기 추세 분석 시 참고)
            
        Returns:
            list: 추천된 보고서 타입 리스트
        """
        try:
            logger.info("Gemini에게 적절한 보고서 타입 추천 요청 중...")
            
            prompt = self.prompt_manager.get_prompt('report_type_recommendation', user_query=user_query)
            
            # Full prompt 로그 출력
            logger.info("=" * 60)
            logger.info("📝 FULL PROMPT (Report Type Recommendation)")
            logger.info("=" * 60)
            logger.info(prompt)
            logger.info("=" * 60)
            
            response_text = self.llm_orchestrator.generate(
                prompt=prompt,
                task_type='query_analysis'
            ).strip()
            
            # JSON 파싱
            import json
            import re
            
            # JSON 부분만 추출 (```json ... ``` 형식 처리)
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                json_text = json_match.group(0)
                recommendation = json.loads(json_text)
                
                recommended_types = recommendation.get('recommended_types', [])
                reason = recommendation.get('reason', '')
                need_historical = recommendation.get('need_historical_reports', False)
                
                # 추천 타입이 비어있으면 기본값 사용
                if not recommended_types:
                    logger.warning("추천된 타입이 없음, 기본 보고서 타입 사용")
                    recommended_types = ['사업보고서', '반기보고서']
                
                logger.info(f"추천된 보고서 타입: {recommended_types} - {reason}")
                if need_historical:
                    logger.info("여러 해의 보고서 필요")
                
                # 튜플로 반환 (타입 리스트, 연도별 보고서 필요 여부)
                return recommended_types, need_historical
            else:
                logger.warning(f"JSON 파싱 실패, 기본 보고서 타입 사용 - 응답: {response_text[:200]}")
                return ['사업보고서', '반기보고서'], False
                
        except Exception as e:
            logger.warning(f"보고서 타입 추천 실패: {e}")
            # 기본값 반환
            return ['사업보고서', '반기보고서'], False
    
    def get_reports(self, corp_code, report_types=None, user_query=None, years=None):
        """
        특정 회사의 보고서 목록 조회
        
        Args:
            corp_code: 회사 고유번호
            report_types: 조회할 보고서 유형 리스트 (None이면 user_query 기반 자동 추천)
            user_query: 사용자 질문 (report_types가 None일 때 사용)
            years: 검색할 연수 (None이면 user_query에서 자동 추출)
            
        Returns:
            list: 보고서 목록
        """
        # 보고서 타입이 지정되지 않았으면 Gemini에게 추천받기
        if report_types is None and user_query:
            logger.info("사용자 질문 기반 보고서 타입 자동 선택 중...")
            report_types, _ = self._recommend_report_types(user_query, years if years else 3)
        
        # report_types가 여전히 None이거나 비어있으면 기본값 사용
        if not report_types:
            logger.info("기본 보고서 타입 사용: 사업보고서, 반기보고서")
            report_types = ['사업보고서', '반기보고서']
        
        # 시간 범위가 지정되지 않았으면 user_query에서 추출
        if years is None and user_query:
            years = self._extract_time_range(user_query)
        elif years is None:
            years = 3  # 기본값
        
        logger.info(f"보고서 검색 중... (타입: {', '.join(report_types)}, 기간: 최근 {years}년)")
        
        try:
            # 지정된 기간 검색
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=years*365)).strftime('%Y%m%d')
            
            logger.info(f"검색 기간: {start_date} ~ {end_date}, 회사 고유번호: {corp_code}")
            
            # 페이지네이션으로 모든 보고서 검색
            all_reports = []
            page_no = 1
            max_pages = 10  # 최대 10페이지까지 검색 (1000개 보고서)
            
            while page_no <= max_pages:
                logger.info(f"페이지 {page_no} 검색 중...")
                
                params = {
                    'crtfc_key': self.dart_api_key,
                    'corp_code': corp_code,
                    'bgn_de': start_date,
                    'end_de': end_date,
                    'page_no': page_no,
                    'page_count': 100
                }
                
                if page_no == 1:
                    logger.info(f"📤 DART API 요청 정보:")
                    logger.info(f"   - URL: {self.base_url}/list.json")
                    logger.info(f"   - 요청 파라미터: {params}")
                    logger.info(f"   - 회사 고유번호: {corp_code}")
                    logger.info(f"   - 검색 기간: {start_date} ~ {end_date}")
                    logger.info(f"   - 보고서 타입: {report_types}")
                
                response = requests.get(f'{self.base_url}/list.json', params=params, timeout=30)
                logger.info(f"📡 DART API 응답 코드: {response.status_code}")
                
                response.raise_for_status()
                
                data = response.json()
                logger.info(f"📋 DART API 응답 상세:")
                logger.info(f"   - 상태: {data.get('status')}")
                logger.info(f"   - 메시지: {data.get('message', 'N/A')}")
                logger.info(f"   - 전체 응답 크기: {len(str(data))}자")
                
                # 응답 데이터의 주요 필드들 로그 출력
                if 'list' in data:
                    logger.info(f"   - 보고서 목록 개수: {len(data.get('list', []))}개")
                    if data.get('list'):
                        sample_report = data['list'][0]
                        logger.info(f"   - 보고서 샘플 필드: {list(sample_report.keys())}")
                        logger.info(f"   - 첫 번째 보고서: {sample_report.get('report_nm', 'N/A')} ({sample_report.get('rcept_dt', 'N/A')})")
                
                # 전체 응답 데이터 출력 (디버깅용)
                logger.info(f"📄 DART API 전체 응답 데이터:")
                logger.info(f"{data}")
                
                if data.get('status') == '000':
                    page_reports = data.get('list', [])
                    logger.debug(f"페이지 {page_no} 보고서 수: {len(page_reports)}개")
                    
                    if not page_reports:
                        logger.info(f"페이지 {page_no}에 보고서가 없습니다. 검색 종료.")
                        break
                    
                    all_reports.extend(page_reports)
                    
                    # 원하는 보고서 유형이 있는지 확인
                    found_target = False
                    for report in page_reports:
                        report_name = report.get('report_nm', '')
                        for report_type in report_types:
                            if report_type in report_name:
                                found_target = True
                                break
                        if found_target:
                            break
                    
                    if found_target:
                        logger.info(f"페이지 {page_no}에서 원하는 보고서 타입 발견! 검색 종료.")
                        break
                    
                    page_no += 1
                else:
                    logger.error(f"❌ 페이지 {page_no} 조회 실패:")
                    logger.error(f"   - 상태 코드: {data.get('status')}")
                    logger.error(f"   - 오류 메시지: {data.get('message', 'N/A')}")
                    logger.error(f"   - 전체 응답: {data}")
                    break
            
            logger.info(f"전체 수집된 보고서 수: {len(all_reports)}개")
            
            if not all_reports:
                logger.warning("전체 보고서가 0개입니다!")
                return []
            
            # 원하는 보고서 유형만 필터링
            filtered_reports = []
            logger.info(f"🔍 보고서 필터링 시작:")
            logger.info(f"   - 전체 보고서 수: {len(all_reports)}개")
            logger.info(f"   - 찾는 타입: {report_types}")
            
            match_count = 0
            for i, report in enumerate(all_reports):
                report_name = report.get('report_nm', '')
                report_date = report.get('rcept_dt', '')
                logger.info(f"   [{i+1}/{len(all_reports)}] 검사 중: '{report_name}' ({report_date})")
                
                matched = False
                for report_type in report_types:
                    if report_type in report_name:
                        filtered_reports.append(report)
                        match_count += 1
                        logger.info(f"      ✅ 매치! '{report_type}' 포함됨 → 필터링됨")
                        matched = True
                        break
                
                if not matched:
                    logger.info(f"      ❌ 매치 안됨")
            
            logger.info(f"🎯 필터링 결과: {match_count}개 매치됨")
            
            logger.info(f"총 {len(filtered_reports)}개의 보고서를 찾았습니다.")
            if not filtered_reports:
                logger.warning("필터링 결과 0개! 원하는 보고서 타입이 없습니다.")
            return filtered_reports
                
        except Exception as e:
            logger.error(f"❌ DART 보고서 검색 오류:")
            logger.error(f"   - 오류 타입: {type(e).__name__}")
            logger.error(f"   - 오류 메시지: {str(e)}")
            logger.error(f"   - 검색 파라미터: corp_code={corp_code}, years={years}")
            logger.error(f"   - 보고서 타입: {report_types}")
            import traceback
            logger.error(f"   - 상세 스택 트레이스:\n{traceback.format_exc()}")
            return []
    
    def download_report(self, rcept_no, save_path=None, company_name=None, report_name=None, report_date=None):
        """
        보고서 다운로드 및 내용 추출 (벡터DB 캐시 우선)
        
        Args:
            rcept_no: 접수번호
            save_path: 저장 경로 (지정하면 파일로 저장)
            company_name: 회사명 (벡터DB 저장용)
            report_name: 보고서명 (벡터DB 저장용)
            report_date: 보고서 날짜 (벡터DB 저장용)
            
        Returns:
            tuple: (text_content, saved_file_path, extracted_path)
        """
        logger.info(f"보고서 조회 중... (접수번호: {rcept_no})")
        
        # 1. 벡터DB에서 먼저 확인
        logger.info("VectorDB 캐시 확인 중...")
        if self.vector_store.check_report_exists(rcept_no):
            cached_content = self.vector_store.get_report_from_cache(rcept_no)
            if cached_content:
                logger.info(f"VectorDB 캐시 사용 (API 호출 생략) - 캐시된 내용: {len(cached_content):,}자")
                # 캐시된 내용 반환 (파일 경로는 None)
                return cached_content, None, None
        
        # 2. 벡터DB에 없으면 API로 다운로드
        logger.info("VectorDB에 없음 → DART API에서 다운로드")
        
        # 상태 업데이트 콜백이 있으면 DART 시작 로그 전송
        if hasattr(self, 'status_callback') and self.status_callback:
            self.status_callback(f"🔵 DART 시작: 보고서 다운로드")
        
        try:
            # 보고서 다운로드
            params = {
                'crtfc_key': self.dart_api_key,
                'rcept_no': rcept_no
            }
            
            response = requests.get(f'{self.base_url}/document.xml', params=params, timeout=60)
            response.raise_for_status()
            
            # 저장 디렉토리 생성
            if not os.path.exists('downloads'):
                os.makedirs('downloads')
            
            # 파일 저장
            if not save_path:
                save_path = f'downloads/{rcept_no}.zip'
            
            with open(save_path, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"보고서 저장: {save_path} ({len(response.content):,} bytes)")
            
            # ZIP 파일인지 확인하고 압축 해제
            content = ""
            extracted_path = None
            
            if zipfile.is_zipfile(save_path):
                # ZIP 압축 해제
                extract_dir = save_path.replace('.zip', '_extracted')
                os.makedirs(extract_dir, exist_ok=True)
                
                with zipfile.ZipFile(save_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
                    file_list = zip_ref.namelist()
                    
                    if file_list:
                        extracted_path = os.path.join(extract_dir, file_list[0])
                        # 첫 번째 XML 파일 읽기
                        with zip_ref.open(file_list[0]) as xml_file:
                            content = xml_file.read().decode('utf-8', errors='ignore')
                        
                        logger.info(f"압축 해제: {extract_dir}")
            else:
                # 직접 XML 읽기
                with open(save_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                extracted_path = save_path
            
            # XML에서 텍스트 추출 및 Markdown 변환
            logger.info(f"XML → Markdown 변환 시작 (원본: {len(content):,}자)")
            text_content = self._extract_text_from_xml(content)
            
            logger.info(f"보고서 변환 완료 (Markdown: {len(text_content):,}자)")
            
            # 상태 업데이트 콜백이 있으면 DART 완료 로그 전송
            if hasattr(self, 'status_callback') and self.status_callback:
                self.status_callback(f"⚪ DART 완료: 보고서 다운로드")
            
            # 3. VectorDB에 저장
            if text_content and company_name and report_name and report_date:
                logger.info("VectorDB에 보고서 저장 중...")
                try:
                    self.vector_store.add_report(
                        rcept_no=rcept_no,
                        report_name=report_name,
                        company_name=company_name,
                        report_date=report_date,
                        content=text_content
                    )
                    logger.info("VectorDB 저장 완료")
                except Exception as ve:
                    logger.warning(f"VectorDB 저장 실패 (계속 진행): {ve}")
            
            return text_content, save_path, extracted_path
            
        except Exception as e:
            logger.error(f"다운로드 오류: {e}")
            return "", None, None
    
    def _extract_text_from_xml(self, xml_content):
        """
        XML 파일에서 모든 텍스트 추출 (XML 태그만 제거, 모든 내용 보존)
        
        Args:
            xml_content: XML 내용
            
        Returns:
            str: 순수 텍스트 (서식 없음, XML 태그만 제거)
        """
        try:
            from bs4 import BeautifulSoup
            
            original_size = len(xml_content)
            logger.debug(f"원본 XML 크기: {original_size:,}자 ({original_size/1024:.1f}KB)")
            
            # BeautifulSoup으로 파싱
            logger.debug("XML 파싱 중 (BeautifulSoup)...")
            try:
                soup = BeautifulSoup(xml_content, 'xml')
                logger.debug("XML 파싱 성공")
            except:
                logger.debug("XML 파서 실패, lxml 시도...")
                try:
                    soup = BeautifulSoup(xml_content, 'lxml')
                    logger.debug("lxml 파싱 성공")
                except:
                    logger.warning("모든 파서 실패, 정규식으로 전환")
                    return self._simple_text_extraction(xml_content)
            
            # 모든 텍스트 추출 (태그 제거, 내용 보존, 제한 없음)
            logger.debug("모든 텍스트 추출 중... (제한 없음)")
            extracted_text = soup.get_text(separator='\n', strip=False)
            
            # 정리
            logger.debug("텍스트 정리 중...")
            
            # 1. 연속된 공백을 단일 공백으로 (줄바꿈은 보존)
            extracted_text = re.sub(r'[ \t]+', ' ', extracted_text)
            
            # 2. 3개 이상의 연속 줄바꿈을 2개로
            extracted_text = re.sub(r'\n{3,}', '\n\n', extracted_text)
            
            # 3. 각 줄의 앞뒤 공백 제거
            lines = extracted_text.split('\n')
            lines = [line.strip() for line in lines if line.strip()]  # 빈 줄 제거
            extracted_text = '\n'.join(lines)
            
            # 4. 전체 앞뒤 공백 제거
            extracted_text = extracted_text.strip()
            
            extracted_size = len(extracted_text)
            
            logger.info(f"XML → 텍스트 추출 완료! 원본: {original_size:,}자 → 추출: {extracted_size:,}자 (보존율: {(extracted_size/original_size*100):.1f}%)")
            
            if not extracted_text or len(extracted_text) < 1000:
                logger.warning(f"추출 결과가 너무 적음 ({len(extracted_text)}자), 정규식으로 재시도")
                return self._simple_text_extraction(xml_content)
            
            return extracted_text
            
        except Exception as e:
            logger.warning(f"XML 파싱 실패, 정규식으로 전환: {e}")
            return self._simple_text_extraction(xml_content)
    
    def _parse_table_to_markdown(self, table_element):
        """테이블을 Markdown 형식으로 변환"""
        try:
            rows = []
            
            # TR 태그 찾기
            for tr in table_element.iter():
                if 'TR' in tr.tag.upper():
                    cells = []
                    for td in tr:
                        if 'TD' in td.tag.upper() or 'TH' in td.tag.upper() or 'TU' in td.tag.upper():
                            cell_text = td.text.strip() if td.text else ''
                            cells.append(cell_text)
                    
                    if cells:
                        rows.append(cells)
            
            if not rows:
                return ""
            
            # Markdown 테이블 생성
            md_table = []
            
            # 첫 번째 행을 헤더로
            if rows:
                header = ' | '.join(rows[0])
                md_table.append(f"| {header} |")
                md_table.append('|' + ' --- |' * len(rows[0]))
                
                # 나머지 행
                for row in rows[1:6]:  # 최대 5개 행만
                    row_text = ' | '.join(row)
                    md_table.append(f"| {row_text} |")
            
            return '\n'.join(md_table) + '\n\n'
            
        except:
            return ""
    
    def _simple_text_extraction(self, xml_content):
        """
        단순 텍스트 추출 (백업용) - 정규표현식으로 XML 태그만 제거
        모든 내용을 보존하고 XML 태그만 제거
        """
        logger.debug("단순 텍스트 추출 모드 (정규식)")
        
        # 1. XML 태그 제거 (내용은 보존)
        # <tag>content</tag> → content
        text = re.sub(r'<[^>]+>', '\n', xml_content)
        
        # 2. XML 선언, DOCTYPE 등 제거
        text = re.sub(r'<\?xml[^>]*\?>', '', text)
        text = re.sub(r'<!DOCTYPE[^>]*>', '', text)
        
        # 3. 연속된 공백을 단일 공백으로 (단, 줄바꿈은 보존)
        text = re.sub(r'[ \t]+', ' ', text)
        
        # 4. 3개 이상의 연속 줄바꿈을 2개로
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # 5. 각 줄의 앞뒤 공백 제거
        lines = text.split('\n')
        lines = [line.strip() for line in lines]
        text = '\n'.join(lines)
        
        # 6. 빈 줄 연속 제거
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # 7. 전체 앞뒤 공백 제거
        text = text.strip()
        
        logger.debug(f"추출 결과: {len(text):,}자 ({len(text)/1024:.1f}KB)")
        
        return text
    
    def cleanup_downloads(self, keep_latest=0):
        """
        downloads 폴더의 파일들을 정리
        벡터DB에 저장된 보고서는 삭제해도 안전함
        
        Args:
            keep_latest: 최신 파일 몇 개를 남길지 (0이면 모두 삭제)
        """
        downloads_dir = 'downloads'
        
        if not os.path.exists(downloads_dir):
            logger.info(f"'{downloads_dir}' 폴더가 없습니다.")
            return
        
        logger.info(f"다운로드 파일 정리 시작... 경로: {downloads_dir}")
        
        try:
            # 모든 파일 및 폴더 목록 가져오기
            items = []
            for item in os.listdir(downloads_dir):
                item_path = os.path.join(downloads_dir, item)
                if os.path.isfile(item_path) or os.path.isdir(item_path):
                    # 수정 시간 가져오기
                    mtime = os.path.getmtime(item_path)
                    items.append((item_path, mtime))
            
            # 수정 시간 기준으로 정렬 (최신순)
            items.sort(key=lambda x: x[1], reverse=True)
            
            logger.info(f"총 {len(items)}개 항목 발견")
            
            # 삭제할 항목 결정
            items_to_delete = items[keep_latest:] if keep_latest > 0 else items
            items_to_keep = items[:keep_latest] if keep_latest > 0 else []
            
            if items_to_keep:
                print(f"   🔒 최신 {len(items_to_keep)}개 항목 유지:")
                for path, _ in items_to_keep[:5]:  # 처음 5개만 출력
                    print(f"      - {os.path.basename(path)}")
            
            if items_to_delete:
                print(f"   🗑️  {len(items_to_delete)}개 항목 삭제 중...")
                
                deleted_count = 0
                freed_size = 0
                
                for item_path, _ in items_to_delete:
                    try:
                        # 크기 계산
                        if os.path.isfile(item_path):
                            size = os.path.getsize(item_path)
                            os.remove(item_path)
                            deleted_count += 1
                            freed_size += size
                        elif os.path.isdir(item_path):
                            size = sum(
                                os.path.getsize(os.path.join(dirpath, filename))
                                for dirpath, dirnames, filenames in os.walk(item_path)
                                for filename in filenames
                            )
                            shutil.rmtree(item_path)
                            deleted_count += 1
                            freed_size += size
                    except Exception as e:
                        print(f"      ⚠️  삭제 실패: {os.path.basename(item_path)} - {e}")
                
                print(f"   ✅ 정리 완료: {deleted_count}개 항목 삭제")
                print(f"   💾 확보된 공간: {freed_size / 1024 / 1024:.2f} MB")
            else:
                print(f"   ℹ️  삭제할 항목이 없습니다.")
            
        except Exception as e:
            print(f"❌ 파일 정리 중 오류: {e}")
            import traceback
            traceback.print_exc()
    
    def extract_text_from_pdf(self, pdf_path):
        """
        PDF 파일에서 텍스트 추출
        
        Args:
            pdf_path: PDF 파일 경로
            
        Returns:
            str: 추출된 텍스트
        """
        try:
            print(f"📄 PDF 텍스트 추출 중: {pdf_path}")
            text = ""
            
            with fitz.open(pdf_path) as doc:
                total_pages = len(doc)
                print(f"   📖 총 {total_pages}페이지")
                
                for page_num, page in enumerate(doc, 1):
                    page_text = page.get_text()
                    text += f"\n--- 페이지 {page_num} ---\n{page_text}"
                    
                    if page_num % 10 == 0:
                        print(f"   ✓ {page_num}/{total_pages} 페이지 처리 완료")
                
                print(f"✅ PDF 텍스트 추출 완료: {len(text):,}자")
                return text
                
        except Exception as e:
            print(f"❌ PDF 텍스트 추출 실패: {e}")
            return ""
    
    def get_company_industry(self, corp_code, company_name):
        """
        DART API로 기업의 산업군 파악
        
        Args:
            corp_code: 회사 고유번호
            company_name: 회사명
            
        Returns:
            str: 산업군 정보
        """
        try:
            print(f"🏢 {company_name}의 산업군 파악 중...")
            
            # DART 기업개황 API 호출
            params = {
                'crtfc_key': self.dart_api_key,
                'corp_code': corp_code
            }
            
            response = requests.get(f'{self.base_url}/company.json', params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status') == '000':
                industry = data.get('induty_code', '')
                
                if industry:
                    print(f"   ✅ 산업군: {industry}")
                    return industry
                else:
                    print(f"   ⚠️  산업군 정보를 찾을 수 없습니다. Gemini로 추론합니다.")
                    # Gemini로 산업군 추론
                    return self._infer_industry_with_gemini(company_name)
            else:
                print(f"   ⚠️  API 호출 실패, Gemini로 추론합니다.")
                return self._infer_industry_with_gemini(company_name)
                
        except Exception as e:
            print(f"   ⚠️  산업군 조회 실패: {e}, Gemini로 추론합니다.")
            return self._infer_industry_with_gemini(company_name)
    
    def _infer_industry_with_gemini(self, company_name):
        """
        Gemini로 기업의 산업군 추론
        
        Args:
            company_name: 회사명
            
        Returns:
            str: 추론된 산업군
        """
        try:
            prompt = self.prompt_manager.get_prompt('industry_inference', company_name=company_name)
            
            # Full prompt 로그 출력
            logger.info("=" * 60)
            logger.info("📝 FULL PROMPT (Industry Inference)")
            logger.info("=" * 60)
            logger.info(prompt)
            logger.info("=" * 60)
            
            industry = self.llm_orchestrator.generate(
                prompt=prompt,
                task_type='query_analysis'
            ).strip()
            print(f"   🤖 Gemini 추론 산업군: {industry}")
            return industry
            
        except Exception as e:
            print(f"   ⚠️  Gemini 산업군 추론 실패: {e}")
            return "일반"
    
    def _extract_industry_keywords(self, user_query, company_name, base_industry):
        """
        Gemini로 사용자 질문에서 산업분석 키워드 추출
        
        Args:
            user_query: 사용자 질문
            company_name: 회사명
            base_industry: 기본 산업군
            
        Returns:
            list: 산업분석 검색 키워드 리스트
        """
        try:
            print(f"🤖 Gemini에게 산업분석 키워드 추출 요청 중...")
            
            prompt = self.prompt_manager.get_prompt(
                'industry_keywords_extraction',
                user_query=user_query,
                company_name=company_name,
                base_industry=base_industry
            )
            
            # Full prompt 로그 출력
            logger.info("=" * 60)
            logger.info("📝 FULL PROMPT (Industry Keywords Extraction)")
            logger.info("=" * 60)
            logger.info(prompt)
            logger.info("=" * 60)
            
            response_text = self.llm_orchestrator.generate(
                prompt=prompt,
                task_type='query_analysis'
            ).strip()
            
            # JSON 파싱
            import json
            import re
            
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                json_text = json_match.group(0)
                result = json.loads(json_text)
                
                keywords = result.get('keywords', [])
                reason = result.get('reason', '')
                
                print(f"   ✅ 추출된 산업 키워드: {keywords}")
                print(f"   💡 이유: {reason}")
                
                return keywords
            else:
                print(f"   ⚠️  JSON 파싱 실패, 기본 산업군 사용")
                return [base_industry.split(',')[0].strip()]
                
        except Exception as e:
            print(f"   ⚠️  산업 키워드 추출 실패: {e}")
            # 기본값으로 기본 산업군의 첫 번째 키워드 사용
            return [base_industry.split(',')[0].strip()]
    
    def get_historical_annual_reports(self, corp_code, years=5):
        """
        연도별 사업보고서 수집 (장기 추세 분석용)
        
        Args:
            corp_code: 회사 고유번호
            years: 수집할 연수
            
        Returns:
            list: 연도별 사업보고서 목록
        """
        print(f"📅 연도별 사업보고서 수집 중... ({years}년치)")
        
        try:
            # 검색 기간 설정
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=years*365)).strftime('%Y%m%d')
            
            params = {
                'crtfc_key': self.dart_api_key,
                'corp_code': corp_code,
                'bgn_de': start_date,
                'end_de': end_date,
                'page_no': 1,
                'page_count': 100
            }
            
            response = requests.get(f'{self.base_url}/list.json', params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status') == '000':
                all_reports = data.get('list', [])
                
                # 사업보고서만 필터링
                annual_reports = []
                for report in all_reports:
                    report_name = report.get('report_nm', '')
                    if '사업보고서' in report_name:
                        annual_reports.append(report)
                
                # 연도별로 그룹화 (각 연도당 1개씩만)
                reports_by_year = {}
                for report in annual_reports:
                    rcept_dt = report.get('rcept_dt', '')
                    if rcept_dt and len(rcept_dt) >= 4:
                        year = rcept_dt[:4]  # YYYYMMDD에서 YYYY 추출
                        # 해당 연도의 첫 번째 보고서만 저장 (최신순 정렬되어 있음)
                        if year not in reports_by_year:
                            reports_by_year[year] = report
                
                # 연도 역순으로 정렬 (최신 → 과거)
                sorted_reports = [reports_by_year[year] for year in sorted(reports_by_year.keys(), reverse=True)]
                
                # 최대 years개까지만 (최소 2개는 보장)
                selected_reports = sorted_reports[:max(2, years)]
                
                print(f"   ✅ {len(selected_reports)}개 연도의 사업보고서 발견")
                for report in selected_reports:
                    rcept_dt = report.get('rcept_dt', '')
                    report_nm = report.get('report_nm', '')
                    print(f"      - {rcept_dt[:4]}년: {report_nm}")
                
                return selected_reports
            else:
                print(f"   ❌ 사업보고서 조회 실패: {data.get('message')}")
                return []
                
        except Exception as e:
            print(f"   ❌ 오류: {e}")
            return []
    
    def get_analyst_reports(self, corp_code, count=5, user_query=None, years=None):
        """
        관련 보고서 조회 (사용자 질문 기반으로 적절한 보고서 선택)
        
        Args:
            corp_code: 회사 고유번호
            count: 조회할 보고서 수
            user_query: 사용자 질문 (보고서 타입 자동 선택용)
            years: 검색할 연수 (None이면 user_query에서 자동 추출)
            
        Returns:
            list: 보고서 목록
        """
        print(f"📊 추가 보고서 검색 중... (최대 {count}개)")
        
        # 시간 범위가 지정되지 않았으면 user_query에서 추출
        if years is None and user_query:
            years = self._extract_time_range(user_query)
        elif years is None:
            years = 3  # 기본값 (메인보다 넓게)
        
        # 보고서 타입 자동 선택
        need_historical = False
        if user_query:
            print(f"   💡 사용자 질문 기반으로 보고서 타입 선택")
            target_types, need_historical = self._recommend_report_types(user_query, years)
            
            # 기본 보고서들도 포함 (중복 제거)
            default_types = ['분기보고서', '반기보고서', '사업보고서', '주요사항보고서', '기타경영사항(자율공시)', '조회공시요구']
            for dtype in default_types:
                if dtype not in target_types:
                    target_types.append(dtype)
        else:
            # 기본 보고서 타입
            target_types = [
                '분기보고서',
                '반기보고서', 
                '사업보고서',
                '주요사항보고서',
                '기타경영사항(자율공시)',
                '조회공시요구',
            ]
        
        try:
            # 지정된 기간 검색
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=years*365)).strftime('%Y%m%d')
            
            print(f"   📅 검색 기간: {start_date} ~ {end_date} ({years}년)")
            
            # 장기 추세 분석이 필요한 경우 연도별 사업보고서 수집
            if need_historical:
                print(f"   📚 장기 추세 분석 감지: 연도별 사업보고서 수집")
                historical_reports = self.get_historical_annual_reports(corp_code, years)
                
                # 일반 보고서도 수집 (사업보고서 제외)
                params = {
                    'crtfc_key': self.dart_api_key,
                    'corp_code': corp_code,
                    'bgn_de': start_date,
                    'end_de': end_date,
                    'page_no': 1,
                    'page_count': 50
                }
                
                response = requests.get(f'{self.base_url}/list.json', params=params, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                
                regular_reports = []
                if data.get('status') == '000':
                    all_reports = data.get('list', [])
                    
                    # 사업보고서를 제외한 다른 타입 필터링
                    for report in all_reports:
                        report_name = report.get('report_nm', '')
                        # 사업보고서는 이미 historical_reports에 있으므로 제외
                        if '사업보고서' not in report_name:
                            for report_type in target_types:
                                if report_type in report_name:
                                    regular_reports.append(report)
                                    break
                    
                    # 최신순으로 제한
                    regular_reports = regular_reports[:max(1, count - len(historical_reports))]
                
                # 연도별 사업보고서 + 일반 보고서 합침
                selected_reports = historical_reports + regular_reports
                
                # 최대 count개로 제한
                selected_reports = selected_reports[:count]
                
                print(f"✅ 총 {len(selected_reports)}개의 보고서를 찾았습니다.")
                print(f"   - 연도별 사업보고서: {len(historical_reports)}개")
                print(f"   - 기타 보고서: {len(regular_reports)}개")
                
                for i, report in enumerate(selected_reports, 1):
                    report_name = report.get('report_nm', '')
                    rcept_dt = report.get('rcept_dt', '')
                    marker = "📅" if '사업보고서' in report_name else "📄"
                    print(f"   [{i}] {marker} {report_name} ({rcept_dt})")
                
                return selected_reports
            
            # 일반적인 경우 (장기 추세 아님)
            params = {
                'crtfc_key': self.dart_api_key,
                'corp_code': corp_code,
                'bgn_de': start_date,
                'end_de': end_date,
                'page_no': 1,
                'page_count': 100
            }
            
            response = requests.get(f'{self.base_url}/list.json', params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status') == '000':
                all_reports = data.get('list', [])
                
                # 다양한 보고서 유형 필터링
                # Gemini 추천 보고서를 우선 순위로 배치
                filtered_reports = []
                for report in all_reports:
                    report_name = report.get('report_nm', '')
                    for report_type in target_types:
                        if report_type in report_name:
                            filtered_reports.append(report)
                            break
                
                # 최신순으로 count개만 선택 (최소 2개는 보장)
                selected_reports = filtered_reports[:max(2, count)]
                
                print(f"✅ 총 {len(selected_reports)}개의 보고서를 찾았습니다.")
                for i, report in enumerate(selected_reports, 1):
                    report_name = report.get('report_nm', '')
                    rcept_dt = report.get('rcept_dt', '')
                    marker = "📄"
                    print(f"   [{i}] {marker} {report_name} ({rcept_dt})")
                
                return selected_reports
            else:
                print(f"❌ 보고서 조회 실패: {data.get('message')}")
                return []
                
        except Exception as e:
            print(f"❌ 오류: {e}")
            return []
    
    def download_multiple_reports(self, reports, max_reports=5, company_name=None):
        """
        여러 보고서 다운로드 및 내용 추출
        
        Args:
            reports: 보고서 목록
            max_reports: 최대 다운로드 수
            company_name: 회사명 (벡터DB 저장용)
            
        Returns:
            list: [(report_name, content), ...] 형식의 리스트
        """
        print(f"📥 {min(len(reports), max_reports)}개 보고서 수집 시작...")
        
        downloaded_reports = []
        
        for i, report in enumerate(reports[:max_reports], 1):
            rcept_no = report.get('rcept_no')
            report_name = report.get('report_nm')
            rcept_dt = report.get('rcept_dt')
            
            print(f"\n[{i}/{min(len(reports), max_reports)}] {report_name} ({rcept_dt})")
            
            try:
                content, zip_path, xml_path = self.download_report(
                    rcept_no=rcept_no,
                    company_name=company_name,
                    report_name=report_name,
                    report_date=rcept_dt
                )
                
                if content:
                    downloaded_reports.append({
                        'name': report_name,
                        'date': rcept_dt,
                        'content': content,
                        'rcept_no': rcept_no
                    })
                    # VectorDB에서 가져온 경우와 API 다운로드 구분
                    if zip_path is None and xml_path is None:
                        print(f"✅ VectorDB 검색 확인: {len(content):,}자")
                    else:
                        print(f"✅ 다운로드 완료: {len(content):,}자")
                else:
                    print(f"⚠️  내용 추출 실패")
                    
            except Exception as e:
                print(f"❌ 다운로드 오류: {e}")
                continue
        
        print(f"\n✅ 총 {len(downloaded_reports)}개 보고서 수집 완료")
        return downloaded_reports
    
    def analyze_with_gemini(self, company_name, report_content, user_query, additional_reports=None, exclude_opinions=False):
        """
        Gemini API로 보고서 분석
        
        Args:
            company_name: 회사명
            report_content: 메인 보고서 내용
            user_query: 사용자 질문
            additional_reports: 추가 보고서 리스트 (선택사항)
            
        Returns:
            str: 분석 결과
        """
        print(f"🤖 Gemini로 분석 중...")
        
        try:
            # Gemini 2.5 Pro는 1백만 토큰을 지원하므로 보고서 전체 사용 가능
            # 하지만 너무 크면 응답 속도가 느려질 수 있으므로 적절히 제한
            max_length_per_report = 200000  # 보고서당 최대 20만자
            
            # 메인 보고서 처리
            original_length = len(report_content)
            print(f"   📊 메인 보고서 정보:")
            print(f"      - 형식: Markdown (XML에서 변환됨)")
            print(f"      - 크기: {len(report_content):,}자")
            print(f"      - 예상 토큰: 약 {len(report_content) / 4:,.0f} 토큰")
            
            if len(report_content) > max_length_per_report:
                print(f"   ⚠️  보고서가 큽니다. {max_length_per_report:,}자로 제한합니다.")
                report_content = report_content[:max_length_per_report]
                print(f"   ✅ 보고서 크기 조정: {len(report_content):,}자")
            
            # 추가 보고서 처리
            additional_content = ""
            dart_reports = []
            naver_reports = []
            
            if additional_reports:
                print(f"\n   📚 추가 보고서 {len(additional_reports)}개 처리 중...")
                for i, report in enumerate(additional_reports, 1):
                    report_name = report.get('name', f'보고서 {i}')
                    report_date = report.get('date', '')
                    content = report.get('content', '')
                    
                    # 각 추가 보고서도 제한
                    if len(content) > max_length_per_report:
                        content = content[:max_length_per_report]
                    
                    # 보고서 출처 구분 (네이버 증권사 리포트인지 확인)
                    if report_name.startswith('[') and ']' in report_name:
                        # 네이버 증권사 리포트 형식: [증권사명] 제목
                        naver_reports.append((report_name, report_date, content))
                    else:
                        # DART 보고서
                        dart_reports.append((report_name, report_date, content))
                
                # DART 보고서 추가
                if dart_reports:
                    additional_content += "\n\n" + "="*80 + "\n"
                    additional_content += "📋 DART 공시 보고서\n"
                    additional_content += "="*80 + "\n"
                    
                    for idx, (name, date, content) in enumerate(dart_reports, 1):
                        additional_content += f"""

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[DART 보고서 {idx}: {name} ({date})]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{content}
"""
                        print(f"      ✓ [DART {idx}] {name}: {len(content):,}자")
                
                # 네이버 증권사 리포트 추가
                if naver_reports:
                    additional_content += "\n\n" + "="*80 + "\n"
                    additional_content += "📊 네이버 증권사 리포트 (시장 분석 및 전망)\n"
                    additional_content += "="*80 + "\n"
                    
                    for idx, (name, date, content) in enumerate(naver_reports, 1):
                        additional_content += f"""

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[증권사 리포트 {idx}: {name} ({date})]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{content}
"""
                        print(f"      ✓ [증권사 {idx}] {name}: {len(content):,}자")
                
                print(f"   ✅ 추가 보고서 통합 완료: 총 {len(additional_content):,}자")
                print(f"      - DART 보고서: {len(dart_reports)}개")
                print(f"      - 증권사 리포트: {len(naver_reports)}개")
            
            # 상세한 프롬프트 구성
            print(f"   📝 Gemini 프롬프트 생성 중...")
            
            # 추가 보고서 섹션 준비
            additional_section = additional_content if additional_content else ""
            
            # 의견제외 지시사항 생성
            exclude_opinions_instruction = ""
            if exclude_opinions:
                exclude_opinions_instruction = "\n6. **중요**: 증권사 리포트 내 작성자의 의견, 추천, 투자 의견, 목표주가, 등급 등을 제외하고 오직 사실(Fact) 기반 데이터만을 참조하여 분석해주세요. 의견이 포함된 부분은 명시적으로 제외하고 객관적 데이터만 활용하세요."
            
            prompt = self.prompt_manager.get_prompt(
                'full_analysis',
                company_name=company_name,
                user_query=user_query,
                main_report=report_content,
                additional_section=additional_section,
                exclude_opinions_instruction=exclude_opinions_instruction
            )
            
            # LLM Orchestrator로 분석
            total_content_length = len(report_content) + len(additional_content)
            print(f"   🚀 LLM Orchestrator 호출 중...")
            print(f"      입력: 약 {len(prompt) / 4:,.0f} 토큰")
            print(f"      총 보고서 내용: {total_content_length:,}자")
            
            # Full prompt 로그 출력
            logger.info("=" * 80)
            logger.info("📝 FULL PROMPT (Full Analysis)")
            logger.info("=" * 80)
            logger.info(prompt)
            logger.info("=" * 80)
            
            result_text = self.llm_orchestrator.generate(
                prompt=prompt,
                task_type='long_context_analysis'
            )
            
            print(f"   ✅ LLM 분석 완료!")
            print(f"      출력: {len(result_text):,}자 (약 {len(result_text) / 4:,.0f} 토큰)")
            
            return result_text
            
        except Exception as e:
            error_message = str(e)
            print(f"❌ Gemini 분석 오류: {e}")
            
            # 할당량 초과 에러 처리
            if "429" in error_message or "quota" in error_message.lower():
                return f"""
⚠️ Gemini API 무료 할당량을 초과했습니다.

**문제**: Gemini API 무료 티어의 일일 요청 한도를 초과했습니다.

**해결 방법**:
1. 24시간 후에 다시 시도하세요 (할당량이 리셋됩니다)
2. Google AI Studio에서 유료 플랜으로 업그레이드
3. API 키를 재발급하거나 다른 계정의 키 사용

**현재 상황**:
- 회사: {company_name}
- 보고서: 다운로드 완료 ({len(report_content):,}자)
- 오류: 무료 할당량 초과

자세한 정보: https://ai.google.dev/gemini-api/docs/rate-limits
"""
            else:
                return f"분석 중 오류가 발생했습니다: {error_message[:500]}"
    
    def analyze_with_gemini_rag(self, company_name, user_query, relevant_context, num_chunks, exclude_opinions=False):
        """
        RAG 방식으로 Gemini AI 분석 (VectorDB에서 검색된 관련 청크만 사용)
        
        Args:
            company_name: 회사명
            user_query: 사용자 질문
            relevant_context: VectorDB에서 검색된 관련 청크들 (결합된 문자열)
            num_chunks: 검색된 청크 개수
            
        Returns:
            str: AI 분석 결과 (Markdown)
        """
        try:
            print(f"\n🤖 Gemini AI 분석 (RAG 모드)")
            print(f"   📊 입력 데이터:")
            print(f"      - 회사명: {company_name}")
            print(f"      - 검색된 청크: {num_chunks}개")
            print(f"      - 총 텍스트: {len(relevant_context):,}자")
            print(f"      - 질문: {user_query[:100]}...")
            
            # 의견제외 지시사항 생성
            exclude_opinions_instruction = ""
            if exclude_opinions:
                exclude_opinions_instruction = "\n6. **중요**: 증권사 리포트 내 작성자의 의견, 추천, 투자 의견, 목표주가, 등급 등을 제외하고 오직 사실(Fact) 기반 데이터만을 참조하여 분석해주세요. 의견이 포함된 부분은 명시적으로 제외하고 객관적 데이터만 활용하세요."
            
            # RAG 프롬프트 생성
            prompt = self.prompt_manager.get_prompt(
                'rag_analysis',
                company_name=company_name,
                user_query=user_query,
                num_chunks=num_chunks,
                relevant_context=relevant_context,
                exclude_opinions_instruction=exclude_opinions_instruction
            )
            
            # LLM Orchestrator로 RAG 분석
            print(f"   🚀 LLM Orchestrator 호출 중... (RAG 모드)")
            print(f"      입력: 약 {len(prompt) / 4:,.0f} 토큰")
            print(f"      관련 내용: {len(relevant_context):,}자")
            
            # Full prompt 로그 출력
            logger.info("=" * 80)
            logger.info("📝 FULL PROMPT (RAG Analysis)")
            logger.info("=" * 80)
            logger.info(prompt)
            logger.info("=" * 80)
            
            result_text = self.llm_orchestrator.generate(
                prompt=prompt,
                task_type='long_context_analysis'
            )
            
            print(f"   ✅ LLM 분석 완료!")
            print(f"      출력: {len(result_text):,}자 (약 {len(result_text) / 4:,.0f} 토큰)")
            
            return result_text
            
        except Exception as e:
            error_message = str(e)
            print(f"❌ Gemini 분석 오류: {e}")
            
            # 할당량 초과 에러 처리
            if "429" in error_message or "quota" in error_message.lower():
                return f"""⚠️ Gemini API 무료 할당량을 초과했습니다.

**문제**: Gemini API 무료 티어의 일일 요청 한도를 초과했습니다.

**해결 방법**:
1. 24시간 후에 다시 시도하세요 (할당량이 리셋됩니다)
2. Google AI Studio에서 유료 플랜으로 업그레이드
3. API 키를 재발급하거나 다른 계정의 키 사용

**현재 상황**:
- 회사: {company_name}
- VectorDB 검색: 완료 ({num_chunks}개 청크)
- 오류: 무료 할당량 초과

자세한 정보: https://ai.google.dev/gemini-api/docs/rate-limits
"""
            else:
                return f"분석 중 오류가 발생했습니다: {error_message[:500]}"
    
    def _create_simple_summary(self, company_name, report_content, user_query):
        """
        AI 없이 간단한 보고서 요약 생성
        
        Args:
            company_name: 회사명
            report_content: 보고서 내용
            user_query: 사용자 질문
            
        Returns:
            str: 요약 내용
        """
        # 보고서 앞부분 2000자 추출
        preview = report_content[:2000]
        
        summary = f"""
📊 {company_name} 공시보고서 분석

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 사용자 질문
{user_query}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📄 보고서 정보
• 회사명: {company_name}
• 전체 내용 길이: {len(report_content):,}자
• 다운로드 완료: ✅

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📑 보고서 내용 미리보기 (처음 2,000자)

{preview}

... (계속)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 안내
보고서 전체 내용은 아래 다운로드 버튼을 통해 확인하실 수 있습니다.

ZIP 파일과 압축 해제된 XML 파일이 함께 제공됩니다.
XML 뷰어(VS Code, XML Notepad 등)로 열어서 확인하세요.

또는 오픈다트 웹사이트(https://dart.fss.or.kr)에서
더 보기 좋은 HTML 버전을 확인할 수 있습니다.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ AI 분석 기능 안내
현재 Gemini API 연동을 일시적으로 비활성화했습니다.
보고서 파일을 다운로드하여 직접 확인하실 수 있습니다.
"""
        return summary
    
    def analyze_company(self, company_name, user_query, status_callback=None, exclude_opinions=False):
        """
        회사 분석 전체 프로세스
        
        Args:
            company_name: 회사명
            user_query: 사용자 질문
            status_callback: 상태 업데이트 콜백 함수
            
        Returns:
            dict: 분석 결과
        """
        import logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        logger = logging.getLogger(__name__)
        
        def update_status(message, component=None, status_type=None):
            """상태 업데이트 헬퍼"""
            logger.info(message)
            if status_callback:
                status_callback(message)
            
            # 다이어그램 업데이트를 위한 상세 로깅
            if component and status_type:
                logger.info(f"🎯 다이어그램 업데이트: {component} → {status_type}")
                if status_callback:
                    status_callback(f"🎯 {component}:{status_type}")
        
        # 상태 콜백을 인스턴스 변수로 설정 (download_report에서 사용)
        self.status_callback = status_callback
        
        result = {
            'success': False,
            'company_name': company_name,
            'corp_code': None,
            'stock_code': None,
            'reports_found': [],
            'analysis': None,
            'error': None,
            'logs': []
        }
        
        try:
            # 1. 회사 고유번호 조회
            update_status(f"🔵 DART 시작: 회사 정보 조회", "dart", "start")
            update_status(f"📋 1단계: '{company_name}' 회사 정보 조회 중...")
            logger.info(f"회사명으로 고유번호 조회 시작: {company_name}")
            
            corp_info = self.get_corp_code(company_name)
            if not corp_info:
                error_msg = f"'{company_name}' 회사를 찾을 수 없습니다."
                logger.error(error_msg)
                result['error'] = error_msg
                return result
            
            logger.info(f"고유번호 조회 성공: {corp_info}")
            
            corp_code, found_name, stock_code = corp_info
            result['company_name'] = found_name
            result['corp_code'] = corp_code
            result['stock_code'] = stock_code
            update_status(f"✅ 회사 정보 조회 완료: {found_name} (종목코드: {stock_code})")
            update_status(f"⚪ DART 완료: 회사 정보 조회", "dart", "complete")
            
            # 2. 보고서 검색 (사용자 질문 기반 자동 선택)
            update_status(f"🔵 Gemini AI 시작: 질문 분석", "gemini", "start")
            update_status(f"🔵 DART 시작: 보고서 검색", "dart", "start")
            update_status(f"📊 2단계: 사용자 질문 분석 및 적절한 보고서 검색 중...")
            logger.info(f"고유번호로 보고서 검색: {corp_code}, 질문: {user_query}")
            
            # 시간 범위 추출
            years = self._extract_time_range(user_query)
            logger.info(f"검색 기간: 최근 {years}년")
            
            reports = self.get_reports(corp_code, report_types=None, user_query=user_query, years=years)
            if not reports:
                error_msg = "보고서를 찾을 수 없습니다."
                logger.error(error_msg)
                result['error'] = error_msg
                return result
            
            logger.info(f"보고서 검색 완료: {len(reports)}개 발견")
            update_status(f"✅ {len(reports)}개의 적합한 보고서를 찾았습니다.")
            update_status(f"⚪ Gemini AI 완료: 질문 분석", "gemini", "complete")
            update_status(f"⚪ DART 완료: 보고서 검색", "dart", "complete")
            
            result['reports_found'] = [
                {
                    'report_nm': r.get('report_nm'),
                    'rcept_dt': r.get('rcept_dt'),
                    'rcept_no': r.get('rcept_no')
                }
                for r in reports[:5]  # 최대 5개만
            ]
            
            # 3. 가장 최근 보고서 다운로드
            latest_report = reports[0]
            rcept_no = latest_report['rcept_no']
            report_name = latest_report['report_nm']
            report_date = latest_report.get('rcept_dt', '')
            
            update_status(f"🔵 VectorDB 시작: 캐시 확인", "vectordb", "start")
            update_status(f"📥 3단계: 메인 보고서 수집 중... ({report_name})")
            logger.info(f"메인 보고서 수집 시작: {rcept_no} - {report_name}")
            
            report_content, zip_path, xml_path = self.download_report(
                rcept_no=rcept_no,
                company_name=found_name,
                report_name=report_name,
                report_date=report_date
            )
            
            if not report_content:
                error_msg = "보고서 내용을 읽을 수 없습니다."
                logger.error(error_msg)
                result['error'] = error_msg
                return result
            
            # VectorDB에서 가져온 경우와 API 다운로드 구분
            if zip_path is None and xml_path is None:
                # VectorDB에서 가져온 경우
                logger.info(f"메인 보고서 VectorDB 검색 확인: {len(report_content)}자")
                logger.info(f"보고서 형식: Markdown (캐시됨)")
                update_status(f"✅ 메인 보고서 VectorDB 검색 확인 ({len(report_content):,}자, Markdown 형식)")
                update_status(f"⚪ VectorDB 완료: 캐시 확인 (적중)", "vectordb", "complete")
            else:
                # API에서 다운로드한 경우
                update_status(f"🔵 DART 시작: 보고서 다운로드", "dart", "start")
                logger.info(f"메인 보고서 다운로드 완료: {len(report_content)}자")
                logger.info(f"보고서 형식: Markdown 변환됨")
                update_status(f"✅ 메인 보고서 다운로드 완료 ({len(report_content):,}자, Markdown 형식)")
                update_status(f"⚪ DART 완료: 보고서 다운로드", "dart", "complete")
                update_status(f"⚪ VectorDB 완료: 캐시 확인 (미적중)", "vectordb", "complete")
            
            # 다운로드 파일 정보 저장
            result['downloaded_files'] = {
                'zip_path': zip_path,
                'xml_path': xml_path,
                'rcept_no': rcept_no,
                'report_name': report_name
            }
            
            # 3-1. 추가 보고서 다운로드 (최근 5개, 사용자 질문 기반)
            update_status(f"📚 3-1단계: DART 추가 보고서 검색 중... (최근 {years}년, 최대 5개)")
            logger.info(f"추가 보고서 검색 시작 (사용자 질문 기반, 기간: {years}년)")
            
            additional_reports_list = self.get_analyst_reports(corp_code, count=5, user_query=user_query, years=years)
            additional_reports = []
            
            if additional_reports_list:
                update_status(f"📥 DART 추가 보고서 {len(additional_reports_list)}개 다운로드 중... (약 10~20초 소요)")
                logger.info(f"추가 보고서 {len(additional_reports_list)}개 수집 시작")
                
                additional_reports = self.download_multiple_reports(
                    additional_reports_list,
                    max_reports=5,
                    company_name=found_name
                )
                
                if additional_reports:
                    total_additional_chars = sum(len(r.get('content', '')) for r in additional_reports)
                    update_status(f"✅ 추가 보고서 {len(additional_reports)}개 수집 완료 (총 {total_additional_chars:,}자)")
                    logger.info(f"추가 보고서 수집 완료: {len(additional_reports)}개")
                    
                    result['additional_reports'] = [
                        {
                            'name': r.get('name'),
                            'date': r.get('date'),
                            'rcept_no': r.get('rcept_no')
                        }
                        for r in additional_reports
                    ]
                else:
                    update_status(f"⚠️  추가 보고서 수집 실패")
                    logger.warning("추가 보고서 수집 실패")
            else:
                update_status(f"ℹ️  추가 보고서를 찾지 못했습니다")
                logger.info("추가 보고서 없음")
            
            # 3-2. 네이버 증권사 리포트 수집 (종목분석 + 산업분석)
            update_status(f"🔵 Naver 시작: 증권사 리포트 수집")
            update_status(f"📈 3-2단계: 네이버 증권사 리포트 수집 중...")
            logger.info("네이버 증권사 리포트 수집 시작")
            
            # 산업군 파악
            industry = self.get_company_industry(corp_code, found_name)
            logger.info(f"산업군: {industry}")
            
            # 종목분석 리포트 수집
            naver_company_reports = []
            company_reports_from_cache = False  # 캐시 여부 추적
            
            try:
                update_status(f"📊 종목분석 리포트 확인 중... ({found_name})")
                
                # 먼저 VectorDB 캐시 확인
                update_status(f"   🔍 VectorDB 캐시 확인 중...")
                cached_company_reports = self.vector_store.get_naver_reports_from_cache(found_name, "NAVER_COMPANY")
                
                if cached_company_reports and len(cached_company_reports) >= 3:
                    # 캐시에 충분한 리포트가 있으면 사용
                    naver_company_reports = cached_company_reports[:3]
                    company_reports_from_cache = True  # 캐시 사용
                    total_chars = sum(len(r.get('content', '')) for r in naver_company_reports)
                    update_status(f"✅ VectorDB 캐시에서 종목분석 리포트 {len(naver_company_reports)}개 로드 (크롤링 생략!)")
                    
                    for idx, report in enumerate(naver_company_reports, 1):
                        update_status(f"   [{idx}] {report.get('name', '')} ({report.get('date', '')})")
                    
                    logger.info(f"종목분석 리포트 캐시 사용: {len(naver_company_reports)}개")
                else:
                    # 캐시에 없거나 부족하면 크롤링
                    if cached_company_reports:
                        update_status(f"   ℹ️  캐시에 {len(cached_company_reports)}개만 있음, 추가 크롤링 필요")
                    else:
                        update_status(f"   ℹ️  캐시 없음, 네이버 금융 크롤링 시작")
                    
                    update_status(f"   🔍 네이버 금융 크롤링 중... (Gemini 추천 검색어 활용)")
                    naver_company_reports = self.naver_crawler.search_company_reports(found_name, max_reports=3)
                
                if naver_company_reports:
                    total_chars = sum(len(r.get('content', '')) for r in naver_company_reports)
                    update_status(f"✅ 종목분석 리포트 {len(naver_company_reports)}개 수집 완료 (총 {total_chars:,}자)")
                    
                    # 발견된 리포트 상세 정보 출력
                    for idx, report in enumerate(naver_company_reports, 1):
                        update_status(f"   [{idx}] {report.get('name', '')} ({report.get('date', '')})")
                    
                    logger.info(f"종목분석 리포트 수집 완료: {len(naver_company_reports)}개")
                else:
                    update_status(f"ℹ️  종목분석 리포트를 찾지 못했습니다")
                    logger.info("종목분석 리포트 없음")
            except Exception as e:
                logger.warning(f"종목분석 리포트 수집 실패: {e}")
                update_status(f"⚠️  종목분석 리포트 수집 실패: {str(e)[:100]}")
            
            # 산업분석 리포트 수집
            naver_industry_reports = []
            industry_reports_from_cache = False  # 캐시 여부 추적
            
            try:
                update_status(f"🏭 산업분석 리포트 확인 중...")
                
                # Gemini로 사용자 질문에서 산업 키워드 추출
                update_status(f"   🤖 Gemini가 사용자 질문 분석 중... (적절한 산업 키워드 추출)")
                industry_keywords = self._extract_industry_keywords(user_query, found_name, industry)
                update_status(f"   ✅ 추출된 산업 키워드: {', '.join(industry_keywords)}")
                
                # 먼저 VectorDB 캐시 확인 (산업 키워드로 검색!)
                update_status(f"   🔍 VectorDB 캐시 확인 중... (키워드: {', '.join(industry_keywords)})")
                cached_industry_reports = self.vector_store.get_naver_reports_from_cache(
                    company_name=None,  # 산업분석은 회사명 필터링 안 함
                    report_type="NAVER_INDUSTRY",
                    industry_keywords=industry_keywords
                )
                
                if cached_industry_reports and len(cached_industry_reports) >= 2:
                    # 캐시에 충분한 리포트가 있으면 사용
                    naver_industry_reports = cached_industry_reports[:2]
                    industry_reports_from_cache = True  # 캐시 사용
                    total_chars = sum(len(r.get('content', '')) for r in naver_industry_reports)
                    update_status(f"✅ VectorDB 캐시에서 산업분석 리포트 {len(naver_industry_reports)}개 로드 (크롤링 생략!)")
                    
                    for idx, report in enumerate(naver_industry_reports, 1):
                        update_status(f"   [{idx}] {report.get('name', '')} ({report.get('date', '')})")
                    
                    logger.info(f"산업분석 리포트 캐시 사용: {len(naver_industry_reports)}개")
                else:
                    # 캐시에 없거나 부족하면 크롤링
                    if cached_industry_reports:
                        update_status(f"   ℹ️  캐시에 {len(cached_industry_reports)}개만 있음, 추가 크롤링 필요")
                    else:
                        update_status(f"   ℹ️  캐시 없음, 네이버 금융 크롤링 시작")
                    
                    update_status(f"   🔍 네이버 금융 크롤링 중... (키워드: {', '.join(industry_keywords)})")
                    naver_industry_reports = self.naver_crawler.search_industry_reports(industry_keywords, max_reports=2)
                
                if naver_industry_reports:
                    total_chars = sum(len(r.get('content', '')) for r in naver_industry_reports)
                    update_status(f"✅ 산업분석 리포트 {len(naver_industry_reports)}개 수집 완료 (총 {total_chars:,}자)")
                    
                    # 발견된 리포트 상세 정보 출력
                    for idx, report in enumerate(naver_industry_reports, 1):
                        update_status(f"   [{idx}] {report.get('name', '')} ({report.get('date', '')})")
                    
                    logger.info(f"산업분석 리포트 수집 완료: {len(naver_industry_reports)}개")
                else:
                    update_status(f"ℹ️  산업분석 리포트를 찾지 못했습니다")
                    logger.info("산업분석 리포트 없음")
            except Exception as e:
                logger.warning(f"산업분석 리포트 수집 실패: {e}")
                update_status(f"⚠️  산업분석 리포트 수집 실패: {str(e)[:100]}")
            
            update_status(f"⚪ Naver 완료: 증권사 리포트 수집")
            
            # 네이버 리포트 결과 저장
            result['naver_reports'] = {
                'company_reports': [
                    {
                        'name': r.get('name'),
                        'date': r.get('date'),
                        'url': r.get('url')
                    }
                    for r in naver_company_reports
                ],
                'industry_reports': [
                    {
                        'name': r.get('name'),
                        'date': r.get('date'),
                        'url': r.get('url')
                    }
                    for r in naver_industry_reports
                ]
            }
            
            # 모든 추가 보고서 통합
            all_additional_reports = additional_reports + naver_company_reports + naver_industry_reports
            logger.info(f"전체 추가 보고서: {len(all_additional_reports)}개 (DART: {len(additional_reports)}, 종목: {len(naver_company_reports)}, 산업: {len(naver_industry_reports)})")
            
            # 3-3. 모든 리포트를 VectorDB에 저장
            update_status(f"🔵 VectorDB 시작: 리포트 저장")
            update_status(f"💾 VectorDB에 리포트 저장 중...")
            logger.info("VectorDB 저장 시작")
            
            try:
                # 메인 DART 보고서 저장
                if not self.vector_store.check_report_exists(rcept_no):
                    update_status(f"   💾 메인 보고서 VectorDB 저장 중...")
                    self.vector_store.add_report(
                        rcept_no=rcept_no,
                        report_name=report_name,
                        company_name=found_name,
                        report_date=report_date,
                        content=report_content
                    )
                    logger.info(f"VectorDB 저장: {report_name} ({len(report_content):,}자)")
                
                # 추가 DART 보고서 저장
                for add_report in additional_reports:
                    add_rcept_no = add_report.get('rcept_no')
                    add_content = add_report.get('content', '')
                    
                    if add_rcept_no and add_content and not self.vector_store.check_report_exists(add_rcept_no):
                        self.vector_store.add_report(
                            rcept_no=add_rcept_no,
                            report_name=add_report.get('name', ''),
                            company_name=found_name,
                            report_date=add_report.get('date', ''),
                            content=add_content
                        )
                        logger.info(f"VectorDB 저장: {add_report.get('name', '')[:50]}")
                
                # 증권사 리포트 저장 (새로 크롤링한 것만)
                new_reports_to_save = []
                
                if naver_company_reports and not company_reports_from_cache:
                    new_reports_to_save.extend([(r, "NAVER_COMPANY") for r in naver_company_reports])
                
                if naver_industry_reports and not industry_reports_from_cache:
                    new_reports_to_save.extend([(r, "NAVER_INDUSTRY") for r in naver_industry_reports])
                
                if new_reports_to_save:
                    update_status(f"   💾 증권사 리포트 {len(new_reports_to_save)}개 VectorDB 저장 중...")
                    
                    for report, report_type_prefix in new_reports_to_save:
                        report_name = report.get('name', '')
                        report_date = report.get('date', '')
                        content = report.get('content', '')
                        
                        if content:
                            report_url = report.get('url', '')
                            rcept_no_hash = f"{report_type_prefix}_{hash(report_url)}"
                            
                            keywords_to_save = None
                            if report_type_prefix == "NAVER_INDUSTRY":
                                keywords_to_save = industry_keywords
                            
                            if not self.vector_store.check_report_exists(rcept_no_hash):
                                self.vector_store.add_report(
                                    rcept_no=rcept_no_hash,
                                    report_name=report_name,
                                    company_name=found_name,
                                    report_date=report_date,
                                    content=content,
                                    industry_keywords=keywords_to_save
                                )
                                logger.info(f"VectorDB 저장: {report_name[:50]}")
                
                update_status(f"✅ 모든 리포트 VectorDB 저장 완료")
                update_status(f"⚪ VectorDB 완료: 리포트 저장")
                logger.info("VectorDB 저장 완료")
                
            except Exception as ve:
                logger.warning(f"VectorDB 저장 실패 (계속 진행): {ve}")
                update_status(f"⚠️  VectorDB 저장 실패 (계속 진행)")
                update_status(f"⚪ VectorDB 완료: 리포트 저장 (실패)")
            
            # 4. Gemini로 분석
            if all_additional_reports:
                dart_count = len(additional_reports)
                company_count = len(naver_company_reports)
                industry_count = len(naver_industry_reports)
                
                report_summary = f"DART {dart_count}개"
                if company_count > 0:
                    report_summary += f" + 종목분석 {company_count}개"
                if industry_count > 0:
                    report_summary += f" + 산업분석 {industry_count}개"
                
                # 예상 시간 계산 (보고서 개수 및 크기 기반)
                total_reports = 1 + len(all_additional_reports)  # 메인 + 추가
                total_chars = len(report_content) + sum(len(r.get('content', '')) for r in all_additional_reports)
                
                # 토큰 수 추정 (한글은 약 1자 = 2토큰)
                estimated_tokens = total_chars * 2
                
                # 시간 추정: 1백만 토큰당 약 1분
                estimated_minutes = max(2, int(estimated_tokens / 500000))  # 최소 2분
                
                update_status(f"🤖 4단계: Gemini AI 분석 중...")
                update_status(f"   📊 분석 대상: 메인 보고서 + {report_summary}")
                update_status(f"   📝 총 텍스트: {total_chars:,}자 (약 {estimated_tokens:,} 토큰)")
                update_status(f"   ⏱️  예상 소요 시간: 약 {estimated_minutes}~{estimated_minutes+2}분")
                update_status(f"   🔄 Gemini API 호출 중... (대용량 보고서 처리)")
                logger.info(f"Gemini AI 분석 시작 (메인 + {report_summary}, 예상: {estimated_minutes}분, 의견제외: {exclude_opinions})")
            else:
                update_status(f"🤖 4단계: Gemini AI 분석 중... (메인 보고서만, 약 1~2분 소요)")
                logger.info(f"Gemini AI 분석 시작 (의견제외: {exclude_opinions})")
            
            # 4-1. VectorDB에서 질문 관련 청크 검색 (RAG)
            update_status(f"🔵 VectorDB 시작: RAG 검색")
            update_status(f"🔍 VectorDB에서 질문 관련 내용 검색 중...")
            logger.info(f"VectorDB 검색 시작: {user_query}")
            
            try:
                # 사용자 질문으로 유사도 검색 (상위 20개 청크)
                relevant_chunks = self.vector_store.search_similar_reports(
                    query=user_query,
                    company_name=found_name,
                    k=20  # 상위 20개 청크
                )
                
                if relevant_chunks:
                    total_chunk_chars = sum(len(chunk[0].page_content) for chunk in relevant_chunks)
                    update_status(f"✅ {len(relevant_chunks)}개 관련 청크 발견 (총 {total_chunk_chars:,}자)")
                    update_status(f"⚪ VectorDB 완료: RAG 검색")
                    logger.info(f"VectorDB 검색 완료: {len(relevant_chunks)}개 청크, {total_chunk_chars:,}자")
                    
                    # 검색된 청크들을 하나의 문자열로 결합 (보고서명 명확하게 표기)
                    context_from_chunks = "\n\n".join([
                        f"━━━ 보고서: {chunk[0].metadata.get('report_name', 'Unknown')} ({chunk[0].metadata.get('report_date', '')}) ━━━\n"
                        f"[Reference {idx+1}/{len(relevant_chunks)} - 청크 {chunk[0].metadata.get('chunk_index', '?')}/{chunk[0].metadata.get('total_chunks', '?')}]\n"
                        f"{chunk[0].page_content}"
                        for idx, chunk in enumerate(relevant_chunks)
                    ])
                    
                    # Gemini 분석 (관련 청크만 사용)
                    update_status(f"🔵 Gemini AI 시작: 분석", "gemini", "start")
                    update_status(f"🤖 Gemini AI 분석 중... (검색된 관련 내용만 사용)")
                    update_status(f"   📊 입력 데이터: {len(relevant_chunks)}개 청크, {total_chunk_chars:,}자")
                    
                    analysis = self.analyze_with_gemini_rag(
                        company_name=found_name,
                        user_query=user_query,
                        relevant_context=context_from_chunks,
                        num_chunks=len(relevant_chunks),
                        exclude_opinions=exclude_opinions
                    )
                    
                    logger.info(f"Gemini AI 분석 완료: {len(analysis)}자")
                    update_status(f"✅ AI 분석 완료!")
                    update_status(f"⚪ Gemini AI 완료: 분석", "gemini", "complete")
                    
                else:
                    update_status(f"⚠️  관련 내용을 찾지 못했습니다. VectorDB에 데이터가 없을 수 있습니다.")
                    analysis = "VectorDB에서 관련 내용을 찾지 못했습니다. 리포트가 제대로 저장되었는지 확인해주세요."
                    
            except Exception as e:
                logger.error(f"VectorDB 검색 또는 Gemini 분석 실패: {e}")
                update_status(f"❌ 분석 실패: {str(e)[:100]}")
                analysis = f"분석 중 오류 발생: {str(e)}"
            
            # 분석 결과 저장
            result['analysis'] = analysis
            result['success'] = True
            logger.info("전체 분석 프로세스 완료 (RAG 모드)")
            
            # ===== 디버깅용 MD 파일 저장 (선택적) =====
            # 환경 변수 SAVE_DEBUG_REPORTS=True로 설정하면 활성화
            # 아래 코드 전체가 주석처리됨
            """
            if os.getenv('SAVE_DEBUG_REPORTS', 'False').lower() == 'true':
                # 디버깅 코드...
                main_zip_dest = os.path.join(output_dir, f"{timestamp}_{found_name}_main_report_ORIGINAL.zip")
            extracted_dir = os.path.join("downloads", f"{rcept_no}_extracted")
            zip_source = os.path.join("downloads", f"{rcept_no}.zip")
            
            zip_saved = False
            if os.path.exists(zip_source):
                shutil.copy2(zip_source, main_zip_dest)
                zip_saved = True
                logger.info(f"원본 ZIP 복사: {zip_source} → {main_zip_dest}")
            
            # 1-2. 원본 XML 파일 복사
            main_xml_dest = os.path.join(output_dir, f"{timestamp}_{found_name}_main_report_ORIGINAL.xml")
            xml_source = os.path.join(extracted_dir, f"{rcept_no}.xml")
            
            xml_saved = False
            if os.path.exists(xml_source):
                shutil.copy2(xml_source, main_xml_dest)
                xml_saved = True
                logger.info(f"원본 XML 복사: {xml_source} → {main_xml_dest}")
            
            # 1-3. 변환 후 텍스트 저장 (XML → 텍스트 추출 결과)
            main_raw_path = os.path.join(output_dir, f"{timestamp}_{found_name}_main_report_CONVERTED.txt")
            with open(main_raw_path, 'w', encoding='utf-8') as f:
                f.write(f"=== {found_name} - 메인 보고서 (XML → 텍스트 변환 결과) ===\n\n")
                f.write(f"보고서명: {report_name}\n")
                f.write(f"보고서 코드: {rcept_no}\n")
                f.write(f"문자 수: {len(report_content):,}자\n\n")
                f.write("=" * 80 + "\n\n")
                f.write(report_content)
            
            # 1-4. MD 파일 저장 (읽기 쉽게 정리된 버전)
            main_report_path = os.path.join(output_dir, f"{timestamp}_{found_name}_main_report.md")
            with open(main_report_path, 'w', encoding='utf-8') as f:
                f.write(f"# {found_name} - 메인 보고서\n\n")
                f.write(f"**보고서명**: {report_name}\n\n")
                f.write(f"**보고서 코드**: {rcept_no}\n\n")
                f.write(f"**문자 수**: {len(report_content):,}자\n\n")
                f.write("---\n\n")
                f.write(report_content)
            
            files_saved = []
            if zip_saved: files_saved.append("ZIP")
            if xml_saved: files_saved.append("XML")
            files_saved.extend(["TXT", "MD"])
            
                update_status(f"   ✅ 메인 보고서 저장: {' + '.join(files_saved)}")
                logger.info(f"메인 보고서 저장 완료: {' + '.join(files_saved)} ({len(report_content):,}자)")
                
                # 2. 추가 DART 보고서 저장 (원본 ZIP + XML + 변환 후 텍스트 + MD)
            if additional_reports:
                update_status(f"   📄 추가 DART 보고서 {len(additional_reports)}개 저장 중...")
                for idx, add_report in enumerate(additional_reports, 1):
                    content = add_report.get('content', '')
                    add_rcept_no = add_report.get('rcept_no', 'N/A')
                    add_name = add_report.get('name', 'Unknown')
                    add_date = add_report.get('date', 'N/A')
                    
                    # 2-1. 원본 ZIP 파일 복사
                    add_zip_dest = os.path.join(output_dir, f"{timestamp}_{found_name}_dart_{idx}_ORIGINAL.zip")
                    add_zip_source = os.path.join("downloads", f"{add_rcept_no}.zip")
                    
                    add_zip_saved = False
                    if os.path.exists(add_zip_source):
                        shutil.copy2(add_zip_source, add_zip_dest)
                        add_zip_saved = True
                    
                    # 2-2. 원본 XML 파일 복사
                    add_xml_dest = os.path.join(output_dir, f"{timestamp}_{found_name}_dart_{idx}_ORIGINAL.xml")
                    add_extracted_dir = os.path.join("downloads", f"{add_rcept_no}_extracted")
                    add_xml_source = os.path.join(add_extracted_dir, f"{add_rcept_no}.xml")
                    
                    add_xml_saved = False
                    if os.path.exists(add_xml_source):
                        shutil.copy2(add_xml_source, add_xml_dest)
                        add_xml_saved = True
                    
                    # 2-3. 변환 후 텍스트 저장
                    add_converted_path = os.path.join(output_dir, f"{timestamp}_{found_name}_dart_{idx}_CONVERTED.txt")
                    with open(add_converted_path, 'w', encoding='utf-8') as f:
                        f.write(f"=== {found_name} - DART 추가 보고서 #{idx} (XML → 텍스트 변환 결과) ===\n\n")
                        f.write(f"보고서명: {add_name}\n")
                        f.write(f"보고서 코드: {add_rcept_no}\n")
                        f.write(f"보고서 날짜: {add_date}\n")
                        f.write(f"문자 수: {len(content):,}자\n\n")
                        f.write("=" * 80 + "\n\n")
                        f.write(content)
                    
                    # 2-4. MD 파일 저장
                    add_report_path = os.path.join(output_dir, f"{timestamp}_{found_name}_dart_{idx}.md")
                    with open(add_report_path, 'w', encoding='utf-8') as f:
                        f.write(f"# {found_name} - DART 추가 보고서 #{idx}\n\n")
                        f.write(f"**보고서명**: {add_name}\n\n")
                        f.write(f"**보고서 코드**: {add_rcept_no}\n\n")
                        f.write(f"**보고서 날짜**: {add_date}\n\n")
                        f.write(f"**문자 수**: {len(content):,}자\n\n")
                        f.write("---\n\n")
                        f.write(content)
                    
                    add_files_saved = []
                    if add_zip_saved: add_files_saved.append("ZIP")
                    if add_xml_saved: add_files_saved.append("XML")
                    add_files_saved.extend(["TXT", "MD"])
                    
                    logger.info(f"DART 추가 #{idx}: {add_name[:50]} ({' + '.join(add_files_saved)}, {len(content):,}자)")
                
                update_status(f"   ✅ DART 보고서 {len(additional_reports)}개 저장 완료 (ZIP + XML + TXT + MD)")
            
            # 3. 종목분석 리포트 저장 (PDF 추출 텍스트 + MD)
            if naver_company_reports:
                update_status(f"   📊 종목분석 리포트 {len(naver_company_reports)}개 저장 중...")
                for idx, company_report in enumerate(naver_company_reports, 1):
                    content = company_report.get('content', '')
                    comp_name = company_report.get('name', 'Unknown')
                    comp_date = company_report.get('date', 'N/A')
                    comp_url = company_report.get('url', 'N/A')
                    
                    # 3-1. PDF에서 추출한 텍스트 저장
                    company_converted_path = os.path.join(output_dir, f"{timestamp}_{found_name}_company_{idx}_CONVERTED.txt")
                    with open(company_converted_path, 'w', encoding='utf-8') as f:
                        f.write(f"=== {found_name} - 증권사 종목분석 리포트 #{idx} (PDF → 텍스트 추출 결과) ===\n\n")
                        f.write(f"리포트명: {comp_name}\n")
                        f.write(f"발행일: {comp_date}\n")
                        f.write(f"URL: {comp_url}\n")
                        f.write(f"문자 수: {len(content):,}자\n\n")
                        f.write("=" * 80 + "\n\n")
                        f.write(content)
                    
                    # 3-2. MD 파일 저장
                    company_report_path = os.path.join(output_dir, f"{timestamp}_{found_name}_company_{idx}.md")
                    with open(company_report_path, 'w', encoding='utf-8') as f:
                        f.write(f"# {found_name} - 증권사 종목분석 리포트 #{idx}\n\n")
                        f.write(f"**리포트명**: {comp_name}\n\n")
                        f.write(f"**발행일**: {comp_date}\n\n")
                        f.write(f"**URL**: {comp_url}\n\n")
                        f.write(f"**문자 수**: {len(content):,}자\n\n")
                        f.write("---\n\n")
                        f.write(content)
                    
                    logger.info(f"종목분석 #{idx}: {comp_name[:50]} (TXT + MD, {len(content):,}자)")
                
                update_status(f"   ✅ 종목분석 리포트 {len(naver_company_reports)}개 저장 완료 (TXT + MD)")
            
            # 4. 산업분석 리포트 저장 (PDF 추출 텍스트 + MD)
            if naver_industry_reports:
                update_status(f"   🏭 산업분석 리포트 {len(naver_industry_reports)}개 저장 중...")
                for idx, industry_report in enumerate(naver_industry_reports, 1):
                    content = industry_report.get('content', '')
                    ind_name = industry_report.get('name', 'Unknown')
                    ind_date = industry_report.get('date', 'N/A')
                    ind_url = industry_report.get('url', 'N/A')
                    
                    # 4-1. PDF에서 추출한 텍스트 저장
                    industry_converted_path = os.path.join(output_dir, f"{timestamp}_{found_name}_industry_{idx}_CONVERTED.txt")
                    with open(industry_converted_path, 'w', encoding='utf-8') as f:
                        f.write(f"=== {found_name} - 증권사 산업분석 리포트 #{idx} (PDF → 텍스트 추출 결과) ===\n\n")
                        f.write(f"리포트명: {ind_name}\n")
                        f.write(f"발행일: {ind_date}\n")
                        f.write(f"URL: {ind_url}\n")
                        f.write(f"문자 수: {len(content):,}자\n\n")
                        f.write("=" * 80 + "\n\n")
                        f.write(content)
                    
                    # 4-2. MD 파일 저장
                    industry_report_path = os.path.join(output_dir, f"{timestamp}_{found_name}_industry_{idx}.md")
                    with open(industry_report_path, 'w', encoding='utf-8') as f:
                        f.write(f"# {found_name} - 증권사 산업분석 리포트 #{idx}\n\n")
                        f.write(f"**리포트명**: {ind_name}\n\n")
                        f.write(f"**발행일**: {ind_date}\n\n")
                        f.write(f"**URL**: {ind_url}\n\n")
                        f.write(f"**문자 수**: {len(content):,}자\n\n")
                        f.write("---\n\n")
                        f.write(content)
                    
                    logger.info(f"산업분석 #{idx}: {ind_name[:50]} (TXT + MD, {len(content):,}자)")
                
                update_status(f"   ✅ 산업분석 리포트 {len(naver_industry_reports)}개 저장 완료 (TXT + MD)")
            
            # 5. 전체 통합 요약 파일 저장
            summary_path = os.path.join(output_dir, f"{timestamp}_{found_name}_SUMMARY.md")
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write(f"# {found_name} - 리포트 수집 결과 요약\n\n")
                f.write(f"**생성 시간**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(f"**사용자 질문**: {user_query}\n\n")
                f.write(f"---\n\n")
                
                # 통계
                f.write(f"## 📊 수집 통계\n\n")
                f.write(f"| 구분 | 개수 | 총 문자 수 |\n")
                f.write(f"|------|------|------------|\n")
                f.write(f"| 메인 DART 보고서 | 1개 | {len(report_content):,}자 |\n")
                f.write(f"| 추가 DART 보고서 | {len(additional_reports)}개 | {sum(len(r.get('content', '')) for r in additional_reports):,}자 |\n")
                f.write(f"| 증권사 종목분석 | {len(naver_company_reports)}개 | {sum(len(r.get('content', '')) for r in naver_company_reports):,}자 |\n")
                f.write(f"| 증권사 산업분석 | {len(naver_industry_reports)}개 | {sum(len(r.get('content', '')) for r in naver_industry_reports):,}자 |\n")
                f.write(f"| **전체 합계** | **{1 + len(all_additional_reports)}개** | **{total_chars:,}자** |\n\n")
                
                f.write(f"**예상 토큰 수**: {estimated_tokens:,} 토큰\n\n")
                f.write(f"---\n\n")
                
                # 메인 보고서 정보
                f.write(f"## 📄 메인 DART 보고서\n\n")
                f.write(f"- **ZIP 원본**: `{timestamp}_{found_name}_main_report_ORIGINAL.zip`\n")
                f.write(f"- **XML 원본**: `{timestamp}_{found_name}_main_report_ORIGINAL.xml`\n")
                f.write(f"- **변환 후 텍스트**: `{timestamp}_{found_name}_main_report_CONVERTED.txt`\n")
                f.write(f"- **MD 파일**: `{timestamp}_{found_name}_main_report.md`\n")
                f.write(f"- **보고서명**: {report_name}\n")
                f.write(f"- **보고서 코드**: {rcept_no}\n")
                f.write(f"- **문자 수**: {len(report_content):,}자\n\n")
                
                # 추가 DART 보고서 목록
                if additional_reports:
                    f.write(f"## 📚 추가 DART 보고서 ({len(additional_reports)}개)\n\n")
                    for idx, rep in enumerate(additional_reports, 1):
                        f.write(f"### {idx}. {rep.get('name', 'Unknown')}\n")
                        f.write(f"- **ZIP 원본**: `{timestamp}_{found_name}_dart_{idx}_ORIGINAL.zip`\n")
                        f.write(f"- **XML 원본**: `{timestamp}_{found_name}_dart_{idx}_ORIGINAL.xml`\n")
                        f.write(f"- **변환 후 텍스트**: `{timestamp}_{found_name}_dart_{idx}_CONVERTED.txt`\n")
                        f.write(f"- **MD 파일**: `{timestamp}_{found_name}_dart_{idx}.md`\n")
                        f.write(f"- **보고서 코드**: {rep.get('rcept_no', 'N/A')}\n")
                        f.write(f"- **날짜**: {rep.get('date', 'N/A')}\n")
                        f.write(f"- **문자 수**: {len(rep.get('content', '')):,}자\n\n")
                
                # 종목분석 리포트 목록
                if naver_company_reports:
                    f.write(f"## 📈 증권사 종목분석 리포트 ({len(naver_company_reports)}개)\n\n")
                    for idx, rep in enumerate(naver_company_reports, 1):
                        f.write(f"### {idx}. {rep.get('name', 'Unknown')}\n")
                        f.write(f"- **변환 후 텍스트**: `{timestamp}_{found_name}_company_{idx}_CONVERTED.txt`\n")
                        f.write(f"- **MD 파일**: `{timestamp}_{found_name}_company_{idx}.md`\n")
                        f.write(f"- **발행일**: {rep.get('date', 'N/A')}\n")
                        f.write(f"- **URL**: {rep.get('url', 'N/A')}\n")
                        f.write(f"- **문자 수**: {len(rep.get('content', '')):,}자\n\n")
                
                # 산업분석 리포트 목록
                if naver_industry_reports:
                    f.write(f"## 🏭 증권사 산업분석 리포트 ({len(naver_industry_reports)}개)\n\n")
                    for idx, rep in enumerate(naver_industry_reports, 1):
                        f.write(f"### {idx}. {rep.get('name', 'Unknown')}\n")
                        f.write(f"- **변환 후 텍스트**: `{timestamp}_{found_name}_industry_{idx}_CONVERTED.txt`\n")
                        f.write(f"- **MD 파일**: `{timestamp}_{found_name}_industry_{idx}.md`\n")
                        f.write(f"- **발행일**: {rep.get('date', 'N/A')}\n")
                        f.write(f"- **URL**: {rep.get('url', 'N/A')}\n")
                        f.write(f"- **문자 수**: {len(rep.get('content', '')):,}자\n\n")
                
                # 저장 위치
                f.write(f"---\n\n")
                f.write(f"## 📁 저장 위치\n\n")
                f.write(f"모든 파일은 `{os.path.abspath(output_dir)}/` 폴더에 저장되었습니다.\n")
            
            update_status(f"✅ 모든 리포트 저장 완료!")
            update_status(f"   📁 저장 위치: {os.path.abspath(output_dir)}/")
            update_status(f"   📄 요약 파일: {summary_path}")
            update_status(f"   총 {1 + len(all_additional_reports)}개 파일 ({total_chars:,}자)")
            
            logger.info(f"모든 리포트 MD 파일 저장 완료: {output_dir}/")
            logger.info(f"  - 메인: {len(report_content):,}자")
            logger.info(f"  - DART 추가: {len(additional_reports)}개")
            logger.info(f"  - 종목분석: {len(naver_company_reports)}개")
            logger.info(f"  - 산업분석: {len(naver_industry_reports)}개")
            
                # 디버깅 코드 끝
                pass
            """
            # 디버깅용 MD 파일 저장 코드 끝
            
            # 분석 완료 후 오래된 다운로드 파일 정리 (최신 5개만 유지)
            update_status(f"🧹 다운로드 파일 정리 중...")
            try:
                self.cleanup_downloads(keep_latest=5)
            except Exception as cleanup_error:
                logger.warning(f"파일 정리 실패 (계속 진행): {cleanup_error}")
            
            return result
            
        except Exception as e:
            error_msg = f"분석 중 오류 발생: {str(e)}"
            logger.error(error_msg, exc_info=True)
            result['error'] = error_msg
            return result

