# API refresh matrix

This matrix documents the intended refresh ownership.  Browser polling is
limited to read-only local API routes; collectors and spiders remain the only
components that contact external platforms.

| API | Page / trigger | Browser cadence | Backend / external source | Cache / stale | Polling policy |
| --- | --- | --- | --- | --- | --- |
| `/api/portal/dashboard` | Home | 60s | MySQL read model | in-process + optional `api_snapshots` | stale response while refresh runs |
| `/api/portal/schemes` | Scheme hall | on entry, search, page change | MySQL | none | user-triggered only |
| `/api/portal/analysis` | Analysis | on entry / filter | MySQL aggregates | request cache | user-triggered only |
| `/api/portal/heatmap` | Heatmap | 60s | MySQL aggregates | play-type cache | hidden tab paused |
| `/api/portal/results` | Results | 60s only while today has pending rows | MySQL | stale allowed | stop after settlement |
| `/api/portal/users` | User center | on entry, search, filter, page | MySQL | browser cache | 450ms debounce, no interval |
| `/api/portal/user/{platform}/{user}` | User detail | on entry; pending retry | MySQL | browser cache | max 15 retries, 2s backoff |
| `/api/matches` | Match list | 30s | local read model | in-memory | hidden tab paused |
| `/api/matches/{id}` | Match detail | 30–60s by match state | local read model | detail cache | completed matches stop |
| `/api/matches/{id}/context` | Match context | 600s | collector snapshot | context cache | user switch triggers one load |
| `/api/matches/{id}/news` | Match news | 180s | collector snapshot | news cache | no 30s polling |
| `/api/platform/list` | Sidebar status | 60–120s | MySQL sync log | in-memory | hidden tab paused |

Every refresh must be single-flight per method + URL + parameters.  A failed
refresh preserves the last successful payload and exposes a freshness marker;
it must not replace rendered data with an empty array or object.

