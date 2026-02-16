# Jira Export Server v2.1
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY config.py .
COPY jira_client.py .
COPY pdf_generator.py .
COPY server/app.py .
COPY server/word_generator.py .
COPY server/markdown_generator.py .

# Copy web interface
COPY server/templates templates/
COPY server/static static/

# Expose port
EXPOSE 5000

# Run with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "app:app"]
