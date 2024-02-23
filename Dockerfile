
FROM python:3.12

WORKDIR /usr/src/app
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y cron vim

COPY requirements.txt ./
RUN pip install --disable-pip-version-check --no-cache-dir -r requirements.txt && rm requirements.txt

COPY scrape.py entrypoint.sh user-agents.json ./
RUN chmod +x entrypoint.sh

# Run the command on container startup
CMD ["./entrypoint.sh"]
