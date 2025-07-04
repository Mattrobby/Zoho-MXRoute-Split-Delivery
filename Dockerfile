FROM python:3.11-slim

# Install cron
RUN apt-get update && apt-get install -y cron && rm -rf /var/lib/apt/lists/*

# Copy python files
COPY main.py /app/main.py
COPY mxroute.py /app/mxroute.py
COPY zoho.py /app/zoho.py
COPY requirements.txt /app/requirements.txt
COPY entrypoint.sh /app/entrypoint.sh

# Install dependencies
RUN pip install -r /app/requirements.txt

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

# Set default cron schedule
ENV CRON_SCHEDULE="*/5 * * * *"
ENV PYTHON_SCRIPT="/app/main.py"

ENTRYPOINT ["/app/entrypoint.sh"]
