-- OPTIONAL: vector index for faster similarity search after you have rows in worker_documents.
-- Run only **after** ingest. If this still errors on memory, skip entirely — seq scan is OK for small tables.
--
-- In Supabase SQL Editor, run as one batch:

set maintenance_work_mem = '128MB';

-- Pick ONE index type (not both). Drop old index if you switch.

-- Option A — IVFFlat: use a small ``lists`` value to reduce index build memory (100 often fails on Supabase).
drop index if exists public.worker_documents_embedding_ivfflat;
create index worker_documents_embedding_ivfflat
  on public.worker_documents
  using ivfflat (embedding vector_cosine_ops)
  with (lists = 10);

-- Option B — HNSW (supported on recent pgvector): often nicer for query latency; try if Option A fails.
-- drop index if exists public.worker_documents_embedding_hnsw;
-- create index worker_documents_embedding_hnsw
--   on public.worker_documents
--   using hnsw (embedding vector_cosine_ops);

-- If ``set maintenance_work_mem`` is rejected, try only Option A with lists = 4,
-- or omit vector indexes until you scale up / contact Supabase for mem limits.
