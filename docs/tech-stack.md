# Technology Stack Rationale

- **Backend:** FastAPI (Python 3.12) selected for async-friendly IO with clear typing, built-in OpenAPI generation, and strong ecosystem support for data processing integrations.
- **Frontend:** Next.js 14 with the App Router provides server-side rendering options, good developer ergonomics, and integrates smoothly with React’s component model for the dataset wizard and dashboards. Recharts renders lightweight data previews directly from ingestion summaries.
- **Package Managers:** Python managed through `venv` and pinned requirements files; frontend uses npm for alignment with Next.js defaults and GitHub Actions caching.
- **Testing & Linting:** Pytest and Ruff cover backend quality gates, while Next.js lint plus Vitest/Jest-DOM/Testing Library cover frontend unit tests. The CI workflow runs these suites on push/pull request.
- **Repository Layout:** Mono-repo with `src/backend` and `src/frontend` centralizes shared tooling and CI, simplifying orchestration of cross-cutting features like the dataset connection workflow.
- **Persistence:** SQLite stores connection definitions and ingestion job history locally; swap to PostgreSQL or another managed service when moving beyond prototypes.
- **AI Insights:** The backend calls OpenAI’s Responses API through the official `openai` SDK when `OPEN_DATA_OPENAI_API_KEY` is set. Requests are formatted with dataset summaries, and the Next.js dashboard surfaces the generated guidance.
