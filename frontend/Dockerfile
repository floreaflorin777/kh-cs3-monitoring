# Base image: official Python 3.12 slim. "slim" means minimal OS packages,
# which keeps the image small and the attack surface low.
FROM python:3.12-slim

# Set the working directory inside the container. Everything we copy and
# run from this point on happens relative to /app.
WORKDIR /app

# Copy ONLY requirements.txt first. This is a caching trick: if requirements
# don't change, Docker reuses the next layer (pip install) without rerunning it.
COPY requirements.txt .

# Install the Python dependencies. --no-cache-dir keeps the image smaller
# by not storing pip's download cache inside the image.
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code.
COPY . .

# Documentation only. EXPOSE does not actually publish the port; it tells
# anyone reading the Dockerfile what the container listens on by convention.
EXPOSE 5000

# Run gunicorn as the WSGI server. Bind to 0.0.0.0 so the container's
# network interface accepts connections from outside the container.
# "app:app" means: import the variable named "app" from the module "app".
CMD ["gunicorn", "--bind=0.0.0.0:5000", "--workers=2", "app:app"]