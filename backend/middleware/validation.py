# backend/middleware/validation.py - Fixed validation middleware

from typing import Any, Dict, List, Union, Callable
import logging
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import json

logger = logging.getLogger(__name__)


class DataValidationMiddleware(BaseHTTPMiddleware):
    """Middleware to ensure all data integrity, especially percentages and confidence scores"""

    def __init__(self, app: ASGIApp, **kwargs):
        super().__init__(app)
        self._current_context = {}  # Track parent key context

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Process the request normally
        response = await call_next(request)

        # Only process JSON responses
        content_type = response.headers.get("content-type", "")
        if not content_type.startswith("application/json"):
            return response

        # Read the response body
        response_body = b""
        async for chunk in response.body_iterator:
            response_body += chunk

        try:
            # Parse JSON
            data = json.loads(response_body.decode())

            # Validate and fix the data
            validated_data = self.validate_response_data(data)

            # Log size change for debugging
            original_size = len(response_body)
            validated_json = json.dumps(validated_data)
            new_size = len(validated_json.encode())
            if original_size != new_size:
                logger.debug(
                    f"Response size changed: {original_size} -> {new_size} bytes"
                )

            # Create new response with validated data
            # Let JSONResponse calculate the correct Content-Length
            return JSONResponse(
                content=validated_data,
                status_code=response.status_code,
                # REMOVED: headers=dict(response.headers),  # This was causing the issue
                media_type="application/json",
            )
        except json.JSONDecodeError:
            # If not valid JSON, return original response body
            return Response(
                content=response_body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=content_type,
            )
        except Exception as e:
            logger.error(f"Error in validation middleware: {e}")
            # Return original response on any error
            return Response(
                content=response_body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=content_type,
            )

    def validate_response_data(self, data: Any, parent_key: str = "") -> Any:
        """Recursively validate and fix data integrity issues"""
        if isinstance(data, dict):
            validated = {}
            for k, v in data.items():
                # Pass the current key as context
                validated[k] = self.validate_response_data(v, parent_key=k)
            return validated

        elif isinstance(data, list):
            return [
                self.validate_response_data(item, parent_key=parent_key)
                for item in data
            ]

        elif isinstance(data, (int, float)):
            # Check if this might be a percentage or confidence value
            if isinstance(data, (int, float)):
                # Common percentage/confidence field patterns
                confidence_keywords = [
                    "confidence",
                    "score",
                    "percentage",
                    "rate",
                    "probability",
                    "reliability",
                    "accuracy",
                    "certainty",
                ]

                if any(
                    keyword in parent_key.lower() for keyword in confidence_keywords
                ):
                    # Handle float values
                    float_value = float(data)

                    # Detect if it's a percentage (1-100) that should be decimal (0-1)
                    if float_value > 1.0 and float_value <= 100.0:
                        # Check if the field name suggests it should be decimal
                        decimal_indicators = ["confidence", "probability", "score"]
                        if any(
                            indicator in parent_key.lower()
                            for indicator in decimal_indicators
                        ):
                            # Convert percentage to decimal
                            logger.debug(
                                f"Converting {parent_key}={float_value} from percentage to decimal"
                            )
                            return float_value / 100.0
                        else:
                            # Keep as percentage if field suggests percentage format
                            return float_value

                    # Cap values that exceed bounds
                    elif float_value > 100.0:
                        logger.warning(
                            f"Invalid {parent_key} value {float_value} capped at 1.0"
                        )
                        return 1.0

                    # Handle negative values
                    elif float_value < 0.0:
                        logger.warning(
                            f"Negative {parent_key} value {float_value} set to 0.0"
                        )
                        return 0.0

                    # Valid confidence value (0-1)
                    else:
                        return float_value

            return data

        else:
            # Return other types unchanged
            return data


# Enhanced scoring validator - remains the same
class ScoringValidator:
    """Validates all scoring and confidence calculations"""

    @staticmethod
    def validate_confidence(confidence: float, source: str = "") -> float:
        """Ensure confidence is within valid bounds [0, 1]"""
        if confidence < 0:
            logger.warning(
                f"Negative confidence {confidence} from {source}, setting to 0"
            )
            return 0.0
        elif confidence > 1:
            # Check if it might be a percentage
            if confidence <= 100:
                logger.info(
                    f"Converting confidence {confidence} from percentage to decimal from {source}"
                )
                return confidence / 100.0
            else:
                logger.warning(
                    f"Confidence {confidence} exceeds valid range from {source}, capping at 1.0"
                )
                return 1.0
        return confidence

    @staticmethod
    def validate_model_scores(scores: Dict[str, float]) -> Dict[str, float]:
        """Validate all model scores in a dictionary"""
        validated = {}
        for model, score in scores.items():
            validated[model] = ScoringValidator.validate_confidence(
                score, f"model:{model}"
            )
        return validated

    @staticmethod
    def validate_percentage(value: float, source: str = "") -> float:
        """Ensure percentage is within valid bounds [0, 100]"""
        if value < 0:
            logger.warning(f"Negative percentage {value} from {source}, setting to 0")
            return 0.0
        elif value > 100:
            logger.warning(
                f"Percentage {value} exceeds 100 from {source}, capping at 100"
            )
            return 100.0
        return value

    @staticmethod
    def validate_trait_scores(trait_scores: Dict[str, float]) -> Dict[str, float]:
        """Validate trait scores ensuring they're in [0, 1] range"""
        validated = {}
        for trait, score in trait_scores.items():
            validated[trait] = ScoringValidator.validate_confidence(
                score, f"trait:{trait}"
            )
        return validated

    @staticmethod
    def validate_response_scores(response_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate all scores in a response object"""
        if "confidence" in response_data:
            response_data["confidence"] = ScoringValidator.validate_confidence(
                response_data["confidence"], "response"
            )

        if "scores_by_trait" in response_data and isinstance(
            response_data["scores_by_trait"], dict
        ):
            response_data["scores_by_trait"] = ScoringValidator.validate_trait_scores(
                response_data["scores_by_trait"]
            )

        if "model_scores" in response_data and isinstance(
            response_data["model_scores"], dict
        ):
            response_data["model_scores"] = ScoringValidator.validate_model_scores(
                response_data["model_scores"]
            )

        return response_data
