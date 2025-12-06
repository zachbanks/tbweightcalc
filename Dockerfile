FROM python:3.11-slim

# 1. Install system libraries needed by WeasyPrint (cairo, pango, gobject, etc.)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libcairo2 \
        pango1.0-tools \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libpangocairo-1.0-0 \
        libgdk-pixbuf-2.0-0 \
        libgobject-2.0-0 \
        libffi8 \
        libxml2 \
        libxslt1.1 \
        shared-mime-info \
        fonts-dejavu-core \
        build-essential && \
    rm -rf /var/lib/apt/lists/*

# 2. Set working directory
WORKDIR /app

# 3. Copy your project files into the image
COPY . .

# 4. Install Python deps your code imports
#    Add anything else you import (click, rich, whatever)
RUN pip install --no-cache-dir \
    jinja2 \
    weasyprint

RUN poetry install --with dev

# 5. Default command
CMD ["python", "cli.py"]
