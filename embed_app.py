from config import ollama_settings
from embedchain import App
import os
PROMPT_TEMPLATE = """Use the provided context to answer the query accurately.

- Always include the page number(s) of the source document from the metadata if available.
- If the answer is not found in the context, respond with: "Answer not found in the document."

Context:
$context

Query:
$query

Answer (with page number if available):"""

# PROMPT_TEMPLATE = """Use the provided context to answer the query accurately.

# If the answer is not present in the context, respond with:
# "Answer not found in the document."

# Context:
# $context

# Query:
# $query

# Answer:"""

def embedchain_bot(app_id):
    return App.from_config(
        config={
            "app": {
                "config": {
                    "id": app_id,
                    "collect_metrics": False
                }
            },
            "llm": {
                "provider": ollama_settings.provider,
                "config": {
                    "model": ollama_settings.llm_model,
                    "base_url": ollama_settings.base_url,
                    "stream": True,
                    "prompt": PROMPT_TEMPLATE,
                }
            },
            "vectordb": {
                "provider": "chroma",
                "config": {
                    "collection_name": ollama_settings.collection,
                    "host": ollama_settings.host,
                    "port": ollama_settings.port,
                    "allow_reset": ollama_settings.reset,
                   # "path": "./Database"   # <-- ✅ Add this if not already defined in ollama_settings
                }

                
            },
            'chunker': {
        'chunk_size': 5000,
        'chunk_overlap': 200,
        'length_function': 'len',
        'min_chunk_size': 0
    },
            "embedder": {
                "provider": ollama_settings.provider,
                "config": {
                    "model": ollama_settings.embedding_model,
                    "base_url": ollama_settings.base_url
                }
            }
        }
    )