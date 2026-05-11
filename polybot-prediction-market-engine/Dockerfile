# Stage 1: Builder
FROM python:3.12-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt
COPY . .

# Stage 2: Runtime
FROM python:3.12-slim AS runtime
RUN groupadd --gid 1000 polybot && \
    useradd --uid 1000 --gid polybot --shell /bin/bash --create-home polybot
COPY --from=builder /install /usr/local
COPY --from=builder /build /app
WORKDIR /app
RUN chown -R polybot:polybot /app
USER polybot
EXPOSE 9090
ENTRYPOINT ["python", "-m", "polybot.main"]
