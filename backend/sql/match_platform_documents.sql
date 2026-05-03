-- Cross-worker semantic search for platform-wide RAG (e.g. "who is good with children?").
-- Run in Supabase → SQL Editor. Adjust vector(1536) if your embedding column uses another size
-- (must match OpenAI ``text-embedding-3-small`` dimensions, default 1536).

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

grant execute on function public.match_platform_documents(vector, int) to anon, authenticated, service_role;
