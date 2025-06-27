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

## Connecting from outside Docker

If you want to use a local psql client or GUI to access the database, expose
the Postgres port in `backend/docker-compose.yml`:

```yaml
  db:
    image: postgres:16
    ports:
      - "5432:5432"
```

Restart the stack with `docker compose up -d`. The database is then available
at `localhost:5432` with the credentials listed above.

