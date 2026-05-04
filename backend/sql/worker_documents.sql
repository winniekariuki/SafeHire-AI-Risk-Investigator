-- Supabase: table + RPC for per-worker vector search (OpenAI text-embedding-3-small = 1536 dims).
-- Run in SQL Editor after enabling the pgvector extension.
--
-- NOTE: We do NOT create an IVFFlat/HNSW index on ``embedding`` here. Building those
-- indexes often needs more than Supabase’s default maintenance_work_mem (~32 MB), which
-- triggers: "memory required is … maintenance_work_mem is 32 MB".
-- For small demo tables, sequential scan on ``embedding`` is fine. After ingesting
-- data, run ``worker_documents_vector_index.sql`` (optional) for faster search.

create extension if not exists vector;

create table if not exists public.worker_documents (
  id uuid primary key default gen_random_uuid(),
  worker_id text not null,
  source text not null,
  content text not null,
  embedding vector(1536) not null,
  created_at timestamptz not null default now()
);

create index if not exists worker_documents_worker_id_idx
  on public.worker_documents (worker_id);

alter table public.worker_documents enable row level security;

-- Adjust policies for your app: often INSERT/SELECT for authenticated service, or open for demo anon + service_role.
-- Example (permissive demo — tighten for production):
-- create policy "Allow read worker_documents" on public.worker_documents for select using (true);
-- create policy "Allow insert worker_documents" on public.worker_documents for insert with check (true);
-- create policy "Allow delete own worker_documents" on public.worker_documents for delete using (true);

-- Postgres cannot change OUT/return row type with CREATE OR REPLACE — drop old overloads first.
drop function if exists public.match_worker_documents(vector(1536), text, integer);
drop function if exists public.match_worker_documents(vector, text, integer);

create or replace function public.match_worker_documents(
  query_embedding vector(1536),
  match_worker_id text,
  match_count int default 8
)
returns table (
  source text,
  content text,
  similarity float
)
language sql
stable
as $$
  select
    wd.source,
    wd.content,
    (1 - (wd.embedding <=> query_embedding))::float as similarity
  from public.worker_documents wd
  where wd.worker_id = match_worker_id
  order by wd.embedding <=> query_embedding
  limit greatest(1, least(match_count, 50));
$$;

grant execute on function public.match_worker_documents(vector, text, int) to anon, authenticated, service_role;
