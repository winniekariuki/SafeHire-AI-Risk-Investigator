# app/rag/retriever.py

from openai import OpenAI
from app.rag.supabase_client import supabase
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_embedding(text: str):
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding


def retrieve_worker_evidence(worker_id: str, query: str, top_k: int = 5):
    embedding = get_embedding(query)

    response = supabase.rpc(
        "match_worker_documents",
        {
            "query_embedding": embedding,
            "match_worker_id": worker_id,
            "match_count": top_k,
        },
    ).execute()

    results = response.data or []

    return [
        {
            "source": r["source"],
            "content": r["content"],
            "relevance_score": r["similarity"],
        }
        for r in results
    ]