FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install UV package manager
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Add UV to PATH
ENV PATH="/root/.local/bin:$PATH"

# Set working directory
WORKDIR /workspaces

# Default command
CMD ["bash"]
