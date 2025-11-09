"""
LLM Provider Interface and Implementations.

Provider-agnostic adapter for OpenAI and Anthropic with fallback support.
"""

import os
import logging
from typing import Dict, Any, Optional, Tuple
from abc import ABC, abstractmethod
from enum import Enum

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class LLMProviderInterface(ABC):
    """Abstract interface for LLM providers."""
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 600,
        temperature: float = 0.3,
        **kwargs
    ) -> Tuple[str, int, int]:
        """
        Generate text from prompt.
        
        Returns:
            (output_text, tokens_in, tokens_out)
        """
        pass
    
    @abstractmethod
    def estimate_cost(self, tokens_in: int, tokens_out: int) -> float:
        """Estimate cost in USD."""
        pass


class OpenAIProvider(LLMProviderInterface):
    """OpenAI GPT provider implementation."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("LLM_MODEL_VERSION", "gpt-4o-mini")
        
        if not self.api_key:
            logger.warning("OpenAI API key not configured")
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 600,
        temperature: float = 0.3,
        **kwargs
    ) -> Tuple[str, int, int]:
        """Generate using OpenAI API."""
        try:
            import openai
            
            if not self.api_key:
                raise ValueError("OpenAI API key not configured")
            
            client = openai.AsyncOpenAI(api_key=self.api_key)
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )
            
            output_text = response.choices[0].message.content or ""
            tokens_in = response.usage.prompt_tokens
            tokens_out = response.usage.completion_tokens
            
            return output_text, tokens_in, tokens_out
            
        except ImportError:
            logger.error("openai package not installed")
            raise
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    def estimate_cost(self, tokens_in: int, tokens_out: int) -> float:
        """Estimate cost based on GPT-4o-mini pricing."""
        # GPT-4o-mini: $0.15/$0.60 per 1M tokens (input/output)
        input_cost = (tokens_in / 1_000_000) * 0.15
        output_cost = (tokens_out / 1_000_000) * 0.60
        return input_cost + output_cost


class AnthropicProvider(LLMProviderInterface):
    """Anthropic Claude provider implementation."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-haiku-20240307"):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model or os.getenv("ANTHROPIC_MODEL_VERSION", "claude-3-haiku-20240307")
        
        if not self.api_key:
            logger.warning("Anthropic API key not configured")
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 600,
        temperature: float = 0.3,
        **kwargs
    ) -> Tuple[str, int, int]:
        """Generate using Anthropic API."""
        try:
            import anthropic
            
            if not self.api_key:
                raise ValueError("Anthropic API key not configured")
            
            client = anthropic.AsyncAnthropic(api_key=self.api_key)
            
            # Anthropic uses system parameter separately
            response = await client.messages.create(
                model=self.model,
                system=system_prompt or "",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )
            
            output_text = response.content[0].text if response.content else ""
            
            # Estimate tokens (Anthropic doesn't always return usage)
            # Rough estimate: 1 token ≈ 4 characters
            tokens_in = len(prompt) // 4
            if system_prompt:
                tokens_in += len(system_prompt) // 4
            tokens_out = len(output_text) // 4
            
            return output_text, tokens_in, tokens_out
            
        except ImportError:
            logger.error("anthropic package not installed")
            raise
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise
    
    def estimate_cost(self, tokens_in: int, tokens_out: int) -> float:
        """Estimate cost based on Claude 3 Haiku pricing."""
        # Claude 3 Haiku: $0.25/$1.25 per 1M tokens (input/output)
        input_cost = (tokens_in / 1_000_000) * 0.25
        output_cost = (tokens_out / 1_000_000) * 1.25
        return input_cost + output_cost


class LLMProviderFactory:
    """Factory for creating LLM providers with fallback."""
    
    @staticmethod
    def create_provider(provider_name: Optional[str] = None) -> LLMProviderInterface:
        """
        Create provider with fallback chain: OpenAI -> Anthropic.
        
        Args:
            provider_name: Preferred provider (openai/anthropic), or None for auto
        
        Returns:
            Configured provider instance
        """
        provider_name = provider_name or os.getenv("LLM_PROVIDER", "openai")
        
        if provider_name == LLMProvider.OPENAI.value:
            try:
                return OpenAIProvider()
            except Exception as e:
                logger.warning(f"Failed to create OpenAI provider: {e}, falling back to Anthropic")
                return AnthropicProvider()
        
        elif provider_name == LLMProvider.ANTHROPIC.value:
            try:
                return AnthropicProvider()
            except Exception as e:
                logger.warning(f"Failed to create Anthropic provider: {e}, falling back to OpenAI")
                return OpenAIProvider()
        
        else:
            # Auto-detect: try OpenAI first, then Anthropic
            try:
                return OpenAIProvider()
            except Exception:
                logger.warning("OpenAI not available, trying Anthropic")
                return AnthropicProvider()
    
    @staticmethod
    async def generate_with_fallback(
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 600,
        temperature: float = 0.3,
        primary_provider: Optional[str] = None,
        **kwargs
    ) -> Tuple[str, int, int, str]:
        """
        Generate with automatic fallback between providers.
        
        Returns:
            (output_text, tokens_in, tokens_out, provider_used)
        """
        provider = LLMProviderFactory.create_provider(primary_provider)
        provider_name = "openai" if isinstance(provider, OpenAIProvider) else "anthropic"
        
        try:
            output, tokens_in, tokens_out = await provider.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )
            return output, tokens_in, tokens_out, provider_name
        except Exception as e:
            logger.error(f"Primary provider ({provider_name}) failed: {e}")
            
            # Try fallback
            fallback_provider = AnthropicProvider() if isinstance(provider, OpenAIProvider) else OpenAIProvider()
            fallback_name = "anthropic" if isinstance(fallback_provider, AnthropicProvider) else "openai"
            
            try:
                output, tokens_in, tokens_out = await fallback_provider.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    **kwargs
                )
                logger.info(f"Fallback to {fallback_name} succeeded")
                return output, tokens_in, tokens_out, fallback_name
            except Exception as fallback_error:
                logger.error(f"Fallback provider ({fallback_name}) also failed: {fallback_error}")
                raise

