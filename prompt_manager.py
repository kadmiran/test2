#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
프롬프트 관리자
프롬프트를 JSON 파일에서 로드하고 관리합니다.
"""

import json
import os
from typing import Dict, List, Optional

class PromptManager:
    """프롬프트 템플릿 관리 클래스"""
    
    def __init__(self, prompts_file: str = "prompts.json"):
        """
        초기화
        
        Args:
            prompts_file: 프롬프트 JSON 파일 경로
        """
        self.prompts_file = prompts_file
        self.prompts: Dict = {}
        self.load_prompts()
    
    def load_prompts(self):
        """JSON 파일에서 프롬프트 로드"""
        try:
            if not os.path.exists(self.prompts_file):
                raise FileNotFoundError(f"프롬프트 파일을 찾을 수 없습니다: {self.prompts_file}")
            
            with open(self.prompts_file, 'r', encoding='utf-8') as f:
                self.prompts = json.load(f)
            
            print(f"✅ 프롬프트 로드 완료: {len(self.prompts)}개")
        except Exception as e:
            print(f"❌ 프롬프트 로드 실패: {e}")
            raise
    
    def get_prompt(self, prompt_name: str, **kwargs) -> str:
        """
        프롬프트 템플릿을 가져와서 변수를 채워 반환
        
        Args:
            prompt_name: 프롬프트 이름
            **kwargs: 템플릿 변수들
            
        Returns:
            str: 완성된 프롬프트
        """
        if prompt_name not in self.prompts:
            raise ValueError(f"프롬프트를 찾을 수 없습니다: {prompt_name}")
        
        prompt_data = self.prompts[prompt_name]
        template = prompt_data.get('template', '')
        required_vars = prompt_data.get('variables', [])
        
        # 필수 변수 확인
        missing_vars = [var for var in required_vars if var not in kwargs]
        if missing_vars:
            raise ValueError(f"필수 변수가 누락되었습니다: {missing_vars}")
        
        # 템플릿 변수 채우기
        try:
            return template.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"템플릿 변수 오류: {e}")
    
    def get_description(self, prompt_name: str) -> str:
        """
        프롬프트 설명 반환
        
        Args:
            prompt_name: 프롬프트 이름
            
        Returns:
            str: 프롬프트 설명
        """
        if prompt_name not in self.prompts:
            return ""
        return self.prompts[prompt_name].get('description', '')
    
    def get_required_variables(self, prompt_name: str) -> List[str]:
        """
        프롬프트에 필요한 변수 목록 반환
        
        Args:
            prompt_name: 프롬프트 이름
            
        Returns:
            List[str]: 필수 변수 목록
        """
        if prompt_name not in self.prompts:
            return []
        return self.prompts[prompt_name].get('variables', [])
    
    def list_prompts(self) -> List[str]:
        """사용 가능한 프롬프트 목록 반환"""
        return list(self.prompts.keys())
    
    def reload(self):
        """프롬프트 파일 다시 로드"""
        self.load_prompts()


# 전역 인스턴스 (싱글톤 패턴)
_prompt_manager_instance: Optional[PromptManager] = None

def get_prompt_manager() -> PromptManager:
    """프롬프트 매니저 싱글톤 인스턴스 반환"""
    global _prompt_manager_instance
    if _prompt_manager_instance is None:
        _prompt_manager_instance = PromptManager()
    return _prompt_manager_instance

