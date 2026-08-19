from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings, get_settings
from app.services.play_store_discovery import (
    PlayDiscoveryResult,
    PlayDiscoveryUnavailable,
    run_cbk_play_discovery,
)
from app.services.serpapi_play_discovery import run_cbk_serpapi_play_discovery
from app.services.talordata_play_discovery import run_cbk_talordata_play_discovery


@dataclass(frozen=True)
class ResolvedPlayProvider:
    provider: str
    talordata_api_key: str | None = None
    serpapi_api_key: str | None = None
    legacy_talordata_key: bool = False
    configuration_note: str | None = None


def _looks_like_talordata_token(value: str | None) -> bool:
    # TalorData's published integrations document SERP tokens as sk_... and
    # explicitly distinguish them from dashboard login JWTs.
    return bool(value and value.strip().startswith("sk_"))


def resolve_play_provider(
    requested: str,
    *,
    talordata_api_key: str | None,
    serpapi_api_key: str | None,
) -> ResolvedPlayProvider:
    normalized = (requested or "auto").strip().lower()
    talor_key = (talordata_api_key or "").strip() or None
    serp_key = (serpapi_api_key or "").strip() or None

    legacy_key: str | None = None
    if not talor_key and _looks_like_talordata_token(serp_key):
        legacy_key = serp_key

    # A prior KDR release told users to place any indexed-provider key in the
    # SerpApi variable. Preserve those installations when the token clearly
    # matches TalorData's documented SERP-token format.
    if normalized == "serpapi" and legacy_key:
        return ResolvedPlayProvider(
            provider="talordata",
            talordata_api_key=legacy_key,
            legacy_talordata_key=True,
            configuration_note=(
                "Detected a TalorData-style SERP token in legacy KDR_SERPAPI_API_KEY; "
                "KDR is routing it to TalorData. Rename it to KDR_TALORDATA_API_KEY when convenient."
            ),
        )

    if normalized == "auto":
        if talor_key or legacy_key:
            return ResolvedPlayProvider(
                provider="talordata",
                talordata_api_key=talor_key or legacy_key,
                legacy_talordata_key=bool(legacy_key and not talor_key),
                configuration_note=(
                    "Detected a TalorData-style SERP token in legacy KDR_SERPAPI_API_KEY; "
                    "KDR is routing it to TalorData. Rename it to KDR_TALORDATA_API_KEY when convenient."
                    if legacy_key and not talor_key
                    else None
                ),
            )
        if serp_key:
            return ResolvedPlayProvider(provider="serpapi", serpapi_api_key=serp_key)
        return ResolvedPlayProvider(provider="public_html")

    if normalized == "talordata":
        key = talor_key or legacy_key
        if not key:
            raise PlayDiscoveryUnavailable(
                "TalorData is selected but KDR_TALORDATA_API_KEY is not configured"
            )
        return ResolvedPlayProvider(
            provider="talordata",
            talordata_api_key=key,
            legacy_talordata_key=bool(legacy_key and not talor_key),
            configuration_note=(
                "Using the TalorData-style token from legacy KDR_SERPAPI_API_KEY; "
                "rename it to KDR_TALORDATA_API_KEY when convenient."
                if legacy_key and not talor_key
                else None
            ),
        )

    if normalized == "serpapi":
        if not serp_key:
            raise PlayDiscoveryUnavailable(
                "SerpApi is selected but KDR_SERPAPI_API_KEY is not configured"
            )
        return ResolvedPlayProvider(provider="serpapi", serpapi_api_key=serp_key)

    if normalized in {"public_html", "google_play_public_html"}:
        return ResolvedPlayProvider(provider="public_html")

    raise PlayDiscoveryUnavailable(f"unsupported Play discovery provider: {requested}")


def resolve_settings_provider(settings: Settings | None = None) -> ResolvedPlayProvider:
    current = settings or get_settings()
    return resolve_play_provider(
        current.play_discovery_provider,
        talordata_api_key=current.talordata_api_key,
        serpapi_api_key=current.serpapi_api_key,
    )


def run_configured_play_discovery(
    session,
    *,
    max_providers: int,
    max_apps: int,
    client=None,
    start_index: int | None = None,
    settings: Settings | None = None,
) -> PlayDiscoveryResult:
    current = settings or get_settings()
    resolved = resolve_settings_provider(current)
    if resolved.provider == "talordata":
        return run_cbk_talordata_play_discovery(
            session,
            max_providers=max_providers,
            max_apps=max_apps,
            client=client,
            start_index=start_index,
            api_key=resolved.talordata_api_key or "",
            endpoint=current.talordata_serp_endpoint,
        )
    if resolved.provider == "serpapi":
        return run_cbk_serpapi_play_discovery(
            session,
            max_providers=max_providers,
            max_apps=max_apps,
            client=client,
            start_index=start_index,
            api_key=resolved.serpapi_api_key or "",
        )
    return run_cbk_play_discovery(
        session,
        max_providers=max_providers,
        max_apps=max_apps,
        client=client,
        start_index=start_index,
        provider="public_html",
        serpapi_api_key=None,
    )
