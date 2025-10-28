#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
벡터 데이터베이스 관리
FAISS와 LangChain을 사용하여 공시보고서를 벡터DB에 저장하고 검색
"""

import os
import json
import pickle
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.docstore.document import Document
from config import config


class VectorStore:
    """벡터 데이터베이스 관리 클래스"""
    
    def __init__(self, persist_directory: Optional[str] = None):
        """
        벡터 데이터베이스 초기화
        
        Args:
            persist_directory: 벡터DB 저장 디렉토리 (None이면 config에서 가져옴)
        """
        self.persist_directory = persist_directory or config.VECTOR_DB_DIR
        self.metadata_path = os.path.join(self.persist_directory, config.VECTOR_DB_METADATA_FILE)
        
        # 디렉토리 생성
        os.makedirs(self.persist_directory, exist_ok=True)
        
        print("🔧 벡터 임베딩 모델 초기화 중...")
        # 한국어 지원 임베딩 모델 사용 (config에서 설정)
        self.embeddings = HuggingFaceEmbeddings(
            model_name=config.EMBEDDING_MODEL,
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        print("✅ 임베딩 모델 초기화 완료")
        
        # 텍스트 분할기 설정 (config에서 설정)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.CHUNK_SIZE,
            chunk_overlap=config.CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", "。", ".", " ", ""]
        )
        
        # FAISS 벡터스토어 로드 또는 생성
        self.vectorstore = self._load_or_create_vectorstore()
        
        # 메타데이터 로드
        self.metadata = self._load_metadata()
        
    def _load_or_create_vectorstore(self) -> FAISS:
        """FAISS 벡터스토어 로드 또는 생성"""
        index_path = os.path.join(self.persist_directory, "index.faiss")
        
        if os.path.exists(index_path):
            print(f"📂 기존 VectorDB 로드 중: {index_path}")
            try:
                vectorstore = FAISS.load_local(
                    self.persist_directory,
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )
                print(f"✅ VectorDB 로드 완료")
                return vectorstore
            except Exception as e:
                print(f"⚠️  VectorDB 로드 실패: {e}")
                print("   새로운 VectorDB를 생성합니다.")
        
        # 새로운 벡터스토어 생성 (빈 문서로 초기화)
        print("🆕 새로운 VectorDB 생성 중...")
        initial_docs = [Document(page_content="초기 문서", metadata={"type": "init"})]
        vectorstore = FAISS.from_documents(initial_docs, self.embeddings)
        print("✅ VectorDB 생성 완료")
        return vectorstore
    
    def _load_metadata(self) -> Dict:
        """메타데이터 로드"""
        if os.path.exists(self.metadata_path):
            try:
                with open(self.metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                print(f"📋 메타데이터 로드: {len(metadata)}개 보고서")
                return metadata
            except Exception as e:
                print(f"⚠️  메타데이터 로드 실패: {e}")
                return {}
        return {}
    
    def _save_metadata(self):
        """메타데이터 저장"""
        try:
            with open(self.metadata_path, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, ensure_ascii=False, indent=2)
            print(f"💾 메타데이터 저장 완료: {len(self.metadata)}개 보고서")
        except Exception as e:
            print(f"⚠️  메타데이터 저장 실패: {e}")
    
    def _save_vectorstore(self):
        """벡터스토어 저장"""
        try:
            self.vectorstore.save_local(self.persist_directory)
            print(f"💾 VectorDB 저장 완료: {self.persist_directory}")
        except Exception as e:
            print(f"⚠️  VectorDB 저장 실패: {e}")
    
    def get_naver_reports_from_cache(self, company_name: str = None, report_type: str = "NAVER_COMPANY", industry_keywords: List[str] = None) -> List[Dict]:
        """
        VectorDB에서 증권사 리포트 조회 (캐싱)
        
        Args:
            company_name: 회사명 (종목분석용)
            report_type: "NAVER_COMPANY" (종목분석) 또는 "NAVER_INDUSTRY" (산업분석)
            industry_keywords: 산업 키워드 리스트 (산업분석용)
            
        Returns:
            list: [{name, date, content, url}, ...] 형식의 리스트
        """
        if report_type == "NAVER_COMPANY":
            print(f"🔍 VectorDB에서 {company_name}의 종목분석 리포트 확인 중...")
        else:
            print(f"🔍 VectorDB에서 산업분석 리포트 확인 중... (키워드: {industry_keywords})")
        
        try:
            cached_reports = []
            
            if report_type == "NAVER_COMPANY":
                # 종목분석: 회사명으로 검색
                for rcept_no, meta in self.metadata.items():
                    if rcept_no.startswith(report_type) and meta.get('company_name') == company_name:
                        cached_reports.append({
                            'name': meta.get('report_name', ''),
                            'date': meta.get('date', ''),
                            'content': meta.get('full_content', ''),
                            'url': rcept_no,
                            'rcept_no': rcept_no
                        })
            
            elif report_type == "NAVER_INDUSTRY" and industry_keywords:
                # 산업분석: 산업 키워드로 검색
                for rcept_no, meta in self.metadata.items():
                    if not rcept_no.startswith(report_type):
                        continue
                    
                    report_name = meta.get('report_name', '')
                    industry_tags = meta.get('industry_keywords', [])
                    
                    # 리포트명이나 산업 태그에 키워드가 포함되어 있는지 확인
                    matched = False
                    for keyword in industry_keywords:
                        if keyword.lower() in report_name.lower():
                            matched = True
                            break
                        if industry_tags and keyword in industry_tags:
                            matched = True
                            break
                    
                    if matched:
                        cached_reports.append({
                            'name': meta.get('report_name', ''),
                            'date': meta.get('date', ''),
                            'content': meta.get('full_content', ''),
                            'url': rcept_no,
                            'rcept_no': rcept_no
                        })
            
            if cached_reports:
                # 날짜 기준으로 정렬 (최신순)
                def parse_date(date_str):
                    try:
                        if not date_str or date_str == "날짜미상":
                            return "00.00.00"
                        return date_str
                    except:
                        return "00.00.00"
                
                cached_reports.sort(key=lambda x: parse_date(x['date']), reverse=True)
                
                print(f"   ✅ VectorDB에서 {len(cached_reports)}개 리포트 발견")
                for idx, report in enumerate(cached_reports[:5], 1):
                    print(f"      [{idx}] {report['name']} ({report['date']})")
                
                return cached_reports
            else:
                if report_type == "NAVER_INDUSTRY":
                    print(f"   ℹ️  VectorDB에 산업 키워드 '{', '.join(industry_keywords)}'와 관련된 리포트 없음")
                else:
                    print(f"   ℹ️  VectorDB에 캐시된 리포트 없음")
                return []
                
        except Exception as e:
            print(f"   ⚠️  VectorDB 조회 실패: {e}")
            return []
    
    def check_report_exists(self, rcept_no: str) -> bool:
        """
        보고서가 벡터DB에 존재하는지 확인
        
        Args:
            rcept_no: 접수번호
            
        Returns:
            bool: 존재 여부
        """
        exists = rcept_no in self.metadata
        if exists:
            report_info = self.metadata[rcept_no]
            print(f"✅ VectorDB에 보고서 존재: {report_info.get('report_name')} ({report_info.get('date')})")
        return exists
    
    def get_report_from_cache(self, rcept_no: str) -> Optional[str]:
        """
        벡터DB에서 보고서 전체 내용 가져오기
        
        Args:
            rcept_no: 접수번호
            
        Returns:
            str: 보고서 내용 (없으면 None)
        """
        if rcept_no not in self.metadata:
            return None
        
        report_info = self.metadata[rcept_no]
        print(f"📖 캐시에서 보고서 로드: {report_info.get('report_name')}")
        
        # 저장된 원본 텍스트 반환
        return report_info.get('full_content')
    
    def add_report(
        self,
        rcept_no: str,
        report_name: str,
        company_name: str,
        report_date: str,
        content: str,
        report_type: str = "공시보고서",
        industry_keywords: List[str] = None
    ):
        """
        보고서를 벡터DB에 추가
        
        Args:
            rcept_no: 접수번호
            report_name: 보고서명
            company_name: 회사명
            report_date: 보고서 날짜
            content: 보고서 내용 (Markdown 형식)
            report_type: 보고서 유형
        """
        print(f"📝 VectorDB에 보고서 추가 중: {report_name}")
        print(f"   회사: {company_name}")
        print(f"   날짜: {report_date}")
        print(f"   크기: {len(content):,}자")
        
        try:
            # 텍스트를 청크로 분할
            print("   🔪 텍스트 청크 분할 중...")
            chunks = self.text_splitter.split_text(content)
            print(f"   ✅ {len(chunks)}개 청크 생성됨")
            
            # Document 객체 생성
            documents = []
            for i, chunk in enumerate(chunks):
                doc = Document(
                    page_content=chunk,
                    metadata={
                        "rcept_no": rcept_no,
                        "report_name": report_name,
                        "company_name": company_name,
                        "report_date": report_date,
                        "report_type": report_type,
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        "added_at": datetime.now().isoformat()
                    }
                )
                documents.append(doc)
            
            # 벡터스토어에 추가
            print("   🔄 벡터 임베딩 생성 및 FAISS 인덱스에 추가 중...")
            self.vectorstore.add_documents(documents)
            print("   ✅ 벡터 임베딩 완료")
            
            # 메타데이터 저장
            self.metadata[rcept_no] = {
                "report_name": report_name,
                "company_name": company_name,
                "date": report_date,
                "report_type": report_type,
                "num_chunks": len(chunks),
                "content_length": len(content),
                "full_content": content,  # 원본 텍스트도 저장
                "industry_keywords": industry_keywords if industry_keywords else [],  # 산업 키워드
                "added_at": datetime.now().isoformat()
            }
            
            # 디스크에 저장
            self._save_vectorstore()
            self._save_metadata()
            
            print(f"✅ VectorDB 추가 완료: {report_name}")
            
        except Exception as e:
            print(f"❌ VectorDB 추가 실패: {e}")
            import traceback
            traceback.print_exc()
    
    def search_similar_reports(
        self,
        query: str,
        company_name: Optional[str] = None,
        k: int = 5
    ) -> List[Tuple[Document, float]]:
        """
        유사한 보고서 검색
        
        Args:
            query: 검색 쿼리
            company_name: 회사명 (선택사항, 지정하면 해당 회사로 필터링)
            k: 반환할 문서 수
            
        Returns:
            List[Tuple[Document, float]]: (문서, 유사도 점수) 리스트
        """
        print(f"🔍 VectorDB 검색 중: '{query[:50]}...'")
        if company_name:
            print(f"   회사 필터: {company_name}")
        
        try:
            # 유사도 검색
            results = self.vectorstore.similarity_search_with_score(query, k=k*3)  # 필터링 고려해서 더 많이 가져옴
            
            # 회사명 필터링
            if company_name:
                filtered_results = []
                for doc, score in results:
                    if doc.metadata.get('company_name', '').upper() == company_name.upper():
                        filtered_results.append((doc, score))
                results = filtered_results[:k]
            else:
                results = results[:k]
            
            print(f"✅ {len(results)}개 결과 발견")
            
            # 결과 출력
            for i, (doc, score) in enumerate(results, 1):
                meta = doc.metadata
                print(f"   [{i}] {meta.get('report_name')} ({meta.get('report_date')})")
                print(f"       유사도: {score:.4f}, 청크: {meta.get('chunk_index')}/{meta.get('total_chunks')}")
            
            return results
            
        except Exception as e:
            print(f"❌ VectorDB 검색 실패: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_all_reports_for_company(self, company_name: str) -> List[Dict]:
        """
        특정 회사의 모든 보고서 목록 가져오기
        
        Args:
            company_name: 회사명
            
        Returns:
            List[Dict]: 보고서 정보 리스트
        """
        reports = []
        for rcept_no, info in self.metadata.items():
            if info.get('company_name', '').upper() == company_name.upper():
                reports.append({
                    'rcept_no': rcept_no,
                    'report_name': info.get('report_name'),
                    'date': info.get('date'),
                    'report_type': info.get('report_type'),
                    'num_chunks': info.get('num_chunks'),
                    'added_at': info.get('added_at')
                })
        
        # 날짜 순으로 정렬 (최신순)
        reports.sort(key=lambda x: x.get('date', ''), reverse=True)
        
        print(f"📊 {company_name}의 보고서 {len(reports)}개 발견")
        return reports
    
    def delete_report(self, rcept_no: str):
        """
        보고서 삭제 (메타데이터만 삭제, 벡터는 재구축 필요)
        
        Args:
            rcept_no: 접수번호
        """
        if rcept_no in self.metadata:
            report_name = self.metadata[rcept_no].get('report_name')
            del self.metadata[rcept_no]
            self._save_metadata()
            print(f"🗑️  보고서 삭제 완료: {report_name}")
            print("   ⚠️  주의: 벡터 인덱스는 재구축이 필요합니다.")
        else:
            print(f"❌ 보고서를 찾을 수 없음: {rcept_no}")
    
    def rebuild_index(self):
        """
        벡터 인덱스 재구축 (메타데이터 기반)
        """
        print("🔄 벡터 인덱스 재구축 중...")
        
        all_documents = []
        for rcept_no, info in self.metadata.items():
            content = info.get('full_content', '')
            if not content:
                continue
            
            chunks = self.text_splitter.split_text(content)
            
            for i, chunk in enumerate(chunks):
                doc = Document(
                    page_content=chunk,
                    metadata={
                        "rcept_no": rcept_no,
                        "report_name": info.get('report_name'),
                        "company_name": info.get('company_name'),
                        "report_date": info.get('date'),
                        "report_type": info.get('report_type'),
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        "added_at": info.get('added_at')
                    }
                )
                all_documents.append(doc)
        
        if all_documents:
            print(f"   총 {len(all_documents)}개 청크 재구축 중...")
            self.vectorstore = FAISS.from_documents(all_documents, self.embeddings)
            self._save_vectorstore()
            print("✅ 벡터 인덱스 재구축 완료")
        else:
            print("⚠️  재구축할 문서가 없습니다.")
    
    def get_stats(self) -> Dict:
        """
        벡터DB 통계 정보
        
        Returns:
            Dict: 통계 정보
        """
        total_reports = len(self.metadata)
        total_chunks = sum(info.get('num_chunks', 0) for info in self.metadata.values())
        total_size = sum(info.get('content_length', 0) for info in self.metadata.values())
        
        companies = set(info.get('company_name') for info in self.metadata.values())
        
        stats = {
            "total_reports": total_reports,
            "total_chunks": total_chunks,
            "total_size_chars": total_size,
            "num_companies": len(companies),
            "companies": list(companies),
            "storage_path": self.persist_directory
        }
        
        return stats
    
    def print_stats(self):
        """통계 정보 출력"""
        stats = self.get_stats()
        
        print("\n" + "="*60)
        print("📊 VectorDB 통계")
        print("="*60)
        print(f"총 보고서 수: {stats['total_reports']}개")
        print(f"총 청크 수: {stats['total_chunks']}개")
        print(f"총 데이터 크기: {stats['total_size_chars']:,}자")
        print(f"회사 수: {stats['num_companies']}개")
        if stats['companies']:
            print(f"회사 목록: {', '.join(stats['companies'])}")
        print(f"저장 경로: {stats['storage_path']}")
        print("="*60 + "\n")
    
    def reset_database(self) -> bool:
        """
        VectorDB 완전 초기화 (모든 데이터 삭제)
        
        Returns:
            bool: 성공 여부
        """
        try:
            print(f"🗑️  VectorDB 초기화 중...")
            
            # 1. 메타데이터 초기화
            self.metadata = {}
            self._save_metadata()
            print(f"   ✅ 메타데이터 초기화 완료")
            
            # 2. 저장된 파일들 삭제
            faiss_index_path = os.path.join(self.persist_directory, "index.faiss")
            faiss_pkl_path = os.path.join(self.persist_directory, "index.pkl")
            
            if os.path.exists(faiss_index_path):
                os.remove(faiss_index_path)
                print(f"   ✅ FAISS 인덱스 파일 삭제")
            
            if os.path.exists(faiss_pkl_path):
                os.remove(faiss_pkl_path)
                print(f"   ✅ FAISS PKL 파일 삭제")
            
            # 3. VectorStore 재초기화
            self.vectorstore = self._load_or_create_vectorstore()
            
            print(f"✅ VectorDB 초기화 완료!")
            return True
            
        except Exception as e:
            print(f"❌ VectorDB 초기화 실패: {e}")
            return False


if __name__ == "__main__":
    # 테스트 코드
    print("🧪 VectorStore 테스트 시작\n")
    
    # VectorStore 초기화
    vs = VectorStore()
    
    # 통계 출력
    vs.print_stats()
    
    print("✅ VectorStore 테스트 완료")

