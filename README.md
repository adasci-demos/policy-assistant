# policy-assistant

Harbourline Freight policy assistant (fictional). A small FastAPI service that answers staff
questions about the shipping and returns policy, with citations to policy sections.

All company names, policies and data in this repository are fictional and exist only for an
ADaSci course demo.

- `GET /healthz` returns `{"status":"ok"}`
- `POST /ask` with `{"question": "..."}` returns `{"answer": "...", "citations": [...], "refused": false}`

Environment: `MODEL_API_KEY` (secret), `MODEL_NAME`, optional `MODEL_BASE_URL` (any
OpenAI-compatible endpoint). Evals also need `JUDGE_MODEL`.
