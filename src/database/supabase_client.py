"""
Supabase client factories.

Two flavours of clients are exposed:

1. `get_supabase_admin()` - uses the service_role key. Bypasses RLS.
   USE ONLY in trusted backend code paths (server-side).

2. `get_supabase_user_client(access_token)` - uses the anon key with the
   end-user's JWT attached. Honours RLS policies.

The admin client is cached (singleton). When a transient HTTP/2 disconnect
happens (Supabase closes idle keep-alive connections), call
`reset_supabase_admin()` to force a fresh client on the next call.

We force HTTP/1.1 on the underlying httpx clients because HTTP/2 keep-alive
on Windows + httpcore is prone to `RemoteProtocolError: Server disconnected`
after periods of inactivity.
"""
from functools import lru_cache
from typing import Optional

import httpx
from supabase import Client, create_client
from supabase.lib.client_options import ClientOptions

from src.config import settings


def _force_http1(client: Client) -> None:
    """Replace HTTP/2 httpx clients inside supabase sub-clients with HTTP/1.1.

    Supabase-py defaults to HTTP/2 which is unreliable on Windows + idle
    keep-alive (causes `RemoteProtocolError: Server disconnected`).
    """
    transport = httpx.HTTPTransport(retries=2, http2=False)

    for attr in ("postgrest", "storage"):
        sub = getattr(client, attr, None)
        if sub is None:
            continue
        session = getattr(sub, "session", None)
        if session is None:
            continue
        try:
            old_headers = dict(session.headers)
            old_timeout = session.timeout
            new_session = httpx.Client(
                base_url=session.base_url,
                headers=old_headers,
                timeout=old_timeout,
                transport=transport,
                http2=False,
            )
            sub.session = new_session
        except Exception:  # noqa: BLE001
            pass


@lru_cache(maxsize=1)
def get_supabase_admin() -> Client:
    """Service-role client. Bypasses RLS. Backend-only."""
    if not settings.supabase_url or not settings.supabase_service_key:
        raise RuntimeError(
            "SUPABASE_URL / SUPABASE_SERVICE_KEY are not set. "
            "Check your .env file."
        )
    client = create_client(settings.supabase_url, settings.supabase_service_key)
    _force_http1(client)
    return client


def reset_supabase_admin() -> None:
    """Drop the cached admin client so the next call rebuilds it."""
    get_supabase_admin.cache_clear()


def get_supabase_user_client(access_token: Optional[str] = None) -> Client:
    """
    Anon-key client scoped to a specific end-user's JWT.

    Pass the token from the Authorization header. The resulting client
    will respect RLS policies as if the user were calling Supabase directly.
    """
    if not settings.supabase_url or not settings.supabase_anon_key:
        raise RuntimeError(
            "SUPABASE_URL / SUPABASE_ANON_KEY are not set."
        )

    options = ClientOptions(
        headers={"Authorization": f"Bearer {access_token}"} if access_token else {}
    )
    client = create_client(settings.supabase_url, settings.supabase_anon_key, options)
    _force_http1(client)
    if access_token:
        try:
            client.postgrest.auth(access_token)
        except Exception:  # noqa: BLE001
            pass
    return client
