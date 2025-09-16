#!/bin/bash

# Customer Cleanup Script
# Deletes customers with no orders since a year ago

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
LOG_FILE="/tmp/customercleanuplog.txt"

# Change to project directory
cd "$PROJECT_DIR"

# Execute Django shell command to delete inactive customers
python manage.py shell -c "
from datetime import datetime, timedelta
from django.utils import timezone
from crm.models import Customer

# Calculate date one year ago
one_year_ago = timezone.now() - timedelta(days=365)

# Find customers with no orders since one year ago
inactive_customers = Customer.objects.filter(orders__isnull=True).union(
    Customer.objects.filter(orders__order_date__lt=one_year_ago).distinct()
)

# Count before deletion
count = inactive_customers.count()

# Delete inactive customers
inactive_customers.delete()

# Log the result
timestamp = datetime.now().strftime('%d/%m/%Y-%H:%M:%S')
with open('$LOG_FILE', 'a') as f:
    f.write(f'{timestamp} Deleted {count} inactive customers\n')

print(f'Deleted {count} inactive customers')
"
