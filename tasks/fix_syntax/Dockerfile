FROM python:3.12-slim

# Run as a non-root user that owns the workspace.
RUN useradd --create-home agent && mkdir /workspace && chown agent:agent /workspace
WORKDIR /workspace

# Only the broken script goes in. The reference fix in solution/ stays on the host.
COPY --chown=agent:agent sandbox/ /workspace/

USER agent
