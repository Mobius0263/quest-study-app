# Quest Study — PostgreSQL setup guide (Windows 11, Django)

Context: the Django backend already exists and currently uses SQLite. Switch it to PostgreSQL 16+ on the Windows 11 laptop that hosts development. Do not change any app code beyond the database settings and migrations.

## 1. Install PostgreSQL 16

Run in PowerShell (admin not required for winget, but accept the installer prompts):

```
winget install PostgreSQL.PostgreSQL.16
```

This is the EDB installer and includes pgAdmin. During install, set a superuser (postgres) password and write it down. The installer does NOT add PostgreSQL to PATH by default — add `C:\Program Files\PostgreSQL\16\bin` to PATH afterwards, or use full paths for `psql` and `createdb`.

## 2. Verify the service is running

```
Get-Service postgresql*
psql -U postgres -c "SELECT version();"
```

You should see PostgreSQL 16.x. If the service isn't running, start it from Services — PostgreSQL is a running service, not a file, so a connection error usually means the service is stopped.

## 3. Create the project database and user

Do not run the app as the postgres superuser. In `psql -U postgres`:

```sql
CREATE USER queststudy_user WITH PASSWORD 'choose-a-strong-password';
CREATE DATABASE queststudy OWNER queststudy_user;
```

Host is localhost, port 5432.

## 4. Install the driver

In the project's Python virtual environment (activate it first):

```
pip install psycopg[binary]
```

## 5. Point Django at PostgreSQL

In `settings.py`, replace the SQLite DATABASES block with:

```python
import os

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "queststudy"),
        "USER": os.environ.get("DB_USER", "queststudy_user"),
        "PASSWORD": os.environ.get("DB_PASSWORD"),
        "HOST": "localhost",
        "PORT": "5432",
    }
}
```

Put `DB_PASSWORD` in a `.env` file (load it with python-dotenv or the shell) and make sure `.env` is in `.gitignore`. Never hardcode the password in `settings.py` and never commit it.

## 6. Migrate and check

```
python manage.py check --database default
python manage.py migrate
python manage.py createsuperuser
```

`createsuperuser` is only needed if the Django admin is wanted.

## 7. Verify it worked

```
python manage.py dbshell
\dt
```

The app's tables should be listed. Also confirm a `JSONField` column is stored as `jsonb` — that's where the AI-generated quiz data will live, and it's one of the reasons for using PostgreSQL over SQLite.

## Pitfalls

- SQLite test data does not carry over automatically. Start with a fresh database, or use `dumpdata` / `loaddata` if any of it matters.
- If Django can't connect, check the PostgreSQL service first, then the password and port.
- The password belongs in `.env` only.

## Done when

`python manage.py check` passes, migrations apply cleanly, `dbshell` shows the tables, and the admin login works.
