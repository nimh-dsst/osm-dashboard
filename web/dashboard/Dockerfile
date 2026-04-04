ARG BASE_IMAGE=osm/osm_base
FROM ${BASE_IMAGE}
COPY web/dashboard/ /app
ENV LOCAL_DATA_PATH=/opt/data/matches.parquet
COPY ./dashboard_data/matches.parquet /opt/data/matches.parquet

# Deployment metadata (set at build time, available at runtime)
ARG BUILD_TIMESTAMP=""
ARG GIT_COMMIT=""
ARG GIT_REPO=""
ARG GIT_BRANCH=""
ENV BUILD_TIMESTAMP=${BUILD_TIMESTAMP}
ENV GIT_COMMIT=${GIT_COMMIT}
ENV GIT_REPO=${GIT_REPO}
ENV GIT_BRANCH=${GIT_BRANCH}

CMD ["streamlit", "run", "streamlit_app.py"]
