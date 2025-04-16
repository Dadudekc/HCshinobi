# Build stage
FROM python:3.11-slim as builder

WORKDIR /build
COPY requirements.txt requirements-dev.txt ./

RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -r requirements-dev.txt

# Runtime stage
FROM python:3.11-slim

# Create non-root user
RUN useradd -r -s /bin/false dreamos \
    && mkdir -p /opt/dreamos/social /var/dreamos/{content,db,logs} \
    && chown -R dreamos:dreamos /opt/dreamos /var/dreamos

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    tini \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/dreamos/social

# Copy only necessary files
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY utils/ utils/
COPY strategies/ strategies/
COPY templates/ templates/
COPY config/ config/
COPY *.py ./

# Set ownership
RUN chown -R dreamos:dreamos /opt/dreamos/social

# Switch to non-root user
USER dreamos

# Use tini as init
ENTRYPOINT ["/usr/bin/tini", "--"]

# Default command
CMD ["python", "-m", "utils.devlog_generator"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${HEALTH_CHECK_PORT}/-/healthy || exit 1 