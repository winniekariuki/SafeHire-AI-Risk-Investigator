# scripts/ingest.py
from dotenv import load_dotenv
load_dotenv()

from app.rag.supabase_client import supabase
from app.rag.retriever import get_embedding

def ingest_all():
    # move your current ingestion logic into this function
    docs = [
        {
            "worker_id": "W002",
            "source": "Reference Note",
            "content": "Jane was good with chores but often came late and disappeared for two days.",
        },
        {
            "worker_id": "W002",
            "source": "Misconduct Report",
            "content": "Employer reported repeated absenteeism and poor communication.",
        },
    ]

    for doc in docs:
        embedding = get_embedding(doc["content"])

        supabase.table("worker_documents").insert({
            "worker_id": doc["worker_id"],
            "source": doc["source"],
            "content": doc["content"],
            "embedding": embedding,
        }).execute()

    print("Done")

print("Done")
if __name__ == "__main__":
    ingest_all()