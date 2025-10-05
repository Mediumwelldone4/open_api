# Development Task Breakdown

## A. Project Setup & Foundations
- [x] Confirm tech stack selections (FastAPI vs Flask, React vs Next.js) and document rationale.
- [x] Initialize monorepo structure with `spec/`, `src/backend/`, `src/frontend/`, `scripts/`, and `tests/` directories.
- [x] Configure Python environment (poetry/venv) with core dependencies (FastAPI, pandas/polars) and linting tools.
- [x] Scaffold frontend project with TypeScript, routing, shared UI component library, and linting/formatting.
- [x] Set up shared CI pipeline skeleton (lint, type-check, test jobs) using GitHub Actions or equivalent.

## B. Open-Data Connection Workflow
- [x] Design API schema for dataset connections (models, validation, persistence entities).
- [x] Build backend endpoint to accept dataset configuration (portal, URL template, API key, query params).
- [x] Implement connection test service: sample request execution, error handling, response schema extraction.
- [x] Create frontend wizard for connection form with portal selector, parameter inputs, inline validation, and tooltips.
- [x] Integrate connection testing flow with JSON/XML preview widget using syntax highlighting.

## C. Data Ingestion & Processing Pipeline
- [x] Implement background task runner (Celery/RQ) with queue configuration and monitoring hooks.
- [x] Build ingestion job to fetch paginated API data, handle rate limiting, and normalize schemas.
- [x] Add persistence layer for raw payload cache (object storage or PostgreSQL) and metadata tracking.
- [x] Develop Python data processing module: cleaning, type coercion, aggregation, outlier detection.
- [x] Write automated tests covering ingestion edge cases (timeouts, malformed responses, large payloads).

## D. Visualization & UX Delivery
- [x] Define visualization presets (line, bar, table, map) mapped to schema types.
- [x] Implement backend endpoint to expose processed dataset summaries to the UI.
- [x] Build initial frontend visualization dashboard with summary statistics and sample data.
- [x] Maintain synchronized raw data viewer allowing users to switch between JSON and XML representations.
- [x] Capture user feedback hooks (e.g., flag chart, request new visualization) for future iteration.

## E. AI-Assisted Insights (Stretch Goal)
- [x] Evaluate OpenAI API integration strategy, including prompt templates and rate controls.
- [x] Create secure service for forwarding user queries with context-aware dataset summaries.
- [x] Add frontend chat interface linked to selected dataset, with citation display for returned insights.
- [ ] Implement guardrails: response truncation, error messaging, and logging for moderation.

## F. Deployment, Security, & Operations
- [ ] Provision secrets management for API keys and third-party tokens; enforce encryption at rest.
- [ ] Containerize backend and frontend services; configure docker-compose for local development.
- [ ] Set up environment-specific configurations (dev/staging/prod) with infrastructure scripts.
- [ ] Implement monitoring and alerting for ingestion jobs, API error rates, and frontend performance.
- [ ] Prepare launch checklist including documentation updates, runbooks, and rollback plan.
