FROM python:3.10-slim-buster

WORKDIR /app

VOLUME ["/root/.local/share/embykeeper"]

COPY . .
RUN apt update && apt install gcc -y && \
    ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && \
    echo "Asia/Shanghai" >/etc/timezone && \
    pip install -U pip && pip install .

ENTRYPOINT ["embykeeper"]
CMD ["config.toml"]
