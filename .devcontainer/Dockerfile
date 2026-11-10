FROM mcr.microsoft.com/devcontainers/python:1-3.11-bookworm

# The base image's Yarn apt source fails signature checks, which breaks
# apt-get update when features install. Nothing here uses Yarn.
RUN rm -f /etc/apt/sources.list.d/yarn.list

# tmux keeps long evals running if VS Code disconnects from the codespace.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tmux \
    && rm -rf /var/lib/apt/lists/*

# Bake uv into the image so it's on PATH before any terminal opens.
COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /uvx /usr/local/bin/
