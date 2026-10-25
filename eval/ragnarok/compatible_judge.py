"""DeepEval bridge to Odin's configured provider, including project headers.

Only constructed when an explicitly enabled judge model is `odin:PROVIDER`.
"""

import re
import sys
from pathlib import Path

from deepeval.models import DeepEvalBaseLLM


class OdinJudge(DeepEvalBaseLLM):
    def __init__(self, provider="openai"):
        self.provider = provider
        super().__init__(model_name=f"odin:{provider}")

    def load_model(self):
        backend = Path(__file__).resolve().parents[2] / "backend"
        if str(backend) not in sys.path:
            sys.path.insert(0, str(backend))
        from odin.llm.factory import chat_model

        return chat_model(self.provider).model_copy(update={"max_tokens": 8192})

    def generate(self, prompt, schema=None):
        model = (
            self.model.with_structured_output(schema, method="function_calling", include_raw=True)
            if schema
            else self.model
        )
        result = model.invoke(prompt)
        return self._validated(result, schema) if schema else result.content

    async def a_generate(self, prompt, schema=None):
        model = (
            self.model.with_structured_output(schema, method="function_calling", include_raw=True)
            if schema
            else self.model
        )
        result = await model.ainvoke(prompt)
        return self._validated(result, schema) if schema else result.content

    @staticmethod
    def _validated(result, schema):
        if isinstance(result, schema):
            return result
        if not isinstance(result, dict) or "raw" not in result:
            return schema.model_validate(result)
        if result.get("parsed") is not None:
            return schema.model_validate(result["parsed"])
        raw = result["raw"]
        calls = getattr(raw, "tool_calls", []) or []
        if len(calls) == 1:
            return schema.model_validate(calls[0]["args"])
        content = raw.content
        if isinstance(content, list):
            content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
        if not isinstance(content, str):
            raise ValueError("Judge returned no structured data")
        content = content.strip()
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
        # Validate actual JSON; do not repair or invent missing fields/scores.
        return schema.model_validate_json(content)

    def generate_with_schema(self, prompt, schema, **kwargs):
        # DeepEval 4.x calls these entrypoints instead of passing schema through
        # generate/a_generate. Its base fallback drops the schema argument.
        return self.generate(prompt, schema=schema)

    async def a_generate_with_schema(self, prompt, schema, **kwargs):
        return await self.a_generate(prompt, schema=schema)

    def get_model_name(self):
        return f"odin:{self.provider}"
