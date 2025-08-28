# backend/middleware/validation.py - New validation middleware

from typing import Any, Dict, List, Union
import logging
from fastapi import Request
from fastapi.responses import JSONResponse
import json

logger = logging.getLogger(__name__)

class DataValidationMiddleware:
    """Middleware to ensure all data integrity, especially percentages and confidence scores"""
    
    async def __call__(self, request: Request, call_next):
        response = await call_next(request)
        
        # Only process JSON responses
        if response.headers.get("content-type", "").startswith("application/json"):
            # Read the original response
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            
            try:
                # Parse JSON
                data = json.loads(body)
                
                # Validate and fix the data
                validated_data = self.validate_response_data(data)
                
                # Create new response with validated data
                return JSONResponse(
                    content=validated_data,
                    status_code=response.status_code,
                    headers=dict(response.headers)
                )
            except json.JSONDecodeError:
                # If not valid JSON, return original response
                return response
        
        return response
    
    def validate_response_data(self, data: Any) -> Any:
        """Recursively validate and fix data integrity issues"""
        if isinstance(data, dict):
            return {k: self.validate_response_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.validate_response_data(item) for item in data]
        elif isinstance(data, (int, float)):
            # Check if this might be a percentage or confidence value
            if isinstance(data, float):
                # Common percentage/confidence field patterns
                parent_key = self._get_parent_key(data)
                if any(keyword in str(parent_key).lower() for keyword in 
                       ['confidence', 'score', 'percentage', 'rate', 'probability']):
                    # Ensure value is between 0 and 1 (or 0 and 100 for percentages)
                    if data > 1.0 and data <= 100.0:
                        # Likely a percentage, convert to decimal
                        return data / 100.0
                    elif data > 100.0:
                        # Invalid percentage, cap at 100%
                        logger.warning(f"Invalid percentage value {data} capped at 1.0")
                        return 1.0
                    elif data < 0.0:
                        # Negative confidence, set to 0
                        logger.warning(f"Negative confidence value {data} set to 0.0")
                        return 0.0
                    else:
                        # Valid confidence value (0-1)
                        return data
            return data
        else:
            return data
    
    def _get_parent_key(self, value):
        """Helper to track parent key context (simplified version)"""
        # In production, you'd implement proper context tracking
        return ""

# Enhanced scoring validator
class ScoringValidator:
    """Validates all scoring and confidence calculations"""
    
    @staticmethod
    def validate_confidence(confidence: float, source: str = "") -> float:
        """Ensure confidence is within valid bounds [0, 1]"""
        if confidence < 0:
            logger.warning(f"Negative confidence {confidence} from {source}, setting to 0")
            return 0.0
        elif confidence > 1:
            logger.warning(f"Confidence {confidence} exceeds 1.0 from {source}, capping at 1.0")
            return 1.0
        return confidence
    
    @staticmethod
    def validate_model_scores(scores: Dict[str, float]) -> Dict[str, float]:
        """Validate all model scores in a dictionary"""
        validated = {}
        for model, score in scores.items():
            validated[model] = ScoringValidator.validate_confidence(score, f"model:{model}")
        return validated
    
    @staticmethod
    def validate_percentage(value: float, source: str = "") -> float:
        """Ensure percentage is within valid bounds [0, 100]"""
        if value < 0:
            logger.warning(f"Negative percentage {value} from {source}, setting to 0")
            return 0.0
        elif value > 100:
            logger.warning(f"Percentage {value} exceeds 100 from {source}, capping at 100")
            return 100.0
        return value