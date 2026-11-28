# R8 · Latency regression after release 3.14

Release 3.14 of the "gateway" went out on 2026-11-20. `latency.csv` holds the p50 and p95
latency for each day, before and after. `endpoints.json` holds the p95 for each endpoint
before and after the release.

Reader: the release manager. They need to know if the release made things slower, by how
much, which endpoints regressed, and whether the SLO of 300 ms p95 is broken.
