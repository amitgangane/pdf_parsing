import json
import os

import requests
from dotenv import load_dotenv
from openai import OpenAI
from langchain_core.prompts import PromptTemplate

from Ingestion.retrieval import hybrid_search, keyword_search, semantic_search

load_dotenv()

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

RAG_PROMPT_TEMPLATE = """
You are an AI assistant helping answer questions about Retrieval-Augmented Generation (RAG).
Use the following retrieved documents to answer the user's question.
If the retrieved documents don't contain relevant information, say that you don't know.

RETRIEVED DOCUMENTS:
{context}

USER QUESTION:
{question}

YOUR ANSWER (be comprehensive, accurate, and helpful):
"""

prompt = PromptTemplate(
    input_variables=["context", "question"],
    template=RAG_PROMPT_TEMPLATE,
)


def generate_with_openai(prompt_text, model_name="gpt-4o-mini", stream=False):
    """Generate response using OpenAI model."""
    try:
        if len(prompt_text) > 30000:
            prompt_text = prompt_text[:30000] + "...[truncated due to length]"
            print("Warning: Prompt was truncated to 30000 characters")

        if stream:
            response = openai_client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt_text}],
                stream=True,
            )
            for chunk in response:
                text = chunk.choices[0].delta.content
                if text:
                    yield text
        else:
            response = openai_client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt_text}],
            )
            return response.choices[0].message.content

    except Exception as e:
        import traceback
        error_msg = f"Error with OpenAI generation: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        if stream:
            yield error_msg
        else:
            return error_msg


def generate_with_ollama(prompt_text, model_name="llama2:latest", stream=False):
    """Generate response using Ollama."""
    try:
        url = "http://localhost:11434/api/generate"
        data = {
            "model": model_name,
            "prompt": prompt_text,
            "stream": stream,
            "options": {"temperature": 0.7},
        }

        if stream:
            response = requests.post(url, json=data, stream=True)
            response.raise_for_status()
            for line in response.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line.decode("utf-8"))
                        if "response" in chunk:
                            yield chunk["response"]
                    except json.JSONDecodeError:
                        continue
        else:
            response = requests.post(url, json=data)
            response.raise_for_status()
            return response.json().get("response", "No response generated")
    except Exception as e:
        error_msg = f"Error generating response with Ollama: {str(e)}"
        if stream:
            yield error_msg
        else:
            return error_msg


def generate_rag_response(
    query, search_type="hybrid", top_k=5, model_type="openai", stream=False
):
    """
    Generate RAG response using retrieved chunks.

    Args:
        query: User query
        search_type: Type of search (keyword, semantic, hybrid)
        top_k: Number of chunks to retrieve
        model_type: Type of model to use (openai, ollama)
        stream: Whether to stream the response

    Returns:
        Generated response or generator for streaming
    """
    try:
        if search_type == "keyword":
            results = keyword_search(query, top_k=top_k)
        elif search_type == "semantic":
            results = semantic_search(query, top_k=top_k)
        else:
            results = hybrid_search(query, top_k=top_k)

        if not results:
            message = "No relevant information found. Please try a different search type or refine your question."
            if stream:
                yield message
                return
            else:
                return message

        contexts = []
        for i, hit in enumerate(results):
            source = hit["_source"]
            content = source.get("content", "")
            content_type = source.get("content_type", "unknown")
            context_entry = f"[Document {i+1} - {content_type}]\n{content}"
            contexts.append(context_entry)

        context_text = "\n\n---\n\n".join(contexts)
        prompt_text = prompt.format(context=context_text, question=query)

        if model_type == "openai":
            if stream:
                yield from generate_with_openai(prompt_text, stream=True)
            else:
                return generate_with_openai(prompt_text, stream=False)
        else:  # ollama
            if stream:
                yield from generate_with_ollama(prompt_text, stream=True)
            else:
                return generate_with_ollama(prompt_text, stream=False)

    except Exception as e:
        error_message = f"Error in RAG process: {str(e)}"
        if stream:
            yield error_message
        else:
            return error_message


if __name__ == "__main__":
    query = "How does RAG work?"

    print("OpenAI Streaming Response: ", end="", flush=True)
    for chunk in generate_rag_response(query, "hybrid", 3, "openai", True):
        print(chunk, end="", flush=True)

    print("\n\nOllama Streaming Response: ", end="", flush=True)
    for chunk in generate_rag_response(query, "hybrid", 3, "ollama", True):
        print(chunk, end="", flush=True)
