from .base_model import BaseGradingModel
from .openai_model import OpenAIModel
from .gemini_model import GeminiModel
from core.config import AI_PROVIDER, VISION_GRADING_MODEL, GEMINI_MODEL, OPENAI_API_KEY, GEMINI_API_KEY

def get_ai_model() -> BaseGradingModel:
    """
    Factory function to get the configured AI grading model instance.
    This allows for easy switching between different AI providers.
    """
    if AI_PROVIDER.lower() == "gemini":
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is required when using Gemini provider")
        return GeminiModel(api_key=GEMINI_API_KEY, model_name=GEMINI_MODEL)
    else:
        # Default to OpenAI
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required when using OpenAI provider")
        return OpenAIModel(api_key=OPENAI_API_KEY, model_name=VISION_GRADING_MODEL)