from abc import ABC, abstractmethod
from typing import Optional, Tuple, Dict, Any
from google import genai
from openai import OpenAI
import os

class AIProvider(ABC):
    @abstractmethod
    def refine(self, text: str, style: str, custom_prompt: str = "") -> str:
        pass

class GeminiProvider(AIProvider):
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.model_id = 'gemini-2.0-flash'

    def refine(self, text: str, style: str, custom_prompt: str = "") -> str:
        prompts = {
            "Verbatim": "Repeat the following text exactly as is, without any changes:",
            "Professional": "Clean up this transcript. Remove fillers (umms, ahhs), fix grammar, and make it concise while preserving the meaning:",
            "Poetic": "Enhance the vocabulary and improve the flow of this text to make it more creative and poetic:",
            "Custom": custom_prompt
        }
        
        system_instruction = prompts.get(style, prompts["Professional"])
        full_prompt = f"{system_instruction}\n\n{text}"
        
        response = self.client.models.generate_content(
            model=self.model_id,
            contents=full_prompt
        )
        return response.text.strip()

class OpenAIProvider(AIProvider):
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)

    def refine(self, text: str, style: str, custom_prompt: str = "") -> str:
        prompts = {
            "Verbatim": "Repeat the following text exactly as is, without any changes.",
            "Professional": "Clean up this transcript. Remove fillers (umms, ahhs), fix grammar, and make it concise while preserving the meaning.",
            "Poetic": "Enhance the vocabulary and improve the flow of this text to make it more creative and poetic.",
            "Custom": custom_prompt
        }
        
        system_instruction = prompts.get(style, prompts["Professional"])
        
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": text}
            ]
        )
        return response.choices[0].message.content.strip()

class WhisperLocalProvider:
    """Local Whisper placeholder or actual implementation."""
    def transcribe(self, audio_path: str, language: Optional[str] = None) -> str:
        # This will be called by the engine using faster-whisper
        return "Internal faster-whisper logic will handle this"

class AIHandler:
    def __init__(self, provider_name: str, keys: Dict[str, str]):
        self.provider_name = provider_name
        self.keys = keys
        self.current_provider = self._get_provider(provider_name, keys)

    def _get_provider(self, name: str, keys: Dict[str, str]) -> Optional[AIProvider]:
        key = keys.get(name)
        if "Gemini" in name and key:
            return GeminiProvider(key)
        elif "GPT" in name and key:
            # Handle both "OpenAI" and "GPT" naming
            key = keys.get("OpenAI") or keys.get("GPT")
            if key:
                return OpenAIProvider(key)
        return None

    def refine_text(self, text: str, style: str = "Professional", custom_prompt: str = "") -> Dict[str, Any]:
        if not self.current_provider or style == "Verbatim":
            return {
                "text": text,
                "word_count": len(text.split())
            }
            
        try:
            refined = self.current_provider.refine(text, style, custom_prompt)
            return {
                "text": refined,
                "word_count": len(refined.split()),
                "original_text": text
            }
        except Exception as e:
            error_msg = str(e)
            print(f"Refinement Error: {error_msg}")
            
            # Special handling for Quota/Rate Limit errors
            if "RESOURCE_EXHAUSTED" in error_msg or "429" in error_msg or "exceeded your current quota" in error_msg.lower():
                # Silently fallback to verbatim but note the reason
                return {
                    "text": text,
                    "word_count": len(text.split()),
                    "warning": "Cloud AI quota reached. Using high-accuracy local transcript."
                }
                
            return {
                "text": text,
                "word_count": len(text.split()),
                "error": error_msg
            }

    @staticmethod
    def validate_api_key(provider: str, key: str) -> Tuple[bool, str]:
        try:
            if "Gemini" in provider:
                client = genai.Client(api_key=key)
                client.models.list()
            elif "GPT" in provider:
                client = OpenAI(api_key=key)
                client.models.list()
            return True, "Success"
        except Exception as e:
            return False, str(e)
