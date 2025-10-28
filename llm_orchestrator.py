#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM Orchestrator
다양한 LLM Provider를 통합 관리하고, 작업 유형에 따라 적절한 LLM을 자동 선택
"""

# Windows 콘솔 인코딩 문제 해결 (이모지 출력용)
import sys
import io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from abc import ABC, abstractmethod
from typing import Optional, Dict
import google.generativeai as genai
import requests
import json


class LLMProvider(ABC):
    """LLM Provider 추상 클래스"""
    
    @abstractmethod
    def generate_content(self, prompt: str, **kwargs) -> str:
        """텍스트 생성"""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Provider 이름 반환"""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> dict:
        """Provider 능력 반환 (context_window, cost, speed 등)"""
        pass


class GeminiProvider(LLMProvider):
    """Google Gemini AI Provider"""
    
    def __init__(self, api_key: str, model_candidates: list = None):
        """
        Gemini Provider 초기화
        
        Args:
            api_key: Gemini API 키
            model_candidates: 시도할 모델 리스트
        """
        genai.configure(api_key=api_key)
        self.model = self._initialize_model(model_candidates or ['gemini-2.5-pro-preview-03-25', 'gemini-pro'])
    
    def _initialize_model(self, candidates):
        """사용 가능한 Gemini 모델 자동 선택"""
        print("🔍 Gemini API 사용 가능한 모델 확인 중...")
        
        try:
            # 사용 가능한 모델 목록 가져오기
            available_models = []
            for model in genai.list_models():
                if 'generateContent' in model.supported_generation_methods:
                    available_models.append(model.name)
                    print(f"   - {model.name}")
            
            if available_models:
                selected_model = available_models[0]
                model_obj = genai.GenerativeModel(selected_model)
                print(f"✅ Gemini 모델 설정 완료: {selected_model}")
                return model_obj
        except Exception as e:
            print(f"⚠️  모델 목록 조회 실패: {e}")
            print("   기본 모델로 시도합니다...")
        
        # 기본 모델들 시도
        for model_name in candidates:
            try:
                test_model = genai.GenerativeModel(model_name)
                # 실제로 작동하는지 테스트
                test_response = test_model.generate_content("test")
                print(f"✅ Gemini 모델 설정 완료: {model_name}")
                return test_model
            except Exception as model_error:
                print(f"   ❌ {model_name} 실패: {str(model_error)[:100]}")
                continue
        
        # 모든 시도 실패 시 gemini-pro로 폴백
        print("⚠️  모든 모델 시도 실패. gemini-pro를 기본값으로 사용합니다.")
        return genai.GenerativeModel('gemini-pro')
    
    def generate_content(self, prompt: str, **kwargs) -> str:
        """텍스트 생성"""
        response = self.model.generate_content(prompt)
        return response.text
    
    def get_name(self) -> str:
        """Provider 이름 반환"""
        return "gemini"
    
    def get_capabilities(self) -> dict:
        """Provider 능력 반환"""
        return {
            'context_window': 1_000_000,
            'supports_long_context': True,
            'supports_korean': True,
            'cost': 'medium',
            'speed': 'fast'
        }


class MidmProvider(LLMProvider):
    """Friendli AI (Midm) Provider"""
    
    def __init__(self, api_token: str, base_url: str, endpoint_id: str):
        """
        Midm Provider 초기화
        
        Args:
            api_token: Friendli API Token
            base_url: Friendli API Base URL (https://api.friendli.ai/dedicated/v1)
            endpoint_id: 배포된 엔드포인트 ID
        
        Reference:
            https://friendli.ai/docs/guides/dedicated_endpoints/quickstart
        """
        self.api_token = api_token
        self.base_url = base_url.rstrip('/')
        self.endpoint_id = endpoint_id
        self.api_url = f"{self.base_url}/chat/completions"
        
        print(f"🔧 Midm Provider 초기화 완료")
        print(f"   Endpoint ID: {endpoint_id}")
        print(f"   API URL: {self.api_url}")
    
    def generate_content(self, prompt: str, **kwargs) -> str:
        """
        텍스트 생성
        
        Args:
            prompt: 생성할 프롬프트
            **kwargs: 추가 파라미터 (max_tokens, temperature, top_p 등)
        
        Returns:
            생성된 텍스트
        """
        try:
            # 가이드에 나온 형식: Authorization Bearer 토큰
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_token}"
            }
            
            # 가이드에 나온 페이로드 형식 그대로
            payload = {
                "model": self.endpoint_id,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": kwargs.get('max_tokens', 512),
                "temperature": kwargs.get('temperature', 0.7),
                "top_p": kwargs.get('top_p', 0.9),
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code != 200:
                error_msg = f"HTTP {response.status_code}"
                try:
                    error_detail = response.json()
                    error_msg += f": {error_detail}"
                except:
                    error_msg += f": {response.text[:200]}"
                print(f"   ❌ {error_msg}")
            
            response.raise_for_status()
            
            result = response.json()
            
            # 가이드의 응답 형식: choices[0].message.content
            if 'choices' in result and len(result['choices']) > 0:
                message = result['choices'][0].get('message', {})
                content = message.get('content', '')
                if content:
                    return content.strip()
            
            raise ValueError(f"예상치 못한 응답 형식: {result}")
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Midm API 요청 오류: {e}"
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    error_msg += f"\n   상세: {error_detail}"
                except:
                    error_msg += f"\n   응답: {e.response.text[:300]}"
            print(f"❌ {error_msg}")
            raise
        except Exception as e:
            print(f"❌ Midm API 처리 오류: {e}")
            raise
    
    def get_name(self) -> str:
        """Provider 이름 반환"""
        return "midm"
    
    def get_capabilities(self) -> dict:
        """Provider 능력 반환"""
        return {
            'context_window': 4096,  # Friendli AI 기본값
            'supports_long_context': False,
            'supports_korean': True,
            'cost': 'low',
            'speed': 'very_fast'  # Dedicated endpoint라 빠름
        }


class LLMOrchestrator:
    """LLM Provider 관리 및 자동 선택"""
    
    def __init__(self):
        """Orchestrator 초기화"""
        self.providers: Dict[str, LLMProvider] = {}
        self.default_provider: Optional[str] = None
        self.task_routing: Dict[str, str] = {}
    
    def register_provider(self, provider: LLMProvider, is_default: bool = False):
        """
        Provider 등록
        
        Args:
            provider: LLMProvider 인스턴스
            is_default: 기본 Provider로 설정할지 여부
        """
        name = provider.get_name()
        self.providers[name] = provider
        print(f"✅ LLM Provider 등록: {name}")
        
        if is_default or self.default_provider is None:
            self.default_provider = name
            print(f"   📌 기본 Provider 설정: {name}")
    
    def set_task_routing(self, task_type: str, provider_name: str):
        """
        작업 유형별 Provider 라우팅 설정
        
        Args:
            task_type: 작업 유형 (예: 'query_analysis', 'long_context_analysis')
            provider_name: 사용할 Provider 이름
        """
        if provider_name not in self.providers:
            raise ValueError(f"Provider '{provider_name}' 미등록")
        self.task_routing[task_type] = provider_name
        print(f"   🔀 라우팅 설정: {task_type} → {provider_name}")
    
    def select_provider(self, task_type: Optional[str] = None) -> LLMProvider:
        """
        작업 유형에 따라 적절한 Provider 선택
        
        Args:
            task_type: 작업 유형 (선택사항)
            
        Returns:
            선택된 LLMProvider
        """
        # 1. 작업 유형별 라우팅이 설정되어 있으면 해당 Provider 사용
        if task_type and task_type in self.task_routing:
            provider_name = self.task_routing[task_type]
            print(f"   🔀 라우팅 적용: {task_type} → {provider_name}")
            return self.providers[provider_name]
        
        # 2. 작업 유형별 자동 선택 로직 (향후 확장)
        if task_type == 'long_context_analysis':
            # 긴 컨텍스트는 Gemini 우선
            for name, provider in self.providers.items():
                if provider.get_capabilities().get('supports_long_context'):
                    return provider
        
        elif task_type == 'quick_analysis':
            # 빠른 분석은 속도 우선 (향후: Claude-Haiku, GPT-3.5 등)
            pass
        
        # 3. 기본 Provider 사용
        if self.default_provider and self.default_provider in self.providers:
            print(f"   🔀 기본 Provider 사용: {self.default_provider}")
            return self.providers[self.default_provider]
        
        # 4. 아무 Provider라도 반환 (폴백)
        if self.providers:
            fallback_name = list(self.providers.keys())[0]
            print(f"   🔀 폴백 Provider 사용: {fallback_name}")
            return list(self.providers.values())[0]
        
        raise RuntimeError("등록된 LLM Provider가 없습니다.")
    
    def generate(self, prompt: str, task_type: Optional[str] = None, **kwargs) -> str:
        """
        텍스트 생성 (자동 Provider 선택)
        
        Args:
            prompt: 생성할 프롬프트
            task_type: 작업 유형 (선택사항)
            **kwargs: 추가 파라미터
            
        Returns:
            생성된 텍스트
        """
        provider = self.select_provider(task_type)
        print(f"🤖 사용 LLM: {provider.get_name()}")
        return provider.generate_content(prompt, **kwargs)
    
    def list_providers(self) -> list:
        """
        등록된 Provider 목록 반환
        
        Returns:
            Provider 정보 리스트
        """
        return [
            {
                'name': name,
                'capabilities': provider.get_capabilities(),
                'is_default': name == self.default_provider
            }
            for name, provider in self.providers.items()
        ]


# 향후 추가 가능한 Provider 예시:
"""
class OpenAIProvider(LLMProvider):
    '''OpenAI GPT Provider'''
    
    def __init__(self, api_key: str, model: str = "gpt-4"):
        import openai
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model
    
    def generate_content(self, prompt: str, **kwargs) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    
    def get_name(self) -> str:
        return "openai"
    
    def get_capabilities(self) -> dict:
        return {
            'context_window': 128_000,
            'supports_long_context': True,
            'supports_korean': True,
            'cost': 'high',
            'speed': 'medium'
        }


class ClaudeProvider(LLMProvider):
    '''Anthropic Claude Provider'''
    
    def __init__(self, api_key: str, model: str = "claude-3-opus-20240229"):
        import anthropic
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
    
    def generate_content(self, prompt: str, **kwargs) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    
    def get_name(self) -> str:
        return "claude"
    
    def get_capabilities(self) -> dict:
        return {
            'context_window': 200_000,
            'supports_long_context': True,
            'supports_korean': True,
            'cost': 'high',
            'speed': 'medium'
        }
"""

