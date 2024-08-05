FROM python:3.10-slim

RUN useradd -ms /bin/bash botuser
USER botuser

WORKDIR /app
COPY --chown=botuser:botuser . /app

RUN pip install --no-cache-dir -r requirements.txt
CMD ["python", "bot.py"]
