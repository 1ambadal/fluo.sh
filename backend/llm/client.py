import re
import json
import asyncio
import logging
from typing import AsyncGenerator, Dict, Any, List, Optional
from openai import AsyncOpenAI
from backend.config import (
    LLM_PROVIDER,
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    LLM_MODEL,
)

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.provider = (provider or LLM_PROVIDER).lower()
        self.model = model or LLM_MODEL
        self.client: Optional[AsyncOpenAI] = None
        self._init_client()

    def _init_client(self) -> None:
        if self.provider == "deepseek":
            if not DEEPSEEK_API_KEY:
                logger.warning("⚠️ DEEPSEEK_API_KEY not set. Falling back to mock LLM.")
                self.provider = "mock"
                self.client = None
            else:
                self.client = AsyncOpenAI(
                    api_key=DEEPSEEK_API_KEY,
                    base_url=DEEPSEEK_BASE_URL,
                )

        elif self.provider == "mock":
            self.client = None
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

    def update_config(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        if provider:
            self.provider = provider.lower()
        if model:
            self.model = model
        self._init_client()

    async def stream_reply(
        self, system_prompt: str, history: List[Dict[str, str]], model: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        model_name = model or self.model

        if self.provider == "deepseek":
            messages = [{"role": "system", "content": system_prompt}]
            for msg in history:
                role = msg["role"] if msg["role"] in ("user", "assistant") else "user"
                messages.append({"role": role, "content": msg["content"]})

            try:
                response = await self.client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    stream=True,
                    temperature=0.7,
                )
                async for chunk in response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content

            except Exception as e:
                logger.error(f"Error in DEEPSEEK LLM streaming: {e}")
                yield f"Error in DeepSeek LLM response: {e}"

        elif self.provider == "mock":
            mock_responses = [
                "Hello! That is a very interesting topic. ",
                "I really enjoy talking about this with you. ",
                "Could you tell me a bit more about your thoughts on this? ",
                "What do you think?"
            ]
            for sentence in mock_responses:
                for word in sentence.split(" "):
                    if word:
                        yield word + " "
                        await asyncio.sleep(0.05)
        else:
            yield "LLM provider not implemented."

    async def generate_feedback(
        self, system_prompt: str, user_message: str, model: Optional[str] = None
    ) -> Dict[str, Any]:
        model_name = model or self.model

        if self.provider == "deepseek":
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ]

            try:
                response = await self.client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=0.2,
                )
                raw_text = response.choices[0].message.content or ""
                return self._clean_and_parse_json(raw_text, user_message)

            except Exception as e_json:
                logger.warning(f"{self.provider.upper()} json_object mode failed ({e_json}), retrying standard text generation...")
                try:
                    response = await self.client.chat.completions.create(
                        model=model_name,
                        messages=messages,
                        temperature=0.2,
                    )
                    raw_text = response.choices[0].message.content or ""
                    return self._clean_and_parse_json(raw_text, user_message)
                except Exception as e:
                    logger.error(f"{self.provider.upper()} feedback generation failed completely: {e}")
                    return {
                        "has_errors": False,
                        "corrected_text": user_message,
                        "mistakes": [],
                        "error": f"{self.provider.capitalize()} feedback generation failed: {str(e)}",
                    }

        elif self.provider == "mock":
            lower_msg = user_message.lower().strip()
            if "i wants" in lower_msg:
                corrected = user_message.replace("wants", "want").replace("Wants", "Want")
                return {
                    "has_errors": True,
                    "corrected_text": corrected,
                    "mistakes": [
                        {
                            "original": "wants",
                            "issue": "subject-verb agreement",
                            "fix": "want",
                            "explanation": "In English, the first-person singular pronoun 'I' takes the verb 'want' instead of 'wants'."
                        }
                    ]
                }
            return {
                "has_errors": False,
                "corrected_text": user_message,
                "mistakes": []
            }

        return {
            "has_errors": False,
            "corrected_text": user_message,
            "mistakes": []
        }

    def _clean_and_parse_json(self, text: str, original_message: str) -> Dict[str, Any]:
        cleaned = text.strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass

        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(cleaned[start:end+1].strip())
            except json.JSONDecodeError:
                pass

        return {
            "has_errors": False,
            "corrected_text": original_message,
            "mistakes": [],
            "raw_output": text
        }
