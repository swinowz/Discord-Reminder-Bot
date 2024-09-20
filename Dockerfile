#!/usr/bin/env python3

FROM python:3.10-slim

RUN apt-get update && apt-get install -y gcc libpq-dev

RUN useradd -ms /bin/bash -u 1000 botuser
USER botuser

WORKDIR /app

COPY --chown=botuser . /app

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

CMD ["python", "bot.py"]