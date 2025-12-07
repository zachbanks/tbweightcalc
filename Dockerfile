# ---------------------------------------------------------
# 1. Base Python image
# ---------------------------------------------------------
FROM python:3.11-slim

# ---------------------------------------------------------
# 2. Install system libs for WeasyPrint + fonts + tools
# ---------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
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
    wget \
    unzip \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------
# 3. Install JetBrains Mono font
# ---------------------------------------------------------
RUN wget -qO /tmp/jbmono.zip https://download.jetbrains.com/fonts/JetBrainsMono-2.304.zip && \
    mkdir -p /usr/share/fonts/truetype/jetbrains && \
    unzip -j /tmp/jbmono.zip 'fonts/ttf/*.ttf' -d /usr/share/fonts/truetype/jetbrains && \
    fc-cache -f -v && \
    rm /tmp/jbmono.zip

# ---------------------------------------------------------
# 4. Install Pandoc + XeLaTeX
# ---------------------------------------------------------
RUN apt-get update && apt-get install -y pandoc texlive-xetex && \
    rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------
# 5. Set working directory
# ---------------------------------------------------------
WORKDIR /app

# ---------------------------------------------------------
# 6. Copy project files into image
# ---------------------------------------------------------
COPY . .

# ---------------------------------------------------------
# 7. Install Python dependencies
# ---------------------------------------------------------

# ---------------------------------------------------------
# 8. Default command
# ---------------------------------------------------------
CMD ["python", "cli.py"]
