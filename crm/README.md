# CRM Celery Setup Guide

This guide explains how to set up and run the CRM system with Celery for automated report generation.

## Prerequisites

1. **Redis Server**: Install and start Redis server
2. **Python Dependencies**: Install all required packages
3. **Django Database**: Run migrations to set up the database

## Installation Steps

### 1. Install Redis

#### Ubuntu/Debian:
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

#### macOS (with Homebrew):
```bash
brew install redis
brew services start redis
```

#### CentOS/RHEL:
```bash
sudo yum install redis
sudo systemctl start redis
sudo systemctl enable redis
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run Database Migrations

```bash
python manage.py migrate
```

### 4. Start Celery Worker

In a terminal window, start the Celery worker:

```bash
celery -A crm worker -l info
```

### 5. Start Celery Beat (Scheduler)

In another terminal window, start Celery Beat:

```bash
celery -A crm beat -l info
```

### 6. Start Django Development Server

In a third terminal window, start the Django server:

```bash
python manage.py runserver
```

## Verification

### Check Celery Worker Status

The Celery worker should show output like:
```
[2024-01-01 10:00:00,000: INFO/MainProcess] Connected to redis://localhost:6379/0
[2024-01-01 10:00:00,000: INFO/MainProcess] mingle: searching for neighbors
[2024-01-01 10:00:00,000: INFO/MainProcess] mingle: all alone
[2024-01-01 10:00:00,000: INFO/MainProcess] celery@hostname ready.
```

### Check Celery Beat Status

The Celery Beat should show output like:
```
[2024-01-01 10:00:00,000: INFO/MainProcess] beat: Starting...
[2024-01-01 10:00:00,000: INFO/MainProcess] beat: Scheduler: Sending due task generate-crm-report
```

### Verify Report Generation

Check the report log file:

```bash
tail -f /tmp/crm_report_log.txt
```

You should see entries like:
```
2024-01-01 06:00:00 - Report: 150 customers, 45 orders, $1250.50 revenue
```

## Scheduled Tasks

The system is configured to generate CRM reports:

- **Frequency**: Every Monday at 6:00 AM UTC
- **Task**: `crm.tasks.generate_crm_report`
- **Log File**: `/tmp/crm_report_log.txt`

## Manual Task Execution

To manually trigger a report generation:

```bash
python manage.py shell
```

Then in the shell:
```python
from crm.tasks import generate_crm_report
result = generate_crm_report.delay()
print(result.get())
```

## Troubleshooting

### Redis Connection Issues

If you see Redis connection errors:
1. Ensure Redis is running: `redis-cli ping` (should return "PONG")
2. Check Redis configuration in `crm/settings.py`
3. Verify Redis is accessible on `localhost:6379`

### Task Execution Issues

If tasks are not executing:
1. Check that both Celery worker and Beat are running
2. Verify the task is registered: `celery -A crm inspect registered`
3. Check the Celery Beat schedule: `celery -A crm beat --dry-run`

### GraphQL Connection Issues

If GraphQL queries fail:
1. Ensure Django server is running on `http://localhost:8000`
2. Check that the GraphQL endpoint is accessible
3. Verify the CRM models and schema are properly configured

## Configuration Files

- **Celery Configuration**: `crm/celery.py`
- **Task Definitions**: `crm/tasks.py`
- **Settings**: `crm/settings.py`
- **Dependencies**: `requirements.txt`

## Log Files

- **CRM Reports**: `/tmp/crm_report_log.txt`
- **CRM Heartbeat**: `/tmp/crm_heartbeat_log.txt`
- **Low Stock Updates**: `/tmp/low_stock_updates_log.txt`
- **Customer Cleanup**: `/tmp/customercleanuplog.txt`
