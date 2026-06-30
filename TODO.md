- [ ] Update embedding_service.py to lazy-load SentenceTransformer (no import-time heavy load)
- [ ] Fix processing_service.py to remove duplicate create_embedding call per chunk
- [ ] Reduce Qdrant payload: stop storing chunk_text in upsert payload (and keep search working)
- [ ] (Optional) Update backend/Dockerfile to run with single uvicorn worker to reduce RAM spikes
- [x] Run a quick local smoke test: import app + call process_document on a small text file (if possible)


