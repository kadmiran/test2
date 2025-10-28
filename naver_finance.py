#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
네이버 금융 증권사 리포트 크롤러
종목분석 및 산업분석 리포트를 수집합니다.
"""

import requests
import os
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote
import fitz  # PyMuPDF
from config import config


class NaverFinanceCrawler:
    """네이버 금융 증권사 리포트 크롤러"""
    
    def __init__(self, llm_orchestrator=None):
        """
        초기화
        
        Args:
            llm_orchestrator: LLM Orchestrator (회사명 변형 추천용, 선택사항)
        """
        self.llm_orchestrator = llm_orchestrator
        # config에서 User-Agent 가져오기
        self.headers = {
            'User-Agent': config.CRAWLER_USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': config.NAVER_FINANCE_BASE_URL
        }
    
    def _get_company_name_variations(self, company_name):
        """
        LLM Orchestrator를 사용하여 회사명의 다양한 표기 가져오기
        
        Args:
            company_name: 입력된 회사명
            
        Returns:
            list: 가능한 회사명 표기 리스트
        """
        if not self.llm_orchestrator:
            return [company_name]
        
        try:
            prompt = f"""
한국 상장회사 "{company_name}"의 공식 명칭과 가능한 모든 표기 방법을 나열해주세요.

예시:
- "KT" 입력 → ["KT", "케이티", "주식회사 케이티", "주식회사 KT", "Korea Telecom"]
- "삼성전자" 입력 → ["삼성전자", "삼성전자주식회사", "Samsung Electronics"]
- "SK텔레콤" 입력 → ["SK텔레콤", "에스케이텔레콤", "SK Telecom"]

"{company_name}"에 대해 가능한 모든 표기를 쉼표로 구분하여 나열해주세요.
답변은 오직 회사명 리스트만 작성하고, 설명은 넣지 마세요.
형식: 표기1, 표기2, 표기3
"""
            
            variations_text = self.llm_orchestrator.generate(
                prompt=prompt,
                task_type='name_variation'
            ).strip()
            
            # 쉼표로 분리하여 리스트 생성
            variations = [v.strip() for v in variations_text.split(',')]
            
            # 원래 입력값도 포함
            if company_name not in variations:
                variations.insert(0, company_name)
            
            print(f"   🤖 LLM 추천 검색어: {variations}")
            return variations
            
        except Exception as e:
            print(f"   ⚠️  LLM 검색어 추천 실패: {e}")
            return [company_name]
    
    def _extract_text_from_pdf(self, pdf_path):
        """
        PDF 파일에서 텍스트 추출
        
        Args:
            pdf_path: PDF 파일 경로
            
        Returns:
            str: 추출된 텍스트
        """
        try:
            print(f"      📄 PDF 텍스트 추출 중: {os.path.basename(pdf_path)}")
            text = ""
            
            with fitz.open(pdf_path) as doc:
                total_pages = len(doc)
                
                for page_num, page in enumerate(doc, 1):
                    page_text = page.get_text()
                    text += f"\n--- 페이지 {page_num} ---\n{page_text}"
                    
                    if page_num % 10 == 0:
                        print(f"         ✓ {page_num}/{total_pages} 페이지 처리 완료")
                
                return text
                
        except Exception as e:
            print(f"      ❌ PDF 텍스트 추출 실패: {e}")
            return ""
    
    def search_company_reports(self, company_name, max_reports=5):
        """
        네이버 금융에서 종목분석 리포트 검색 및 다운로드
        
        Args:
            company_name: 회사명
            max_reports: 최대 다운로드 수
            
        Returns:
            list: [{name, date, content, url}, ...] 형식의 리스트
        """
        try:
            print(f"📊 네이버 금융에서 '{company_name}' 종목분석 리포트 검색 중...")
            
            # LLM Orchestrator로 회사명 변형 검색어 가져오기
            if self.llm_orchestrator:
                print(f"🤖 LLM Orchestrator에게 '{company_name}'의 검색어 추천 요청 중...")
                search_variations = self._get_company_name_variations(company_name)
            else:
                search_variations = [company_name]
            
            # 네이버 증권 종목분석 리포트 검색 URL
            base_url = "https://finance.naver.com/research/company_list.naver"
            
            # 모든 검색어로 검색 시도
            all_reports = []
            seen_urls = set()  # 중복 제거용
            
            for variation_idx, search_term in enumerate(search_variations):
                print(f"\n   🔍 [{variation_idx + 1}/{len(search_variations)}] 검색어 '{search_term}'로 검색 중...")
                
                try:
                    # 검색어 EUC-KR 인코딩
                    keyword_euckr = search_term.encode('euc-kr')
                    encoded_keyword = quote(keyword_euckr)
                    
                    # URL 직접 구성
                    search_url = f"{base_url}?searchType=keyword&keyword={encoded_keyword}&brokerCode=&writeFromDate=&writeToDate=&itemName=&itemCode="
                    
                    print(f"      EUC-KR 인코딩: {encoded_keyword}")
                    
                    # 검색 페이지 로드
                    response = requests.get(search_url, headers=self.headers, timeout=30)
                    response.raise_for_status()
                    response.encoding = 'euc-kr'
                    
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # 첫 번째 검색어일 때만 HTML 디버깅 파일 저장
                    if variation_idx == 0:
                        debug_html_path = 'downloads/debug_company_list.html'
                        os.makedirs('downloads', exist_ok=True)
                        with open(debug_html_path, 'w', encoding='utf-8') as f:
                            f.write(soup.prettify())
                        print(f"      🔍 HTML 저장됨: {debug_html_path}")
                    
                    # 테이블 찾기
                    table = soup.find('table', class_='type_1')
                    if not table:
                        tables = soup.find_all('table')
                        for t in tables:
                            rows = t.find_all('tr')
                            if len(rows) > 5:
                                table = t
                                break
                    
                    if not table:
                        print(f"      ⚠️  테이블을 찾을 수 없습니다")
                        continue
                    
                    rows = table.find_all('tr')
                    
                    # 헤더 분석 (첫 검색어일 때만)
                    if variation_idx == 0:
                        header_map = {}
                        if len(rows) > 0:
                            first_row = rows[0]
                            header_cells = first_row.find_all(['td', 'th'])
                            print(f"      📊 헤더: {len(header_cells)}개 열")
                            for idx, cell in enumerate(header_cells):
                                header_text = cell.get_text(strip=True)
                                header_map[header_text] = idx
                                print(f"         열 {idx}: '{header_text}'")
                        
                        stock_idx = header_map.get('종목명', 0)
                        title_idx = header_map.get('제목', 1)
                        broker_idx = header_map.get('증권사', 2)
                        pdf_idx = header_map.get('첨부', 3)
                        date_idx = header_map.get('작성일', 4)
                    
                    # 리포트 파싱
                    found_count = 0
                    for row in rows[1:]:  # 헤더 제외
                        try:
                            cells = row.find_all('td')
                            if len(cells) < 5:
                                continue
                            
                            # 데이터 추출
                            stock_name = cells[stock_idx].get_text(strip=True) if len(cells) > stock_idx else ""
                            
                            title_cell = cells[title_idx]
                            title_link = title_cell.find('a')
                            if not title_link:
                                continue
                            
                            title = title_link.get_text(strip=True)
                            if not title:
                                continue
                            
                            broker = cells[broker_idx].get_text(strip=True) if len(cells) > broker_idx else "증권사"
                            
                            pdf_cell = cells[pdf_idx]
                            pdf_link = pdf_cell.find('a')
                            if not pdf_link or not pdf_link.get('href'):
                                continue
                            
                            pdf_url = pdf_link.get('href')
                            
                            # 절대 URL로 변환
                            if not pdf_url.startswith('http'):
                                if pdf_url.startswith('//'):
                                    pdf_url = 'https:' + pdf_url
                                else:
                                    pdf_url = urljoin('https://stock.pstatic.net', pdf_url)
                            
                            # 중복 체크
                            if pdf_url in seen_urls:
                                continue
                            seen_urls.add(pdf_url)
                            
                            date = cells[date_idx].get_text(strip=True) if len(cells) > date_idx else "날짜미상"
                            
                            all_reports.append({
                                'stock_name': stock_name,
                                'title': title,
                                'broker': broker,
                                'date': date,
                                'pdf_url': pdf_url
                            })
                            
                            found_count += 1
                            
                        except Exception as row_error:
                            continue
                    
                    print(f"      ✓ {found_count}개 리포트 발견")
                    
                    # 충분한 리포트를 찾으면 중단
                    if len(all_reports) >= max_reports * 2:
                        print(f"      ℹ️  충분한 리포트 수집, 검색 중단")
                        break
                    
                    # 다음 검색어 사이에 짧은 지연
                    time.sleep(0.5)
                    
                except Exception as search_error:
                    print(f"      ⚠️  검색 실패: {search_error}")
                    continue
            
            if not all_reports:
                print(f"\n   ⚠️  '{company_name}'에 대한 리포트를 찾을 수 없습니다.")
                return []
            
            # 날짜 기준으로 정렬 (최신순)
            def parse_date(date_str):
                """YY.MM.DD 형식을 정렬 가능한 값으로 변환"""
                try:
                    if not date_str or date_str == "날짜미상":
                        return "00.00.00"
                    return date_str
                except:
                    return "00.00.00"
            
            all_reports.sort(key=lambda x: parse_date(x['date']), reverse=True)
            
            # 상위 N개만 선택
            selected_reports = all_reports[:max_reports]
            
            print(f"\n   ✅ 총 {len(all_reports)}개 리포트 발견 (중복 제거 후)")
            print(f"   📋 선정된 리포트 (최신 {len(selected_reports)}개):")
            for idx, report in enumerate(selected_reports, 1):
                print(f"      [{idx}] {report['stock_name']} - {report['title']}")
                print(f"          증권사: {report['broker']}, 날짜: {report['date']}")
                print(f"          PDF: {report['pdf_url'][:80]}...")
            print()
            
            # PDF 다운로드 및 텍스트 추출
            extracted_reports = []
            
            for i, report in enumerate(selected_reports, 1):
                try:
                    print(f"\n   [{i}/{len(selected_reports)}] PDF 다운로드 중: {report['title'][:50]}...")
                    
                    # PDF 다운로드
                    pdf_response = requests.get(report['pdf_url'], headers=self.headers, timeout=60)
                    pdf_response.raise_for_status()
                    
                    # 임시 PDF 파일 저장
                    pdf_filename = f"downloads/naver_report_{i}_{int(time.time())}.pdf"
                    os.makedirs('downloads', exist_ok=True)
                    
                    with open(pdf_filename, 'wb') as f:
                        f.write(pdf_response.content)
                    
                    print(f"      💾 PDF 저장: {len(pdf_response.content):,} bytes")
                    
                    # 텍스트 추출
                    text_content = self._extract_text_from_pdf(pdf_filename)
                    
                    if text_content:
                        extracted_reports.append({
                            'name': f"[{report['broker']}] {report['title']}",
                            'date': report['date'],
                            'content': text_content,
                            'url': report['pdf_url'],
                            'stock_name': report['stock_name']
                        })
                        print(f"      ✅ 텍스트 추출 완료: {len(text_content):,}자")
                    else:
                        print(f"      ⚠️  텍스트 추출 실패")
                    
                    # PDF 파일 삭제
                    try:
                        os.remove(pdf_filename)
                    except:
                        pass
                    
                    # 짧은 지연
                    time.sleep(1)
                    
                except Exception as download_error:
                    print(f"      ❌ 다운로드 실패: {download_error}")
                    continue
            
            print(f"\n   ✅ 최종 {len(extracted_reports)}개 리포트 추출 완료")
            return extracted_reports
            
        except Exception as e:
            print(f"❌ 네이버 종목분석 리포트 검색 실패: {e}")
            return []
    
    def search_industry_reports(self, industry_keywords, max_reports=5):
        """
        네이버 금융에서 산업분석 리포트 검색 및 다운로드
        
        Args:
            industry_keywords: 검색할 산업 키워드 리스트 (예: ["반도체", "메모리"])
            max_reports: 최대 다운로드 수
            
        Returns:
            list: [{name, date, content, url}, ...] 형식의 리스트
        """
        try:
            print(f"📊 네이버 금융에서 산업분석 리포트 검색 중...")
            print(f"   🔍 검색 키워드: {industry_keywords}")
            
            # 키워드가 문자열이면 리스트로 변환
            if isinstance(industry_keywords, str):
                industry_keywords = [kw.strip() for kw in industry_keywords.split(',')]
            
            # 검색어 리스트로 사용
            search_variations = industry_keywords
            
            # 네이버 증권 산업분석 리포트 검색 URL
            base_url = "https://finance.naver.com/research/industry_list.naver"
            
            # 모든 검색어로 검색 시도
            all_reports = []
            seen_urls = set()  # 중복 제거용
            
            for variation_idx, search_term in enumerate(search_variations):
                print(f"\n   🔍 [{variation_idx + 1}/{len(search_variations)}] 검색어 '{search_term}'로 검색 중...")
                
                try:
                    # 검색어 EUC-KR 인코딩
                    keyword_euckr = search_term.encode('euc-kr')
                    encoded_keyword = quote(keyword_euckr)
                    
                    # URL 직접 구성
                    search_url = f"{base_url}?searchType=keyword&keyword={encoded_keyword}&brokerCode=&writeFromDate=&writeToDate=&upjong="
                    
                    print(f"      EUC-KR 인코딩: {encoded_keyword}")
                    
                    # 검색 페이지 로드
                    response = requests.get(search_url, headers=self.headers, timeout=30)
                    response.raise_for_status()
                    response.encoding = 'euc-kr'
                    
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # 첫 번째 검색어일 때만 HTML 디버깅 파일 저장
                    if variation_idx == 0:
                        debug_html_path = 'downloads/debug_industry_list.html'
                        os.makedirs('downloads', exist_ok=True)
                        with open(debug_html_path, 'w', encoding='utf-8') as f:
                            f.write(soup.prettify())
                        print(f"      🔍 HTML 저장됨: {debug_html_path}")
                    
                    # 테이블 찾기
                    table = soup.find('table', class_='type_1')
                    if not table:
                        tables = soup.find_all('table')
                        for t in tables:
                            rows = t.find_all('tr')
                            if len(rows) > 5:
                                table = t
                                break
                    
                    if not table:
                        print(f"      ⚠️  테이블을 찾을 수 없습니다")
                        continue
                    
                    rows = table.find_all('tr')
                    
                    # 헤더 분석 (첫 검색어일 때만)
                    if variation_idx == 0:
                        header_map = {}
                        if len(rows) > 0:
                            first_row = rows[0]
                            header_cells = first_row.find_all(['td', 'th'])
                            print(f"      📊 헤더: {len(header_cells)}개 열")
                            for idx, cell in enumerate(header_cells):
                                header_text = cell.get_text(strip=True)
                                header_map[header_text] = idx
                                print(f"         열 {idx}: '{header_text}'")
                        
                        title_idx = header_map.get('제목', 0)
                        broker_idx = header_map.get('증권사', 1)
                        pdf_idx = header_map.get('첨부', 2)
                        date_idx = header_map.get('작성일', 3)
                    
                    # 리포트 파싱
                    found_count = 0
                    for row in rows[1:]:  # 헤더 제외
                        try:
                            cells = row.find_all('td')
                            if len(cells) < 4:
                                continue
                            
                            # 제목 (링크)
                            title_cell = cells[title_idx]
                            title_link = title_cell.find('a')
                            if not title_link:
                                continue
                            
                            title = title_link.get_text(strip=True)
                            if not title:
                                continue
                            
                            # 증권사
                            broker = cells[broker_idx].get_text(strip=True) if len(cells) > broker_idx else "증권사"
                            
                            # PDF 첨부
                            pdf_cell = cells[pdf_idx]
                            pdf_link = pdf_cell.find('a')
                            if not pdf_link or not pdf_link.get('href'):
                                continue
                            
                            pdf_url = pdf_link.get('href')
                            
                            # 절대 URL로 변환
                            if not pdf_url.startswith('http'):
                                if pdf_url.startswith('//'):
                                    pdf_url = 'https:' + pdf_url
                                else:
                                    pdf_url = urljoin('https://stock.pstatic.net', pdf_url)
                            
                            # 중복 체크
                            if pdf_url in seen_urls:
                                continue
                            seen_urls.add(pdf_url)
                            
                            # 작성일
                            date = cells[date_idx].get_text(strip=True) if len(cells) > date_idx else "날짜미상"
                            
                            all_reports.append({
                                'title': title,
                                'broker': broker,
                                'date': date,
                                'pdf_url': pdf_url
                            })
                            
                            found_count += 1
                            
                        except Exception as row_error:
                            continue
                    
                    print(f"      ✓ {found_count}개 리포트 발견")
                    
                    # 충분한 리포트를 찾으면 중단
                    if len(all_reports) >= max_reports * 2:
                        print(f"      ℹ️  충분한 리포트 수집, 검색 중단")
                        break
                    
                    # 다음 검색어 사이에 짧은 지연
                    time.sleep(0.5)
                    
                except Exception as search_error:
                    print(f"      ⚠️  검색 실패: {search_error}")
                    continue
            
            if not all_reports:
                print(f"\n   ⚠️  '{company_name}'에 대한 산업분석 리포트를 찾을 수 없습니다.")
                return []
            
            # 날짜 기준으로 정렬 (최신순)
            def parse_date(date_str):
                """YY.MM.DD 형식을 정렬 가능한 값으로 변환"""
                try:
                    if not date_str or date_str == "날짜미상":
                        return "00.00.00"
                    return date_str
                except:
                    return "00.00.00"
            
            all_reports.sort(key=lambda x: parse_date(x['date']), reverse=True)
            
            # 상위 N개만 선택
            selected_reports = all_reports[:max_reports]
            
            print(f"\n   ✅ 총 {len(all_reports)}개 리포트 발견 (중복 제거 후)")
            print(f"   📋 선정된 리포트 (최신 {len(selected_reports)}개):")
            for idx, report in enumerate(selected_reports, 1):
                print(f"      [{idx}] {report['title']}")
                print(f"          증권사: {report['broker']}, 날짜: {report['date']}")
                print(f"          PDF: {report['pdf_url'][:80]}...")
            print()
            
            # PDF 다운로드 및 텍스트 추출
            extracted_reports = []
            
            for i, report in enumerate(selected_reports, 1):
                try:
                    print(f"\n   [{i}/{len(selected_reports)}] PDF 다운로드 중: {report['title'][:50]}...")
                    
                    # PDF 다운로드
                    pdf_response = requests.get(report['pdf_url'], headers=self.headers, timeout=60)
                    pdf_response.raise_for_status()
                    
                    # 임시 PDF 파일 저장
                    pdf_filename = f"downloads/naver_industry_{i}_{int(time.time())}.pdf"
                    os.makedirs('downloads', exist_ok=True)
                    
                    with open(pdf_filename, 'wb') as f:
                        f.write(pdf_response.content)
                    
                    print(f"      💾 PDF 저장: {len(pdf_response.content):,} bytes")
                    
                    # 텍스트 추출
                    text_content = self._extract_text_from_pdf(pdf_filename)
                    
                    if text_content:
                        extracted_reports.append({
                            'name': f"[{report['broker']}] {report['title']}",
                            'date': report['date'],
                            'content': text_content,
                            'url': report['pdf_url']
                        })
                        print(f"      ✅ 텍스트 추출 완료: {len(text_content):,}자")
                    else:
                        print(f"      ⚠️  텍스트 추출 실패")
                    
                    # PDF 파일 삭제
                    try:
                        os.remove(pdf_filename)
                    except:
                        pass
                    
                    # 짧은 지연
                    time.sleep(1)
                    
                except Exception as download_error:
                    print(f"      ❌ 다운로드 실패: {download_error}")
                    continue
            
            print(f"\n   ✅ 최종 {len(extracted_reports)}개 리포트 추출 완료")
            return extracted_reports
            
        except Exception as e:
            print(f"❌ 네이버 산업분석 리포트 검색 실패: {e}")
            return []

