FROM python:3.12-slim

# Run as a non-root user that owns the workspace.
RUN useradd --create-home agent && mkdir /workspace && chown agent:agent /workspace
WORKDIR /workspace

# No scripts are copied here. Inspect copies each sample's broken script into
# /workspace when the sample starts. The fixes and expected outputs stay on the host.

USER agent
