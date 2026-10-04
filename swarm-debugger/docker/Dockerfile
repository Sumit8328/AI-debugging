FROM python:3.12-slim

# Install system dependencies and security sandboxing essentials
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create unprivileged sandbox user
RUN useradd -m -s /bin/bash sandboxuser

WORKDIR /sandbox

# Pre-install pytest and essential testing tools
RUN pip install --no-cache-dir \
    pytest>=8.0.0 \
    pytest-timeout>=2.3.0

USER sandboxuser

# Default command: execute pytest in mounted repo directory
CMD ["pytest", "-v"]
