FROM python:3.10-slim-buster AS builder

WORKDIR /src
COPY . .

RUN apt update && apt install gcc -y \
    && python -m venv /opt/venv \
    && . /opt/venv/bin/activate \
    && pip install --no-cache-dir -U pip setuptools wheel \
    && pip install --no-cache-dir .

FROM python:3.10-slim-buster
COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
RUN touch config.toml \
    && ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    && echo "Asia/Shanghai" > /etc/timezone
ENV PATH="/opt/venv/bin:$PATH"

ENTRYPOINT ["embykeeper", "--session-dir", "/app"]