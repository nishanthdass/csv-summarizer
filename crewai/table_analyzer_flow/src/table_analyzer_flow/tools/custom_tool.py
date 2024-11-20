from crewai_tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type, Dict, Any
import json


class JSONConversionToolInput(BaseModel):
    """Input schema for JSONConversionTool."""
    argument: Dict[str, Any] = Field(..., description="A JSON object (Python dictionary) to be serialized into a string.")

class JSONConversionTool(BaseTool):
    name: str = "JSON Conversion Tool"
    description: str = (
        "This tool takes a JSON object (Python dictionary) and converts it into a JSON-formatted string for storage."
    )
    args_schema: Type[BaseModel] = JSONConversionToolInput

    def _run(self, argument: Dict[str, Any]) -> str:
        """Convert the provided JSON object into a JSON string and replace single quotes with $$."""
        try:
            # Serialize the JSON object to a string
            result = json.dumps(argument)

            # Replace single quotes with $$
            result_with_replacements = result.replace("'", "$$")
            return result_with_replacements
        except TypeError as e:
            raise ValueError(f"Invalid JSON object for conversion: {e}")