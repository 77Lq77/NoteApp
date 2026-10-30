FROM python:3.11-slim

WORKDIR /app

# iputils-ping so the admin "test the server" tool can actually ping a host.
RUN apt-get update && apt-get install -y --no-install-recommends iputils-ping \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

# Create the runtime user and writable locations with restricted permissions.
RUN groupadd --system notesapp \
    && useradd --system --gid notesapp --home-dir /app --no-create-home \
        --shell /usr/sbin/nologin notesapp \
    && mkdir -p /var/log/notesapp /app/backups \
    && printf 'DB_PASSWORD=notesapp_pg_pw_2024\n' > /app/config.env \
    && printf '%s\n' '-- nightly dump of users table' \
        'admin:admin123:admin' 'prof.turing:teach123:teacher' > /app/backups/users_backup.sql \
    && touch /var/log/notesapp/app.log \
    && chmod 0750 /var/log/notesapp /app/backups \
    && chmod 0640 /var/log/notesapp/app.log /app/backups/users_backup.sql /app/config.env \
    && chown -R notesapp:notesapp /var/log/notesapp /app/backups /app/config.env

USER notesapp

EXPOSE 5000

CMD ["python", "app.py"]
