# AI Search Roadmap

The current database schema includes `search_embeddings` with `double precision[]` as a temporary local embedding store. This lets development continue before pgvector is installed everywhere.

## Next Steps

1. Add `search_documents` records for public clubs and events.
2. Add a reindex command that rebuilds documents from source rows.
3. Store embedding model and embedding version on every document.
4. Filter retrieval by visibility and user permissions before any LLM call.
5. Migrate `search_embeddings.embedding` from `double precision[]` to `vector(1536)` after pgvector is available.
6. Benchmark exact search first, then compare HNSW and IVFFlat indexes.
7. Add prompt-injection tests before using retrieved content in an assistant.

## Safety Rules

- Do not send unnecessary personal data to model providers.
- Treat retrieved content as untrusted.
- Do not expose hidden prompts.
- Add cost limits and rate limits before public use.
- Require human confirmation before destructive AI-assisted writes.
