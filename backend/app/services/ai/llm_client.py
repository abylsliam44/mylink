from typing import Optional
import asyncio
from langchain_openai import ChatOpenAI
from app.config import settings


def get_llm(model: Optional[str] = None, temperature: float = 0.2) -> ChatOpenAI:
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return ChatOpenAI(
        model=model or settings.OPENAI_MODEL,
        temperature=temperature,
        timeout=60,
        max_retries=2,
        api_key=settings.OPENAI_API_KEY,
    )


class LLMClient:
    def __init__(self):
        self.llm = get_llm()
    
    async def generate_response(self, prompt: str) -> str:
        """Generate response using LLM"""
        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: self.llm.invoke(prompt).content
            )
            return response
        except Exception as e:
            raise Exception(f"LLM generation failed: {e}")


# Global instance
llm_client = LLMClient()
