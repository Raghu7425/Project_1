# Fly.io Deployment Runbook

This project deploys to Fly.io as one Docker image with two process groups:

- `api`: public FastAPI service
- `worker`: private background job consumer

## 1. Install and log in

```bash
fly auth login
```

## 2. Create the app

The checked-in `fly.toml` uses `distributed-job-platform` as a placeholder app name. Fly app names are globally unique, so pick your own:

```bash
fly apps create your-unique-job-platform-name
```

Then update `app = "your-unique-job-platform-name"` in `fly.toml`.

## 3. Create Postgres

```bash
fly postgres create --name your-unique-job-platform-db --region bom
fly postgres attach your-unique-job-platform-db --app your-unique-job-platform-name
```

`fly postgres attach` sets `DATABASE_URL` for the app.

## 4. Create Redis

Use Upstash Redis from Fly:

```bash
fly redis create
```

Copy the Redis URL into an app secret:

```bash
fly secrets set REDIS_URL="redis://..."
```

## 5. Set application secrets

```bash
fly secrets set JWT_SECRET="$(openssl rand -hex 32)"
```

On Windows PowerShell, use:

```powershell
$secret = -join ((48..57) + (97..102) | Get-Random -Count 64 | ForEach-Object {[char]$_})
fly secrets set JWT_SECRET="$secret"
```

## 6. Deploy

```bash
fly deploy
```

## 7. Run the database migration

```bash
fly ssh console -C "psql \$DATABASE_URL -f migrations/001_init.sql"
```

If the image does not include `psql`, run the migration from your local machine using the Postgres connection string from Fly.

## 8. Scale API and workers

```bash
fly scale count api=1 worker=1
fly scale count worker=3
```

## 9. Verify

```bash
fly status
fly logs
curl https://your-unique-job-platform-name.fly.dev/health
curl https://your-unique-job-platform-name.fly.dev/docs
```
