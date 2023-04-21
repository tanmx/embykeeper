FROM python:3.10-slim-buster

WORKDIR /app

VOLUME ["/root/.local/share/embykeeper"]

COPY . .
RUN touch config.toml
RUN pip install -U pip && pip install .

ENTRYPOINT ["embykeeper"]
CMD ["config.toml"]
