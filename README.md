# Yelp1 Backend Migration

This project was originally configured with SQLite. To run it with PostgreSQL,
Docker Compose now includes a `db` service using Postgres 16. Default
credentials are:

- **User**: `yelproot`
- **Password**: `yelproot`
- **Database**: `postgres`

The `db` service sets `POSTGRES_HOST_AUTH_METHOD=md5` so host connections always
require a password.

The Django services read these credentials via environment variables and use
PostgreSQL when `DB_ENGINE=postgres`.

## Migrating existing data

A helper script is provided to migrate data from the previous SQLite database
to PostgreSQL:

```bash
python backend/scripts/migrate_sqlite_to_postgres.py
```

The script dumps all data using the SQLite configuration and then loads it into
the Postgres database after applying migrations. Ensure the Postgres service is
running before executing the script.

After seeding the `AutoResponseSettings` table with the initial row (`id=1`),
update the PostgreSQL sequence so new records receive the next available ID:

```sql
SELECT setval(pg_get_serial_sequence('webhooks_autoresponsesettings','id'),
              (SELECT MAX(id) FROM webhooks_autoresponsesettings));
```

Migration `0035_update_autoresponsesettings_sequence` runs this query
automatically when migrations are applied.

## Connecting from outside Docker

If you want to use a local psql client or GUI to access the database, expose
the Postgres port in `backend/docker-compose.yml`:

```yaml
  db:
    image: postgres:16
    ports:
      - "5433:5432"
```

Restart the stack with `docker compose up -d`. The database is then available
at `localhost:5433` with the credentials listed above.

## Persisting RQ jobs

RQ uses Redis to queue background jobs. If the stack is restarted and Redis
is not configured with a volume, any scheduled jobs are lost. The
`redis` service in `backend/docker-compose.yml` now mounts the named volume
`redis_data` so RQ's queue survives container restarts:

```yaml
  redis:
    image: redis:7
    restart: unless-stopped
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

After updating the compose file, run `docker compose up -d` again to apply the
changes. Scheduled tasks and other Redis data will persist between restarts.

If you need additional safeguards against duplicate jobs, assign deterministic
`job_id` values when enqueuing RQ tasks. For example, hash the `lead_id` and
message text and pass that value as the `job_id`. Attempting to enqueue the same
task again with the identical `job_id` simply reuses the existing job and no new
task is created.

## Webhook event processing

When events are fetched from Yelp after a lead is created, the backend ignores
consumer messages that occurred **before** the lead was processed **unless** the
message contains a phone number. This prevents the initial lead message from
cancelling pending auto-response tasks, while still capturing phone numbers that
might appear in that first message. Events created after
`ProcessedLead.processed_at` always trigger phone number logic.

Phone numbers found in a lead's `additional_info` field also trigger the "real
phone provided" flow when the lead is first processed.

When a business account is authorized, the callback fetches
`/businesses/{business_id}/lead_ids` for each connected business and stores the
returned IDs in the local `ProcessedLead` table.

During webhook processing the backend no longer queries Yelp. Instead it checks
if the incoming `lead_id` exists in `ProcessedLead`. If not, the update is
tagged as `"NEW_LEAD"` and the ID is saved so subsequent events are treated as
already processed.

Lead details and events are recorded for every lead even when automatic
responses are disabled for a business.

## Frontend API configuration

When building the React frontend for production, point it at your deployed
backend by setting the `REACT_APP_API_BASE_URL` environment variable:

```bash
REACT_APP_API_BASE_URL=http://46.62.139.177:8000 npm run build
```

If this variable is omitted, the app falls back to `http://46.62.139.177:8000/api`.

## Task log cleanup

Old records in `CeleryTaskLog` can grow quickly. Remove entries older than 30 days
with the management command:

```bash
python backend/manage.py cleanup_celery_logs --days 30
```

This command is executed automatically every day via the RQ scheduler using the
`cleanup-celery-logs` schedule.

## RQ Dashboard

The compose file includes a `rqdash` service running [RQ Dashboard](https://github.com/rq/rq-dashboard).
RQ uses Redis database 1, so `rqdash` connects to `redis://redis:6379/1`.
Start it and visit <http://localhost:9181> to monitor queued jobs:

```bash
docker compose up -d rqdash
```

## RQ Scheduler Dashboard

To inspect jobs scheduled with `rq-scheduler`, the compose file includes a
`scheduler-dashboard` service built from the same Docker image as the other
backend components. The service automatically patches
`rq_scheduler_dashboard` at runtime so it works with newer Flask versions.
Start it and open
<http://localhost:9182> to view scheduled tasks:

```bash
docker compose up -d scheduler-dashboard
```

## Redis Commander

To inspect the Redis database through a web interface, the compose file includes
a `redis-commander` service. It is configured to use database 1 so it shows RQ's
queues. Start it and visit <http://localhost:8081>:

```bash
docker compose up -d redis-commander
```


