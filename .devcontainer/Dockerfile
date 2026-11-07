FROM mcr.microsoft.com/devcontainers/python:1-3.11-bookworm

# Bake uv into the image so it's on PATH before any terminal opens.
COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /uvx /usr/local/bin/
