#!/bin/bash

printenv > /etc/environment

CRON_LOG=/var/log/cron.log
touch $CRON_LOG

CRON_SCHEDULE="*/3 * * * *"
CRON_JOB=". /etc/environment; cd /usr/src/app/; /usr/local/bin/python3 scrape.py >> /var/log/cron.log 2>&1"

CRONTAB_CONTENT=$(crontab -l 2>/dev/null)
if [ $? -eq 0 ]; then
    echo "$CRONTAB_CONTENT" | grep -Fq "$CRON_JOB"
    if [ $? -ne 0 ]; then
        (echo "$CRONTAB_CONTENT"; echo "$CRON_SCHEDULE $CRON_JOB") | crontab -
    fi
else
    echo "$CRON_SCHEDULE $CRON_JOB" | crontab -
fi

# Start the cron service in the foreground to keep container running
echo "Cron started..."
tail -f $CRON_LOG &
cron -f

