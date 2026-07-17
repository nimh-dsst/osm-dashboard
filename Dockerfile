FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY dashboard/ /app/dashboard/

# Deployment metadata (set at build time)
ARG BUILD_TIMESTAMP=""
ARG GIT_COMMIT=""
ARG GIT_REPO=""
ARG GIT_BRANCH=""
ENV BUILD_TIMESTAMP=${BUILD_TIMESTAMP}
ENV GIT_COMMIT=${GIT_COMMIT}
ENV GIT_REPO=${GIT_REPO}
ENV GIT_BRANCH=${GIT_BRANCH}

EXPOSE 8050

CMD ["gunicorn", "dashboard.app:server", "-b", "0.0.0.0:8050", "-w", "2"]
