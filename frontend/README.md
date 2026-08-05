# Frontend placeholder

The backend is intentionally usable before a frontend framework is selected.

A future React or Next.js client should consume the FastAPI OpenAPI contract from `/docs` or `/openapi.json`. Keep frontend display logic separate from the meaning stored in `DiffResult.comparison_type`; colors are presentation, while the enum carries the actual semantic classification.
