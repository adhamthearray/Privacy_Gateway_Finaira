# Free shared deployment: Render + Neon

This deployment runs only the independent annotation project. It does not include the production privacy gateway, customer documents, or a customer database.

## Architecture

- **Render Free Web Service:** hosts the password-protected Gradio UI at a shared HTTPS URL.
- **Neon Free PostgreSQL:** stores append-only reviews and adjudications outside Render's ephemeral filesystem.
- **Repository JSONL:** supplies the fixed synthetic prompt dataset and is read-only at runtime.

Render Free sleeps after 15 minutes without inbound HTTP or WebSocket traffic and may take about a minute to wake. This does not lose annotations because PostgreSQL is external. Neon currently provides a free PostgreSQL tier suitable for this small research dataset. Free services do not provide production guarantees or automatic backup guarantees, so download annotation CSV backups regularly.

## 1. Create the free Neon database

1. Create a free project at <https://console.neon.tech/>.
2. In the Neon dashboard, copy the **pooled PostgreSQL connection string** for the project.
3. Ensure the connection string includes `sslmode=require`. It will resemble:

   ```text
   postgresql://USER:PASSWORD@HOST/DBNAME?sslmode=require
   ```

4. Keep the full string secret. It grants database access and must never be committed.

The application creates its three tables automatically on first startup.

## 2. Put this directory in a private Git repository

Use `finaira_laya_relevance_dataset` as the repository root. The standalone ZIP supplied with the project excludes local annotation databases, logs, caches, and passwords.

## 3. Deploy the free Render Blueprint

1. Sign in at <https://dashboard.render.com/>.
2. Choose **New → Blueprint** and connect the private repository.
3. Render detects `render.yaml` and creates the free Docker web service.
4. Enter these secret environment variables when prompted:

   - `DATABASE_URL`: the complete Neon pooled connection string.
   - `FINAIRA_AUTH_USERS`: a JSON object containing one account per reviewer, for example:

     ```json
     {"reviewer_alice":"long-random-password-1","reviewer_bob":"long-random-password-2","adjudicator":"long-random-password-3"}
     ```

5. Deploy and open the generated `https://...onrender.com` URL.

The authenticated username is automatically used as the reviewer identity. Real passwords belong only in Render secrets.

## 4. Back up and export

Use **Export review CSV** in the application after annotation sessions. For gold synchronization on a trusted local machine, set `DATABASE_URL` to the same Neon connection string and run:

```powershell
$env:DATABASE_URL = "postgresql://...?...sslmode=require"
py -3.13 scripts/sync_annotations.py
py -3.13 scripts/export_laya.py
```

Do not paste the database URL into chat, source files, screenshots, or commits.

## Local PostgreSQL-compatible test

With any PostgreSQL connection string:

```powershell
$env:DATABASE_URL = "postgresql://...?...sslmode=require"
$env:FINAIRA_AUTH_USERS = '{"reviewer":"change-this-password"}'
py -3.13 annotation_ui/app.py --host 127.0.0.1 --port 7862 --no-browser
```

Without `DATABASE_URL`, the app automatically falls back to local SQLite for development.

## Limitations of the free setup

- The Render UI sleeps after inactivity and has a cold start.
- Neon may scale database compute to zero when idle, adding a small first-query delay.
- Free plans have quotas and no production service guarantee.
- Export CSV backups regularly. If the study becomes operationally important, move to a paid database with managed backups.

