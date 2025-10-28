Goal: Add 5 YouTube videos of K-pop stars being interviewed (Korean speech preferred) to the dataset today.

Success:
- 5 interview videos (not MVs/fancams), ≥3 different channels.
- Download to staging/ first; then append-only promote into dataset/ via ingest.promote (or ingest.promote_glob).
- Tag promoted items: lang=ko, domain=yt, topic=kpop_interview.
- Keep total size modest (respect daily budget); prefer 2–20 min duration.

You decide:
- Queries, channels, flags, filters; verification heuristics and rate-limit-safe settings.
Constraints:
- Tools-only via gateway. No privileged docker. Dataset is append-only (promotion only).
