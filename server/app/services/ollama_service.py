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

        # Build enhanced legal system prompt
        system_prompt = """You are an elite Legal Expert Assistant specializing in document analysis, legal reasoning, and law.

CORE DIRECTIVES:
1. LEGAL PRECISION: Analyze all input with a legal lens. Look for obligations, rights, definitions, and jurisdictional nuances.
2. RAG CONTEXT FIRST: If document context is provided, it is your primary source of truth. Cite specific filenames and quote relevant sections when possible.
3. KNOWLEDGE INTEGRATION: If the documents are silent on a point, use your internal knowledge of law to provide general legal principles, but clearly distinguish them as "general legal perspective" vs "document-specific findings".
4. STRUCTURED REASONING: Break down complex legal queries into issues, relevant rules/clauses, analysis, and conclusions (IRAC-style).
5. CITATION: Always cite sources in the format: [Source: filename, Page/Chunk X].
6. CAUTION: Remind the user that your output is for informational purposes and not formal legal advice when making significant legal interpretations."""

        # Add RAG context if available
        if context_docs:
            context_str = "\n\n".join(context_docs)
            system_prompt += f"\n\n=== AUTHORITATIVE DOCUMENT CONTEXT ===\n{context_str}\n=== END CONTEXT ==="

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

    async def generate_queries(self, original_query: str, count: int = 3) -> List[str]:
        """
        Generate variations of a query to improve RAG retrieval accuracy.
        """
        prompt = f"""You are a search expert. Generate {count} different versions of the following legal query to help find relevant documents. 
Include alternative legal terminology or broader/narrower versions of the question.

Original Query: "{original_query}"

Output ONLY the queries, one per line, without numbers or any other text."""

        messages = [
            SystemMessage(content="You generate search query variations."),
            HumanMessage(content=prompt)
        ]

        try:
            response = await self.llm.ainvoke(messages)
            queries = [q.strip() for q in response.content.split("\n") if q.strip()]
            # Always include the original query
            return list(set([original_query] + queries[:count]))
        except Exception as e:
            print(f"Error generating queries: {e}")
            return [original_query]

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
