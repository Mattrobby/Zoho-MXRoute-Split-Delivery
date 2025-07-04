#!/bin/bash

echo "Cron schedule set to '${CRON_SCHEDULE}'"

# Set up cron job (note: cron.d files need username field)
echo "${CRON_SCHEDULE} root cd /app && python ${PYTHON_SCRIPT} >> /var/log/cron.log 2>&1" > /etc/cron.d/python-cron

# Run the Python script once immediately (without cron schedule part)
cd /app && python ${PYTHON_SCRIPT}

# Give execution rights to cron file
chmod 0644 /etc/cron.d/python-cron

# Create log file
touch /var/log/cron.log

# Start cron and tail logs
cron && tail -f /var/log/cron.log
