FROM python:3.10-slim

RUN apt-get update && apt-get install -y gcc libpq-dev

RUN useradd -ms /bin/bash botuser

COPY --chown=botuser:botuser . ./app

WORKDIR /app

CMD ["bash", "/start.sh"]