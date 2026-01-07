# Argus du Libre

A Django application for managing and analyzing free and open-source software information with multilingual support.

The analyzing part is done in another repository: [qsos-lng](https://github.com/linagora/qsos-lng).

## Features

- Multilingual content management (English, French)
- Software catalog with categories, fields, and tags
- Metric persistence system for storing raw analysis data (GitHub stars, npm downloads, etc.)
- Analysis results with weighted scoring system
- Public-facing pages for browsing projects
- OIDC authentication support for admin interface
- Markdown content rendering

## Tech Stack

- Python 3.13
- Django 5.2.8
- PostgreSQL with psycopg3
- uv (package manager)
- ruff (linting and formatting)

## Prerequisites

- Python 3.13 or higher
- PostgreSQL 12 or higher
- [uv](https://docs.astral.sh/uv/) package manager
- gettext

### Installing uv

```bash
# macOS and Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## Installation

### 1. Clone the repository

```bash
git clone <repository-url>
cd argus_du_libre
```

### 2. Create and activate virtual environment

```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install dependencies

```bash
uv sync
```

### 4. Set up PostgreSQL database

Create a PostgreSQL database and user:

```sql
CREATE DATABASE argus_du_libre;
CREATE USER argus_user WITH PASSWORD 'your-secure-password';
ALTER ROLE argus_user SET client_encoding TO 'utf8';
ALTER ROLE argus_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE argus_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE argus_du_libre TO argus_user;
```

Then connect to the database and grant schema permissions (required for PostgreSQL 15+):

```sql
\c argus_du_libre
GRANT ALL ON SCHEMA public TO argus_user;
GRANT CREATE ON SCHEMA public TO argus_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO argus_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO argus_user;
```

### 5. Configure environment variables

Copy the example environment file and edit it with your settings:

```bash
cp .env.example .env
```

Edit `.env` and configure:

```bash
# Django Settings
SECRET_KEY=your-secret-key-here  # Generate with: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
DEBUG=True  # Set to False in production
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_NAME=argus_du_libre
DB_USER=argus_user
DB_PASSWORD=your-secure-password
DB_HOST=localhost
DB_PORT=5432

# OIDC Configuration (optional)
OIDC_ENABLED=False  # Set to True to enable OIDC authentication
```

### 6. Run database migrations

```bash
uv run python manage.py migrate
```

### 7. Create a superuser (if not using OIDC)

```bash
uv run python manage.py createsuperuser
```

### 8. Compile translation messages

```bash
uv run python manage.py compilemessages
```

### 9. Run the development server

```bash
uv run python manage.py runserver
```

The application will be available at:
- Public pages: http://localhost:8000/
- Admin interface: http://localhost:8000/admin/

## Development

### Running tests

```bash
uv run python manage.py test
```

### Code formatting and linting

The project uses ruff for code formatting and linting:

```bash
# Check for issues
uv run ruff check .

# Format code
uv run ruff format .
```

### Managing translations

#### Generate translation files

```bash
# For French
uv run python manage.py makemessages -l fr --no-location --no-obsolete

# For multiple languages
uv run python manage.py makemessages -l fr -l en --no-location --no-obsolete
```

#### Compile translation files

```bash
uv run python manage.py compilemessages
```

## OIDC Authentication

To enable OIDC authentication for the admin interface:

1. Set `OIDC_ENABLED=True` in your `.env` file
2. Configure the OIDC endpoints and credentials:

```bash
OIDC_RP_CLIENT_ID=your-client-id
OIDC_RP_CLIENT_SECRET=your-client-secret
OIDC_OP_AUTHORIZATION_ENDPOINT=https://your-oidc-provider.com/auth
OIDC_OP_TOKEN_ENDPOINT=https://your-oidc-provider.com/token
OIDC_OP_USER_ENDPOINT=https://your-oidc-provider.com/userinfo
OIDC_OP_JWKS_ENDPOINT=https://your-oidc-provider.com/jwks
```

3. Restart the server

Users authenticated via OIDC are automatically granted admin privileges.

## Production Deployment

For production deployment:

1. Set `DEBUG=False` in your `.env` file
2. Generate a strong `SECRET_KEY`
3. Configure `ALLOWED_HOSTS` with your domain names
4. Use a production-grade database configuration
5. Set up static file serving (configure `STATIC_ROOT` and run `collectstatic`)
6. Use a production WSGI server (e.g., gunicorn, uwsgi)
7. Configure HTTPS
8. Set up proper database backups

## Project Structure

```
argus_du_libre/
    argus_du_libre/     # Main Django project settings
    projects/           # Categories and fields management
    public/             # Public-facing pages
    manage.py           # Django management script
    pyproject.toml      # Python project configuration
    .env.example        # Environment variables template
```
