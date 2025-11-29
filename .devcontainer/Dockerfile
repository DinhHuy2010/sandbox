FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Install UV package manager
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Add UV to PATH
ENV PATH="/root/.local/bin:$PATH"

# Create user huyonunix without password for security
RUN useradd -m -s /bin/bash -p '!' huyonunix && \
    mkdir -p /home/huyonunix/.local/bin && \
    cp /root/.local/bin/uv /home/huyonunix/.local/bin/ && \
    chown -R huyonunix:huyonunix /home/huyonunix && \
    echo "huyonunix ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/huyonunix && \
    chmod 0440 /etc/sudoers.d/huyonunix

# Set working directory
WORKDIR /workspaces

# Set huyonunix user
USER huyonunix
ENV PATH="/home/huyonunix/.local/bin:$PATH"

# Default command
CMD ["bash"]