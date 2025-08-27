from .base_model import BaseGradingModel
from .openai_model import OpenAIModel
from core.config import VISION_GRADING_MODEL, OPENAI_API_KEY

def get_ai_model() -> BaseGradingModel:
    """
    Factory function to get the configured AI grading model instance.
    This allows for easy switching between different AI providers.
    """
    # For now, we only have OpenAI, but this is where you could add
    # logic to switch to Gemini, a local model, etc. based on config.
    
    # Example logic for future expansion:
    # if AI_PROVIDER == "google":
    #     return GeminiModel(...)
    
    return OpenAIModel(api_key=OPENAI_API_KEY, model_name=VISION_GRADING_MODEL)