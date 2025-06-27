# Yelp1 Backend Migration

This project was originally configured with SQLite. To run it with PostgreSQL,
Docker Compose now includes a `db` service using Postgres 16. Default
credentials are:

- **User**: `yelproot`
- **Password**: `yelproot`
- **Database**: `postgres`

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

