from typing import AsyncGenerator, List
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from app.core.settings import settings

class OllamaService:
    def __init__(self):
        self.llm = ChatOllama(
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_HOST,
            temperature=settings.OLLAMA_TEMPERATURE,
        )

    async def stream_chat(
        self, 
        messages: List[dict], 
        context_docs: List[str] = None
    ) -> AsyncGenerator[str, None]:
        
        system_prompt = "You are a helpful AI assistant."
        if context_docs:
            context_str = "\n\n".join(context_docs)
            system_prompt += f"\n\nHere is some context to help answer the user's question:\n{context_str}"
        
        langchain_messages = [SystemMessage(content=system_prompt)]
        
        for msg in messages:
            if msg["role"] == "user":
                langchain_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                langchain_messages.append(AIMessage(content=msg["content"]))
        
        # Stream response
        async for chunk in self.llm.astream(langchain_messages):
            yield chunk.content

ollama_service = OllamaService()
