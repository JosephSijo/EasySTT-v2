from abc import ABC, abstractmethod
import importlib
from typing import Optional, Tuple, Dict, Any
from openai import OpenAI


def _load_gemini_client() -> tuple[str, Any]:
    try:
        return "google-genai", importlib.import_module("google.genai")
    except ImportError:
        try:
            return "google-generativeai", importlib.import_module("google.generativeai")
        except ImportError as exc:
            raise RuntimeError(
                "Gemini support requires either 'google-genai' or the legacy "
                "'google-generativeai' package to be installed."
            ) from exc

class AIProvider(ABC):
    @abstractmethod
    def refine(self, text: str, style: str, custom_prompt: str = "") -> str:
        pass

class GeminiProvider(AIProvider):
    def __init__(self, api_key: str, model_id: str = "gemini-2.0-flash"):
        self.api_key = api_key
        self.model_id = model_id

    def refine(self, text: str, style: str, custom_prompt: str = "") -> str:
        prompts = {
            "Verbatim": "Repeat the following text exactly as is, without any changes:",
            "Professional": "Clean up this transcript. Remove fillers (umms, ahhs), fix grammar, and make it concise while preserving the meaning:",
            "Poetic": "Enhance the vocabulary and improve the flow of this text to make it more creative and poetic:",
            "Custom": custom_prompt
        }
        
        system_instruction = prompts.get(style, prompts["Professional"])
        full_prompt = f"{system_instruction}\n\n{text}"

        client_style, modern_genai = _load_gemini_client()
        if client_style == "google-genai":
            client = modern_genai.Client(api_key=self.api_key)
            response = client.models.generate_content(
                model=self.model_id,
                contents=full_prompt
            )
            return response.text.strip()

        modern_genai.configure(api_key=self.api_key)
        model = modern_genai.GenerativeModel(self.model_id)
        response = model.generate_content(full_prompt)
        return (response.text or "").strip()

class OpenAICompatibleProvider(AIProvider):
    def __init__(self, api_key: str, model: str, base_url: Optional[str] = None):
        client_kwargs: Dict[str, Any] = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url

        self.client = OpenAI(**client_kwargs)
        self.model = model

    def refine(self, text: str, style: str, custom_prompt: str = "") -> str:
        prompts = {
            "Verbatim": "Repeat the following text exactly as is, without any changes.",
            "Professional": "Clean up this transcript. Remove fillers (umms, ahhs), fix grammar, and make it concise while preserving the meaning.",
            "Poetic": "Enhance the vocabulary and improve the flow of this text to make it more creative and poetic.",
            "Custom": custom_prompt
        }
        
        system_instruction = prompts.get(style, prompts["Professional"])
        
        response = self.client.chat.completions.create(
            model=self.model,
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
    def __init__(
        self,
        provider_name: str,
        keys: Dict[str, str],
        api_models: Optional[Dict[str, str]] = None,
        custom_api_profiles: Optional[list[Dict[str, Any]]] = None,
    ):
        self.provider_name = provider_name
        self.keys = keys
        self.api_models = api_models or {}
        self.custom_api_profiles = custom_api_profiles or []
        self.current_provider = self._get_provider(provider_name, keys)

    def _get_provider(self, name: str, keys: Dict[str, str]) -> Optional[AIProvider]:
        custom_profile = self._find_custom_profile(name)
        if custom_profile:
            api_type = custom_profile.get("api_type", "openai_compatible")
            api_key = custom_profile.get("api_key", "")
            model = custom_profile.get("model", "gpt-4o")
            base_url = custom_profile.get("base_url") or None

            if api_type == "gemini" and api_key:
                return GeminiProvider(api_key, model_id=model)
            if api_key:
                return OpenAICompatibleProvider(api_key, model=model, base_url=base_url)

        key = keys.get(name)
        if name == "Gemini" and key:
            return GeminiProvider(key, model_id=self.api_models.get("Gemini", "gemini-2.0-flash"))
        if name == "OpenAI":
            key = keys.get("OpenAI") or keys.get("GPT")
            if key:
                return OpenAICompatibleProvider(
                    key,
                    model=self.api_models.get("OpenAI", "gpt-4o"),
                )
        return None

    def _find_custom_profile(self, name: str) -> Optional[Dict[str, Any]]:
        for profile in self.custom_api_profiles:
            if profile.get("id") == name or profile.get("name") == name:
                return profile
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
    def validate_api_key(
        provider: str,
        key: str,
        base_url: Optional[str] = None,
        api_type: str = "openai_compatible",
    ) -> Tuple[bool, str]:
        try:
            if api_type == "gemini" or "Gemini" in provider:
                client_style, modern_genai = _load_gemini_client()
                if client_style == "google-genai":
                    client = modern_genai.Client(api_key=key)
                    client.models.list()
                else:
                    modern_genai.configure(api_key=key)
                    list(modern_genai.list_models())
            else:
                client_kwargs: Dict[str, Any] = {"api_key": key}
                if base_url:
                    client_kwargs["base_url"] = base_url
                client = OpenAI(**client_kwargs)
                client.models.list()
            return True, "Success"
        except Exception as e:
            return False, str(e)
