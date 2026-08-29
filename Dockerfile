# boreal-stand-intelligence/Dockerfile
# Reproducible container for the Project 1 batch pipeline. Matches the portfolio
# convention (MatoGrossoCarbon, LAwildfireSAR, SARFloodAnalysis): slim Python
# base, requirements installed from requirements.txt, package installed editable.
# Day-to-day development uses the shared .venv at the working directory root;
# this image is for a clean reproducible run and CI parity.

FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# rasterio, geopandas and rasterstats ship manylinux wheels bundling GDAL, so no
# system GDAL is needed here. Point-cloud system libraries (PDAL) get added when
# Module A actually consumes ALS data.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt pyproject.toml ./
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY fi_forest_data/ ./fi_forest_data/
COPY src/ ./src/
COPY config/ ./config/
COPY tests/ ./tests/
RUN pip install -e . --no-deps

# data/ and outputs/ are mounted at run time, never baked into the image.
# Default command is a health check: validate the pipeline configuration.
CMD ["python", "-m", "fi_forest_data.validate", "config/pipeline.yaml"]
