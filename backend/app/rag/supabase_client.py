import os
from functools import lru_cache

from supabase import create_client


def _normalize_supabase_url(raw: str) -> str:
    """Strip whitespace/quotes, ensure a scheme, and keep project origin only.

    If ``SUPABASE_URL`` includes ``/rest/v1`` (copy-paste from API docs), the Python
    client would build ``.../rest/v1/rest/v1/rpc/...`` and PostgREST returns PGRST125.
    """
    u = raw.strip().strip('"').strip("'")
    if not u:
        return ""
    if not u.startswith(("http://", "https://")):
        u = f"https://{u.lstrip('/')}"
    u = u.rstrip("/")
    suffix = "/rest/v1"
    while u.endswith(suffix):
        u = u[: -len(suffix)].rstrip("/")
    return u


@lru_cache(maxsize=1)
def get_supabase():
    """Create the client on first use so importing the app does not require valid Supabase env."""
    url = _normalize_supabase_url(os.getenv("SUPABASE_URL") or "")
    # Prefer service-role key for backend ingest jobs (bypasses RLS), fallback to anon.
    raw_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY") or ""
    key = raw_key.strip().strip('"').strip("'")
    if not url or not key:
        raise RuntimeError(
            "Supabase is not configured: set SUPABASE_URL and one of "
            "SUPABASE_SERVICE_ROLE_KEY / SUPABASE_ANON_KEY "
            "(Vercel: Project → Settings → Environment Variables). "
            "SUPABASE_URL must be the project URL only, e.g. https://<ref>.supabase.co "
            "(do not append /rest/v1)"
        )
    return create_client(url, key)
