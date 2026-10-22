name：雷晴 Leah
student id: 2023905937

# NotesApp

A small grades application used throughout the Computer Security course. Teachers
record grades and comments for their classes, students read their own grades, and an
admin manages users and classes.

## Run it

You need Docker with the Compose plugin.

```
git clone git@github.com:KristenPire/NoteApp.git notesapp
cd notesapp
docker compose up
```

The first start builds the image, launches PostgreSQL, and loads the seed data
automatically. When it is ready, open:

```
http://localhost:8080
```

## Run with HTTPS (self-signed certificate)

The HTTPS overlay adds nginx on ports 80 and 443 and removes the web service's
directly published HTTP port. In PowerShell, create the certificate directory
and a local certificate/private key using OpenSSL in a temporary Docker
container:

```powershell
New-Item -ItemType Directory -Force nginx\certs | Out-Null
docker run --rm -v "${PWD}\nginx\certs:/certs" alpine:3.21 sh -c "apk add --no-cache openssl >/dev/null && openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout /certs/notesapp.key -out /certs/notesapp.crt -subj '/CN=localhost' -addext 'subjectAltName=DNS:localhost,IP:127.0.0.1'"
docker compose -f docker-compose.yml -f docker-compose.https.yml up -d --build
```

Open `https://localhost`. The browser will warn because the certificate is
self-signed; it is suitable only for local lab testing. Do not expose this
configuration publicly. The certificate and private key under `nginx/certs/`
are ignored by Git. Port 80 redirects to HTTPS; Flask remains reachable only
inside the Compose network on port 5000.

## Test accounts

| Role    | Username      | Password   |
|---------|---------------|------------|
| Student | `alice`       | `alicepw`  |
| Teacher | `prof.turing` | `teach123` |
| Admin   | `admin`       | `admin123` |

(There are ~30 students in total; each student's password is their username + `pw`,
e.g. `bob` / `bobpw`.)

## Stack

- Python 3.11 + Flask (server-rendered Jinja2 pages and a small JSON API)
- PostgreSQL 15
- Docker Compose (`web` and `db` services)

## Reset

```
docker compose down -v   # wipes the database volume
docker compose up        # reloads the seed data
```

## Updating your fork

The course repository is sometimes updated. Your fork does **not** update by itself.
To pull the latest changes into your fork:

**Easiest (GitHub website):** open your fork, and if it says *"This branch is behind
KristenPire/NoteApp"*, click **Sync fork → Update branch**. Then, in your local clone:

```
git pull
```

**Command line (keeps your own commits):**

```
git remote add upstream https://github.com/KristenPire/NoteApp.git   # once
git fetch upstream
git merge upstream/main
git push
```

Then **rebuild**, because the app code is baked into the Docker image:

```
docker compose up --build
```

A plain `docker compose up` would keep running the old image.
