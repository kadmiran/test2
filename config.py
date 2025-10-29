#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration Management
모든 API 키와 설정을 한 곳에서 관리하는 클래스
"""

import os
from typing import Optional


class Config:
    """
    애플리케이션 설정 관리 클래스
    
    환경 변수 우선순위:
    1. 환경 변수 (os.environ)
    2. 클래스 기본값
    
    사용 예시:
        config = Config()
        dart_key = config.DART_API_KEY
        gemini_key = config.GEMINI_API_KEY
    """
    
    # ============================================
    # API Keys
    # ============================================
    
    # DART API Key (금융감독원 전자공시)
    DART_API_KEY: str = os.getenv(
        'DART_API_KEY',
        '65684cef96753157d5488a7c934ee97d2863bcf3'  # 기본값
    )
    
    # Gemini API Key (Google AI)
    GEMINI_API_KEY: str = os.getenv(
        'GEMINI_API_KEY',
        'AIzaSyB_0WAaZenacmpSLoty2YyDXr32LW_NSNw'  # 기본값
    )
    
    # Friendli AI (Midm) Settings
    FRIENDLI_TOKEN: str = os.getenv(
        'FRIENDLI_TOKEN',
        'flp_QXk0SAkG40tSgnB0wWN76zPYheDkXMiooz8MFs1YC6x34'
    )
    FRIENDLI_BASE_URL: str = os.getenv(
        'FRIENDLI_BASE_URL',
        'https://api.friendli.ai/dedicated/v1'
    )
    FRIENDLI_ENDPOINT_ID: str = os.getenv(
        'FRIENDLI_ENDPOINT_ID',
        'depu7a0f8bsrscw'
    )
    
    # Perplexity AI Settings
    PERPLEXITY_API_KEY: str = os.getenv(
        'PERPLEXITY_API_KEY',
        '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'
    )
    
    
    # ============================================
    # LLM Orchestrator Settings
    # ============================================
    
    # 기본 LLM Provider
    DEFAULT_LLM_PROVIDER: str = 'perplexity'  # Perplexity 사용 (웹 검색 지원)
    
    # 작업별 LLM 라우팅 (task_type -> provider_name)
    LLM_TASK_ROUTING: dict = {
        'query_analysis': 'perplexity',     # 질문 분석은 Perplexity 사용 (웹 검색 지원)
        'long_context_analysis': 'gemini',  # 긴 맥락 분석은 Gemini 사용
        'name_variation': 'perplexity',     # 검색어 제안은 Perplexity 사용 (Midm 서버 다운)
    }
    
    # ============================================
    # DART API Settings
    # ============================================
    
    # DART API Base URL
    DART_BASE_URL: str = "https://opendart.fss.or.kr/api"
    
    # DART API Endpoints
    DART_CORP_CODE_URL: str = f"{DART_BASE_URL}/corpCode.xml"
    DART_LIST_URL: str = f"{DART_BASE_URL}/list.json"
    DART_DOCUMENT_URL: str = f"{DART_BASE_URL}/document.xml"
    DART_COMPANY_URL: str = f"{DART_BASE_URL}/company.json"
    
    # ============================================
    # Gemini AI Settings
    # ============================================
    
    # Gemini Model Name (자동으로 사용 가능한 모델 선택)
    GEMINI_MODEL_CANDIDATES: list = [
        'gemini-2.5-pro-preview-03-25',
        'gemini-pro',
        'gemini-1.5-pro',
        'gemini-1.5-flash',
    ]
    
    
    # ============================================
    # Vector Store Settings (VectorDB)
    # ============================================
    
    # VectorDB 저장 디렉토리
    VECTOR_DB_DIR: str = os.getenv('VECTOR_DB_DIR', 'vector_db')
    
    # VectorDB 메타데이터 파일명
    VECTOR_DB_METADATA_FILE: str = 'metadata.json'
    
    # 임베딩 모델 (한국어 특화)
    EMBEDDING_MODEL: str = 'jhgan/ko-sroberta-multitask'
    
    # 텍스트 청크 크기
    CHUNK_SIZE: int = 1000
    
    # 텍스트 청크 오버랩
    CHUNK_OVERLAP: int = 200
    
    # ============================================
    # Naver Finance Crawler Settings
    # ============================================
    
    # 네이버 금융 Base URL
    NAVER_FINANCE_BASE_URL: str = "https://finance.naver.com"
    
    # 종목분석 리포트 URL
    NAVER_COMPANY_REPORT_URL: str = f"{NAVER_FINANCE_BASE_URL}/research/company_list.naver"
    
    # 산업분석 리포트 URL
    NAVER_INDUSTRY_REPORT_URL: str = f"{NAVER_FINANCE_BASE_URL}/research/industry_list.naver"
    
    # 크롤링 User-Agent
    CRAWLER_USER_AGENT: str = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    
    
    # ============================================
    # Download Settings
    # ============================================
    
    # 다운로드 폴더
    DOWNLOAD_DIR: str = 'downloads'
    
    
    # ============================================
    # Report Settings
    # ============================================
    
    # 메인 보고서 최대 문자 수
    MAX_MAIN_REPORT_CHARS: int = 500_000
    
    # 추가 보고서 개수
    MAX_ADDITIONAL_REPORTS: int = 5
    
    # 증권사 종목분석 리포트 개수
    MAX_COMPANY_REPORTS: int = 3
    
    # 증권사 산업분석 리포트 개수
    MAX_INDUSTRY_REPORTS: int = 2
    
    # 추가 보고서 최대 문자 수
    MAX_ADDITIONAL_REPORT_CHARS: int = 200_000
    
    
    # ============================================
    # Flask Server Settings
    # ============================================
    
    # Flask Debug Mode
    FLASK_DEBUG: bool = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Flask Host
    FLASK_HOST: str = os.getenv('FLASK_HOST', '0.0.0.0')
    
    # Flask Port
    FLASK_PORT: int = int(os.getenv('FLASK_PORT', '5000'))
    
    
    # ============================================
    # Supported Report Types (DART)
    # ============================================
    
    REPORT_TYPES: dict = {
        'A001': '사업보고서',
        'A002': '반기보고서',
        'A003': '분기보고서',
        'B001': '주요사항보고서',
        'C001': '자율공시',
        'D001': '조회공시',
        'D002': '수시공시',
        'E001': '공정공시',
        'F001': '주주총회소집공고',
        'G001': '증권발행실적',
    }
    
    # ============================================
    # Helper Methods
    # ============================================
    
    @classmethod
    def get_dart_api_key(cls) -> str:
        """DART API 키 반환"""
        return cls.DART_API_KEY
    
    @classmethod
    def get_gemini_api_key(cls) -> str:
        """Gemini API 키 반환"""
        return cls.GEMINI_API_KEY
    
    @classmethod
    def get_perplexity_api_key(cls) -> str:
        """Perplexity API 키 반환"""
        return cls.PERPLEXITY_API_KEY
    
    @classmethod
    def get_vector_db_path(cls) -> str:
        """VectorDB 경로 반환"""
        return cls.VECTOR_DB_DIR
    
    @classmethod
    def get_download_path(cls) -> str:
        """다운로드 폴더 경로 반환"""
        return cls.DOWNLOAD_DIR
    
    @classmethod
    def validate_api_keys(cls) -> bool:
        """
        API 키 유효성 검증
        
        Returns:
            bool: 모든 키가 설정되어 있으면 True
        """
        if not cls.DART_API_KEY or cls.DART_API_KEY == '':
            print("❌ DART API 키가 설정되지 않았습니다.")
            return False
        
        if not cls.GEMINI_API_KEY or cls.GEMINI_API_KEY == '':
            print("❌ Gemini API 키가 설정되지 않았습니다.")
            return False
        
        if not cls.PERPLEXITY_API_KEY or cls.PERPLEXITY_API_KEY == '':
            print("❌ Perplexity API 키가 설정되지 않았습니다.")
            return False
        
        return True
    


# 설정 인스턴스 생성 (싱글톤 패턴)
config = Config()



