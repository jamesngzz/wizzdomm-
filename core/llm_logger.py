import os
import logging
from datetime import datetime
from typing import Any, Optional

# GPT-5 Mini Pricing (per 1M tokens)
GPT_5_MINI_INPUT_COST_PER_1M = 0.150  # $0.15 per 1M input tokens
GPT_5_MINI_OUTPUT_COST_PER_1M = 0.600  # $0.60 per 1M output tokens

# Service names
SERVICE_VISION_GRADING = "vision_grading"
SERVICE_BATCH_GRADING = "batch_grading"

# Setup logging
def _setup_logger():
    """Setup file logger for LLM usage tracking"""
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Create logger
    logger = logging.getLogger('llm_usage')
    logger.setLevel(logging.INFO)
    
    # Avoid duplicate handlers
    if not logger.handlers:
        # File handler
        file_handler = logging.FileHandler('logs/llm_usage.log', encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter('%(asctime)s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        file_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
    
    return logger

# Global logger instance
_llm_logger = _setup_logger()

def calculate_cost(input_tokens: int, output_tokens: int, model_name: str) -> float:
    """Calculate cost based on token usage and model pricing"""
    if "gpt-5-mini" in model_name.lower():
        input_cost = (input_tokens / 1_000_000) * GPT_5_MINI_INPUT_COST_PER_1M
        output_cost = (output_tokens / 1_000_000) * GPT_5_MINI_OUTPUT_COST_PER_1M
        return input_cost + output_cost
    else:
        # Default pricing if model not recognized
        return 0.0

def log_llm_call(response: Any, model_name: str, service_name: str):
    """Log LLM API call with token usage and cost"""
    try:
        # Extract token usage from OpenAI response
        usage = getattr(response, 'usage', None)
        if not usage:
            _llm_logger.warning(f"No usage data found for {service_name} call")
            return
        
        input_tokens = getattr(usage, 'prompt_tokens', 0)
        output_tokens = getattr(usage, 'completion_tokens', 0) 
        total_tokens = getattr(usage, 'total_tokens', input_tokens + output_tokens)
        
        # Calculate cost
        cost = calculate_cost(input_tokens, output_tokens, model_name)
        
        # Log format: model | service | input:X | output:Y | total:Z | cost:$X.XX
        log_message = (
            f"{model_name} | {service_name} | "
            f"input:{input_tokens} | output:{output_tokens} | "
            f"total:{total_tokens} | cost:${cost:.5f}"
        )
        
        _llm_logger.info(log_message)
        
    except Exception as e:
        _llm_logger.error(f"Error logging LLM call: {e}")

def log_batch_summary(batch_size: int, total_cost: float, service_name: str):
    """Log summary for batch processing"""
    log_message = f"BATCH_SUMMARY | {service_name} | items:{batch_size} | total_cost:${total_cost:.5f}"
    _llm_logger.info(log_message)