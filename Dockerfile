FROM python:3.10-slim

RUN apt-get update && apt-get install -y gcc libpq-dev

<<<<<<< HEAD
RUN useradd -ms /bin/bash -u 1000 botuser
USER botuser
=======
RUN useradd -ms /bin/bash botuser

COPY --chown=botuser:botuser . ./app
>>>>>>> df73cb71ae208c26da4ffc907a9fda5891c587ae

WORKDIR /app

CMD ["bash", "/start.sh"]