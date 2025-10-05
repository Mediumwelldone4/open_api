# Open Data Insight Platform PRD

## 1. Product Summary
A web application that ingests datasets from public open-data APIs, processes them in Python, and presents actionable visualizations to end users. The platform streamlines connecting to heterogeneous government or civic datasets, performing server-side analysis, and surfacing interactive charts with optional AI-assisted insights.

## 2. Objectives & Success Metrics
- **Primary Goal:** Fetch a specified open-data dataset, analyze it, and deliver visual insights in the web UI.
- **Success Metric 1:** Successful data retrieval and visualization for at least one dataset per targeted portal.
- **Success Metric 2:** Analysis pipeline completes within acceptable latency (target: <60 seconds for datasets up to 100k rows).
- **Success Metric 3:** Optional OpenAI integration provides natural-language summaries or answers for at least 80% of user queries about the loaded data.

## 3. Target Users & Needs
- **Civic data analysts** who require quick exploration of publicly available data without building one-off scripts.
- **Non-technical stakeholders** who need digestible dashboards derived from complex datasets.
- Users must be able to provide API credentials (key, base URL, dataset id) and receive trustworthy insights without manual preprocessing.

## 4. Key Functional Requirements
1. **Data Source Registration UI**
   - Provide a guided form where the user selects the open-data portal (autocomplete with common portals, allow custom entry) and supplies dataset identifier, request URL template, API key, and parameter descriptions (e.g., date range, region).
   - Validate required fields client-side, surface inline help/tooltips, and persist the configuration for reuse after a successful connection test.
2. **API Connection & Preview**
   - Backend validates credentials by issuing a sample request and returns status plus response metadata (record count, schema).
   - UI displays the raw payload in a toggleable JSON/XML viewer with syntax highlighting so users can confirm the dataset.
   - Allow users to adjust request parameters and re-test before finalizing the connection.
3. **Data Ingestion & Processing**
   - Backend fetches data via HTTP, handling pagination, rate limits, and schema normalization.
   - Python-based processing handles large payloads using streaming or chunked loading.
   - Data transformations include cleaning, type coercion, aggregation, and outlier detection.
4. **Visualization Delivery**
   - Generate charts (line, bar, map, table) driven by dataset schema and user-selected dimensions.
   - Support filtering, sorting, drill-down interactions, and link from the viewer to visualizations for traceability.
5. **AI-Assisted Analysis (Stretch Goal)**
   - Allow users to query data conversationally.
   - Summaries or answers produced via OpenAI API with safeguards against hallucination (include data citations where possible).

## 5. User Experience Flow
1. Onboarding: user logs in, lands on “Connect Dataset” page, and starts the guided form to choose the source portal and dataset.
2. Input Collection: user enters API key, base URL, dataset path, required query parameters, and any filters; inline validation ensures completeness.
3. Connection Test: system issues a sample request; on success, the UI presents a JSON/XML preview with schema summary and lets the user iterate on parameters.
4. Processing: user confirms the configuration and triggers a full data fetch; backend queues a job to ingest and process the dataset.
5. Visualization: once processing finishes, UI notifies the user, retains access to the raw payload viewer, and renders default dashboards. Users can adjust filters or chart types.
6. AI Insights (optional): user opens the AI assistant panel to ask natural-language questions about the dataset; responses include supporting statistics.

## 6. Data Sources & Integrations
- Primary integration: user-specified public open-data REST APIs (e.g., data.go.kr, data.gov, municipally maintained portals).
- Authentication: API key or token stored securely; no refresh token flows expected.
- Optional integration: OpenAI API (`gpt-4` or successors) for narrative insights.

## 7. Technical Considerations
- **Backend stack:** Python (FastAPI or Flask) for API orchestration and data processing; leverage pandas or polars for analysis.
- **Frontend stack:** React or Next.js to deliver responsive dashboards (use D3.js, Vega-Lite, or ECharts for visualization).
- **Data storage:** Temporary persistence in PostgreSQL or object storage (Parquet/CSV) to cache processed datasets.
- **Scalability:** Implement background workers (Celery, RQ) for long-running ingestion tasks; monitor job execution and retry failed fetches.
- **Security:** Encrypt stored API keys, enforce role-based access, log access attempts.

## 8. Risks & Open Questions
- Variability in dataset schemas may require dynamic visualization generation—define a fallback for unsupported types.
- Open-data APIs may impose rate limits or inconsistent pagination—need a retry/backoff strategy.
- Clarify whether datasets should be refreshed on schedule or only on-demand.
- Confirm legal constraints for storing and redistributing public data.
