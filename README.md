## Reviews Reporting API Take-Home

This project ingests a mock Reviews CSV dataset into a relational database and exposes a simple HTTP API that returns CSV reports for common ad-hoc data requests from the Legal & Data Governance stakeholders.

### Tech stack

- **Language**: Python 3.11+
- **Web framework**: FastAPI
- **ORM**: SQLAlchemy 2.x
- **Database**: Postgres (via Docker Compose)

### High-level flow

1. **Ingestion**: `POST /ingest` endpoint accepts CSV uploads, validates, deduplicates (Last Write Wins), and upserts into the database.
2. **Data model**: The schema is modeled around three core entities:
   - `users` – reviewer identity and contact fields
   - `businesses` – business identifiers and names
   - `reviews` – individual reviews linked to a user and a business
3. **Reporting API**: FastAPI endpoints allow:
   - looking up reviews for a given business
   - looking up reviews written by a given user
   - retrieving user account information
   Each endpoint returns a CSV file suitable for legal/governance workflows.

### Running (Docker Compose)

1. **Start Postgres + API**

```bash
docker compose up --build
```

Keep this running. The API will be available at `http://localhost:8000`.

2. **Health check** (new terminal)

```bash
curl http://localhost:8000/health
```

Expected: `{"status":"ok"}`

3. **Ingest the demo CSV** (new terminal)

```bash
curl -X POST "http://localhost:8000/ingest" -F "file=@data/tp_reviews.csv"
```

Expected: JSON summary with row counts.

4. **Download CSV reports (what Legal would do)**

- **Browser** (downloads a CSV file):
  - `http://localhost:8000/reports/reviews/by-business?business_id=24a6a92a-f745-455f-b669-f2f02842039f`
  - `http://localhost:8000/reports/reviews/by-user?user_id=9f51330e-f123-48b6-88fb-00020e824fc2`
  - `http://localhost:8000/reports/users/9f51330e-f123-48b6-88fb-00020e824fc2`

- **curl** (save to file):

```bash
curl "http://localhost:8000/reports/reviews/by-business?business_id=24a6a92a-f745-455f-b669-f2f02842039f" -o artisan_reviews.csv
```

5. **Run tests (against Postgres)**

```bash
docker compose run --rm test
```

6. **Run governance check**

```bash
docker compose run --rm governance
```

7. **Shut down**

```bash
docker compose down
```

**Note**: Postgres data is persisted in a Docker volume (`postgres_data`).  
If you want to wipe the database completely (fresh start), run:

```bash
docker compose down -v
```

### `POST /ingest` (notes)

Uploads a reviews CSV, applies validation + last-write-wins deduplication, and upserts into Postgres.
In production, you’d typically protect this endpoint and trigger ingestion via orchestration or file-drop events.

### Design choices (brief)

- **Postgres via Docker Compose**: production-like persistence/concurrency and consistent behavior across dev/test.
- **Normalised schema**: separating users, businesses and reviews avoids duplication and makes common legal queries efficient.
- **CSV responses**: legal/governance teams often need extract-style outputs; CSV is simple, portable and easy to ingest downstream.

### Data governance: classification & PII handling

- **Field classification**:
  - `users.email`, `reviews.ip_address`: **PII** (direct identifiers)
  - `users.name`, `users.country`: **SENSITIVE** (quasi-identifying)
  - All other fields: **NON_SENSITIVE**

- **Classification is enforced via code** (`app/classification.py`):
  - Every column in the database schema is explicitly classified
  - Helper functions: `get_pii_columns()`, `get_sensitive_columns()`

- **Governance check script** (`scripts/governance_check.py`):
  ```bash
  docker compose run --rm governance
  ```
  This script validates:
  - ✓ All database columns have a classification
  - ✓ No stale classifications for removed columns
  
Returns exit code 0 (pass) or 1 (fail).

- **Future production enhancements**:
  - Sync classifications to a data catalog (Collibra, Alation)
  - Use labels to drive view-based masking for non-Legal roles
  - Automated PII audit reports

### Testing

Tests run against **Postgres** (environment parity with the app):

```bash
docker compose run --rm test
```

They cover CSV response generation, ingestion, and the main report endpoints.

### Orchestration & lineage (Airflow-friendly)

- **Ingestion runs**:
  - Each `POST /ingest` call creates an `ingestion_runs` row with:
    - `source_path`, `started_at`, `finished_at`, `status`,
    - `rows_read`, `rows_inserted`, `rows_skipped`.
  - All reviews ingested in that run are linked back to the corresponding `ingestion_runs.id`.
- **Scheduler integration**:
  - The endpoint returns HTTP 500 on failure, allowing orchestrators (Airflow, etc.) to detect failures and retry/alert.
  - In a real deployment, an orchestrator would trigger ingestion via the API or a file-drop event (S3 trigger).
- **Idempotency**:
  - The ingestion uses `db.merge()` (upsert) so re-uploading the same CSV produces the same final state.
  - Last Write Wins (LWW) deduplication ensures the latest version of each review is kept.

### Observability

- **Ingestion**:
  - The `POST /ingest` endpoint logs when a run starts, and on success or failure, along with row-count metrics.
  - Returns a JSON summary with rows read/inserted/skipped and skip reasons.
- **API endpoints**:
  - The FastAPI app logs startup and successful health checks.
  - Reporting endpoints log which report was requested (by business/user) and how many rows were returned.
This keeps a basic audit trail of ingestions and report usage without adding extra infrastructure.

### Performance & scaling considerations

**Current implementation** (suitable for ~10K-100K rows):
- Postgres via Docker Compose — persistent and supports concurrency
- In-memory LWW buffer — works well for CSVs that fit in memory
- `db.merge()` row-by-row — simple, correct, adequate for small batches

**For larger scale (1M+ rows)**, I would:
- **Database**: Switch to Postgres/BigQuery (change `DATABASE_URL` env var)
- **Bulk upserts**: Use `INSERT ... ON CONFLICT DO UPDATE` instead of row-by-row merge
- **Streaming ingestion**: Process CSV in chunks instead of loading entire file to memory
- **Async processing**: Queue large uploads (e.g., Celery + Redis) and process in background
- **Indexing**: Add indexes on frequently queried columns (already have on `user_id`, `business_id`, `rating`)

### Production deployment notes

This repo uses Postgres in Docker Compose for a production-like local environment.
In a real production deployment, use a managed Postgres instance or a warehouse (e.g., BigQuery) and manage schema changes via migrations (e.g., Alembic).



