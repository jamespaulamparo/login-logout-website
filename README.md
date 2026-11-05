# Foundry — Django Hackathon Starter

A reusable Django foundation for an as-yet-unknown hackathon topic. It includes session-based authentication, a responsive workspace shell, generic record CRUD, and working SQLite database backup/restore utilities.

## Stack

- Python 3.11+
- Django 5.2
- SQLite for zero-configuration local development
- Django templates + vanilla CSS (no Node/Vite build required)

The frontend is intentionally kept inside Django so the project can be cloned, opened in a virtual environment, and run quickly during a hackathon.

## Windows setup (PowerShell)

```powershell
# 1. Open the project directory
cd path\to\hackathon_django_starter

# 2. Create and activate the virtual environment
py -m venv venv
.\venv\Scripts\Activate.ps1

# If PowerShell blocks activation for this terminal:
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1

# 3. Install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# 4. Create your local environment file
Copy-Item .env.example .env

# 5. Initialize the database
python manage.py migrate

# 6. Create your administrator account
python manage.py createsuperuser

# 7. Run the development server
python manage.py runserver
```

Open `http://127.0.0.1:8000/`. Sign in using the superuser account you created. The Django admin is available at `/admin/`.

## Features

### Authentication
- Django's built-in password hashing and session authentication.
- Login and POST-based logout.
- Protected workspace views.
- Admin-managed accounts; create additional users through Django admin.

### Workspace records
- Create, view, edit, and delete generic records.
- Records are scoped to the account that created them.
- This generic model is intended to be renamed or replaced once the hackathon topic is announced.

### Backup and restore
- Create a consistent SQLite snapshot using SQLite's online backup API.
- Download generated `.sqlite3` backup files.
- Restore from a compatible SQLite backup upload.
- Validate uploaded database integrity and required Django tables before restoration.
- Keep a small operation log.

**Important:** Restore replaces the current database, including users, sessions, and records. Download a current backup first. After a successful restore, the current user is signed out and may need to log in using credentials present in the restored database. The restore endpoint is intentionally limited to authenticated users in this starter; for a public deployment, restrict it to trusted administrators only.

The backup utility currently supports SQLite only. It is designed for local development and a quick hackathon prototype, not as a production disaster-recovery service. For PostgreSQL or another database, implement a database-specific backup/restore adapter and operational safeguards.

## Project structure

```text
hackathon_django_starter/
├── config/                 # Django settings and project URLs
├── workspace/              # Generic records and backup/restore views
├── templates/
│   ├── registration/       # Login template
│   └── workspace/          # Dashboard and workspace pages
├── static/css/             # Design system and responsive styling
├── backups/                # Generated local backups (gitignored)
├── manage.py
├── requirements.txt
└── .env.example
```

## Before pushing to GitHub

```powershell
git init
git add .
git commit -m "Initial Django hackathon foundation"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git
git push -u origin main
```

Never commit `.env`, `db.sqlite3`, virtual environments, or real backup files. The `.gitignore` already excludes them.

## Adapting it on hackathon day

1. Rename the project and replace the Foundry label in `templates/base.html` and `templates/registration/login.html`.
2. Identify the hackathon's core data and replace or extend `workspace.Entry`.
3. Add focused Django apps for substantial features rather than putting everything into one `views.py`.
4. Keep authentication and the shared layout unless the project requirements call for a different access model.
5. Revisit backup permissions before allowing non-admin users to restore the shared database.

## Production checklist

- Set a strong, private `SECRET_KEY`.
- Set `DEBUG=False` and configure `ALLOWED_HOSTS`.
- Use HTTPS.
- Restrict restore access to authorized administrators.
- Configure secure session and CSRF cookies.
- Use a production database and a database-appropriate backup strategy.
- Store backups outside the public web root and define retention/off-site storage.
- Run `python manage.py check --deploy` before deployment.
