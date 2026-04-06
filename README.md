# E-Ticketing System

A comprehensive E-Ticketing System built with Django REST Framework, featuring both **Support Ticket Management** and **Event Ticket Booking** capabilities.

## Features

### Support Ticket System
- Create, track, and manage support tickets
- Auto-assignment of tickets to agents (round-robin)
- Ticket status workflow: Open → In Progress → Waiting → Resolved → Closed
- Priority levels: Low, Medium, High, Critical
- Comments (public and internal)
- File attachments
- Ticket statistics and analytics
- CSV export

### Event Ticket System
- Create and manage events with ticket types
- Event publishing workflow
- Booking system with unique booking codes
- Payment processing
- QR code generation for tickets
- Booking cancellation with inventory restoration
- Event reminders via Celery beat

### Authentication & Authorization
- JWT-based authentication (access + refresh tokens)
- Role-based access control (Admin, Agent, Customer, Event Organizer)
- Email verification on registration
- Password reset via email
- Object-level permissions

### Additional Features
- Real-time notifications (in-app + email)
- Async email processing with Celery + Redis
- Comprehensive filtering, searching, and ordering
- Pagination and rate limiting
- Auto-generated API documentation (Swagger/ReDoc)
- Docker support with PostgreSQL, Redis, Celery

## Tech Stack

- **Backend**: Django 5.0, Django REST Framework
- **Database**: PostgreSQL 16
- **Cache/Broker**: Redis 7
- **Async Tasks**: Celery
- **Authentication**: JWT (djangorestframework-simplejwt)
- **API Docs**: drf-spectacular (OpenAPI 3.0)
- **Containerization**: Docker + Docker Compose

## Quick Start (Docker)

```bash
# 1. Clone the repository
git clone <repo-url>
cd eticket-system

# 2. Copy environment file
cp .env.example .env

# 3. Start all services
docker-compose up --build

# 4. Run migrations (in another terminal)
docker-compose exec web python manage.py migrate

# 5. Create superuser
docker-compose exec web python manage.py createsuperuser

# 6. Access the API
# API: http://localhost:8000/api/
# Admin: http://localhost:8000/admin/
# Swagger Docs: http://localhost:8000/api/docs/
# ReDoc: http://localhost:8000/api/redoc/
```

## Manual Setup

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up environment
cp .env.example .env
# Edit .env with your settings

# 4. Run migrations
python manage.py migrate

# 5. Create superuser
python manage.py createsuperuser

# 6. Start development server
python manage.py runserver

# 7. Start Celery worker (in another terminal)
celery -A core worker -l info

# 8. Start Celery beat (in another terminal)
celery -A core beat -l info
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Debug mode | `True` |
| `SECRET_KEY` | Django secret key | - |
| `ALLOWED_HOSTS` | Allowed hosts | `localhost,127.0.0.1` |
| `DB_ENGINE` | Database engine | `django.db.backends.postgresql` |
| `DB_NAME` | Database name | `eticket_db` |
| `DB_USER` | Database user | `postgres` |
| `DB_PASSWORD` | Database password | `postgres` |
| `DB_HOST` | Database host | `db` |
| `DB_PORT` | Database port | `5432` |
| `REDIS_URL` | Redis connection URL | `redis://redis:6379/0` |
| `JWT_ACCESS_TOKEN_LIFETIME` | Access token lifetime (minutes) | `60` |
| `JWT_REFRESH_TOKEN_LIFETIME` | Refresh token lifetime (minutes) | `1440` |
| `EMAIL_BACKEND` | Email backend | `console` |
| `EMAIL_HOST` | SMTP host | `smtp.gmail.com` |
| `EMAIL_PORT` | SMTP port | `587` |
| `EMAIL_HOST_USER` | SMTP user | - |
| `EMAIL_HOST_PASSWORD` | SMTP password | - |
| `DEFAULT_FROM_EMAIL` | From email address | `noreply@eticket.com` |
| `FRONTEND_URL` | Frontend URL | `http://localhost:3000` |
| `CORS_ALLOWED_ORIGINS` | CORS origins | `http://localhost:3000` |

## Project Structure

```
core/                    # Main Django project
    settings/            # Split settings (base, dev, prod)
    urls.py              # Main URL configuration
    celery.py            # Celery configuration
accounts/                # User management & authentication
support_tickets/         # Support ticket system
event_tickets/           # Event ticket & booking system
notifications/           # Notifications & email system
    templates/emails/    # HTML email templates
common/                  # Shared utilities & permissions
tests/                   # Test suite
```

## API Endpoints

### Authentication
```
POST   /api/auth/register/              Register new user
POST   /api/auth/login/                 Login (get JWT tokens)
POST   /api/auth/token/refresh/         Refresh access token
POST   /api/auth/token/verify/          Verify token
GET    /api/auth/verify-email/<uid>/<token>/  Verify email
POST   /api/auth/password-reset/        Request password reset
POST   /api/auth/password-reset-confirm/ Reset password
POST   /api/auth/change-password/       Change password
GET    /api/auth/profile/               Get profile
PATCH  /api/auth/profile/               Update profile
```

### Users (Admin only)
```
GET    /api/users/                      List all users
GET    /api/users/<id>/                 Get user detail
PATCH  /api/users/<id>/                 Update user
DELETE /api/users/<id>/                 Delete user
```

### Support Tickets
```
GET/POST  /api/support/categories/      List/Create categories
GET       /api/support/categories/<id>/ Get category
GET/POST  /api/support/tickets/         List/Create tickets
GET       /api/support/tickets/<id>/    Get ticket detail
PATCH     /api/support/tickets/<id>/    Update ticket
DELETE    /api/support/tickets/<id>/    Delete ticket
POST      /api/support/tickets/<id>/assign/         Assign agent
POST      /api/support/tickets/<id>/change_status/  Change status
POST      /api/support/tickets/<id>/comments/       Add comment
POST      /api/support/tickets/<id>/attachments/    Upload attachment
GET       /api/support/tickets/stats/               Statistics
GET       /api/support/tickets/export/              Export CSV
```

### Events
```
GET/POST  /api/events/categories/       List/Create categories
GET       /api/events/categories/<id>/  Get category
GET/POST  /api/events/                  List/Create events
GET       /api/events/<slug>/           Get event detail
PATCH     /api/events/<slug>/           Update event
DELETE    /api/events/<slug>/           Delete event
POST      /api/events/<slug>/publish/   Publish event
GET       /api/events/stats/            Statistics
GET       /api/events/upcoming/         Upcoming events
GET/POST  /api/events/<slug>/ticket-types/  List/Create ticket types
```

### Bookings
```
GET/POST  /api/bookings/                List/Create bookings
GET       /api/bookings/<id>/           Get booking detail
POST      /api/bookings/<id>/cancel/    Cancel booking
GET       /api/bookings/my_bookings/    My bookings
GET       /api/bookings/export/         Export CSV
GET/POST  /api/bookings/<id>/payments/  List/Create payments
```

### Notifications
```
GET    /api/notifications/              List notifications
GET    /api/notifications/<id>/         Get notification
POST   /api/notifications/<id>/mark_read/    Mark as read
POST   /api/notifications/mark_all_read/     Mark all read
GET    /api/notifications/unread_count/      Unread count
```

### Dashboard & Docs
```
GET    /api/dashboard/                  Combined dashboard stats
GET    /api/docs/                       Swagger UI
GET    /api/redoc/                      ReDoc UI
GET    /api/schema/                     OpenAPI schema (JSON/YAML)
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific app tests
pytest tests/accounts/
pytest tests/support_tickets/
pytest tests/event_tickets/

# Run without coverage
pytest --no-cov -v
```

## User Roles

| Role | Permissions |
|------|-------------|
| **Admin** | Full access to everything |
| **Agent** | View/assign/update support tickets, view all tickets they're involved with |
| **Customer** | Create support tickets, view own tickets, book events, manage own bookings |
| **Organizer** | Create/manage own events, view bookings for own events, publish events |

## Ticket Workflow

```
Support Ticket:  Open → In Progress → Waiting → Resolved → Closed
Event Booking:   Pending → Confirmed → (Cancelled / Refunded)
```

## License

MIT
