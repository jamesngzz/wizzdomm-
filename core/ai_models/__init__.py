from .base_model import BaseGradingModel
from .gemini_model import GeminiModel
from core.config import GEMINI_GRADING_MODEL, GEMINI_API_KEY

def get_ai_model() -> BaseGradingModel:
    """
    Factory function to get the Gemini grading model instance.
    Only Gemini is supported for grading.
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is required for grading")
    return GeminiModel(api_key=GEMINI_API_KEY, model_name=GEMINI_GRADING_MODEL)