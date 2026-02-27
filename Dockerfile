# ============================================================
# TechNova Support Bot — Docker Build
# Multi-stage: compile Neam → minimal runtime
# ============================================================

# --- Stage 1: Builder ---
FROM neam-lang/neamc:latest AS builder

WORKDIR /build
COPY support_bot.neam .
COPY data/ ./data/

# Compile the .neam source to bytecode
RUN neamc support_bot.neam -o support_bot.neamb

# --- Stage 2: Runtime ---
FROM neam-lang/runtime:latest

WORKDIR /home/neam

# Copy compiled bytecode and data
COPY --from=builder /build/support_bot.neamb .
COPY --from=builder /build/data/ ./data/

# Seed the SQLite database
RUN apt-get update && apt-get install -y sqlite3 curl && rm -rf /var/lib/apt/lists/*
RUN sqlite3 ./data/technova.db < ./data/seed.sql

# Create workspace directories
RUN mkdir -p workspace/tickets workspace/escalations

# Volume mounts for persistence
VOLUME ["/home/neam/workspace", "/home/neam/.neam/sessions"]

# Expose HTTP channel
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

# Run the agent
CMD ["neam-api", "--program", "support_bot.neamb", "--port", "8080", "--workers", "4"]
