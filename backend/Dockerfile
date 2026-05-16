# Same base image as the frontend. Keeps the two containers similar to
# defend in the architecture document.
FROM python:3.12-slim

WORKDIR /app

# Copy requirements first for layer caching.
COPY requirements.txt .

# Install Python dependencies. pymssql has native C bits, but its wheels
# cover linux/amd64 so we do not need build tools here.
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code.
COPY . .

# Document the listening port.
EXPOSE 5000

# Run gunicorn. Bind to 0.0.0.0 inside the container so the host port-map works.
CMD ["gunicorn", "--bind=0.0.0.0:5000", "--timeout=120", "--workers=2", "app:app"]