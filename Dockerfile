FROM python:3.10-slim

RUN apt-get update && apt-get install -y gcc libpq-dev

RUN useradd -ms /bin/bash -u 1000 botuser

COPY ./start.sh /start.sh

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

CMD ["bash", "/start.sh"]