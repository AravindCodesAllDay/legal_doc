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
        """
        Stream chat responses with optional RAG context

        Args:
            messages: List of message dicts with 'role' and 'content'
            context_docs: Optional list of context strings from RAG
        """

        # Build enhanced system prompt
        system_prompt = """You are a helpful AI assistant with access to documents.

When answering questions:
1. If context from documents is provided, base your answer primarily on that context
2. Cite the source document when using information from it (e.g., "According to [filename]...")
3. If the context doesn't contain enough information, say so clearly
4. Be concise but thorough
5. If no documents are available, answer from your general knowledge"""

        # Add RAG context if available
        if context_docs:
            context_str = "\n\n".join(context_docs)
            system_prompt += f"\n\n=== DOCUMENT CONTEXT ===\n{context_str}\n=== END CONTEXT ==="

        # Convert to LangChain messages
        langchain_messages = [SystemMessage(content=system_prompt)]

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "user":
                langchain_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                langchain_messages.append(AIMessage(content=content))
            elif role == "system":
                # Skip system messages from history (already have system prompt)
                continue

        # Stream response
        try:
            async for chunk in self.llm.astream(langchain_messages):
                if chunk.content:
                    yield chunk.content
        except Exception as e:
            error_msg = f"Error streaming from Ollama: {str(e)}"
            print(error_msg)
            yield f"\n\n[Error: {error_msg}]"

    async def generate_title(self, first_message: str) -> str:
        """
        Generate a concise title for a chat session based on the first message
        """
        prompt = f"""Generate a very short title (3-6 words max) for a chat that starts with:

"{first_message[:200]}"

Only output the title, nothing else."""

        messages = [
            SystemMessage(content="You generate concise chat titles."),
            HumanMessage(content=prompt)
        ]

        try:
            response = await self.llm.ainvoke(messages)
            title = response.content.strip().strip('"').strip("'")
            return title[:50]  # Limit to 50 chars
        except Exception as e:
            print(f"Error generating title: {e}")
            return "New Chat"


ollama_service = OllamaService()
