import os
from functools import lru_cache

from supabase import create_client


def _normalize_supabase_url(raw: str) -> str:
    """Strip whitespace/quotes and ensure a scheme (avoids SupabaseException: Invalid URL)."""
    u = raw.strip().strip('"').strip("'")
    if not u:
        return ""
    if not u.startswith(("http://", "https://")):
        u = f"https://{u.lstrip('/')}"
    return u.rstrip("/")


@lru_cache(maxsize=1)
def get_supabase():
    """Create the client on first use so importing the app does not require valid Supabase env."""
    url = _normalize_supabase_url(os.getenv("SUPABASE_URL") or "")
    key = (os.getenv("SUPABASE_ANON_KEY") or "").strip().strip('"').strip("'")
    if not url or not key:
        raise RuntimeError(
            "Supabase is not configured: set SUPABASE_URL and SUPABASE_ANON_KEY "
            "(Vercel: Project → Settings → Environment Variables). "
            "SUPABASE_URL must look like https://<ref>.supabase.co"
        )
    return create_client(url, key)
