FROM python:3.10-slim

RUN apt-get update && apt-get install -y gcc libpq-dev

RUN useradd -ms /bin/bash -u 1000 botuser

COPY ./start.sh /start.sh

WORKDIR /app

CMD ["bash", "/start.sh"]