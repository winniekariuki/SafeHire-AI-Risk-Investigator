-- OPTIONAL: one-shot similarity across all workers (no per-worker RPC loop).
-- Requires ``worker_documents`` and pgvector.

drop function if exists public.match_platform_documents(vector(1536), integer);
drop function if exists public.match_platform_documents(vector, integer);

create or replace function public.match_platform_documents(
  query_embedding vector(1536),
  match_count int default 15
)
returns table (
  worker_id text,
  source text,
  content text,
  similarity float
)
language sql
stable
as $$
  select
    wd.worker_id,
    wd.source,
    wd.content,
    (1 - (wd.embedding <=> query_embedding))::float as similarity
  from public.worker_documents wd
  order by wd.embedding <=> query_embedding
  limit greatest(1, least(match_count, 50));
$$;

grant execute on function public.match_platform_documents(vector(1536), integer) to anon, authenticated, service_role;
