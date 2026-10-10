# Docker Compose

A Dockerfile defines the **image template** for a container. Docker Compose defines the **runtime environment** for one or more containers. It is a convenient tool for running multiple containers together on a single host.

Anything that describes how a container runs belongs in the Compose file:

- Environment variables
- Docker image
- Restart policy
- Memory and CPU limits
- Command overrides
- Networks and port mappings
- Volumes

Ready-made examples are in the [Awesome Compose repository](https://github.com/docker/awesome-compose), which has 30+ sample stacks (WordPress, Nextcloud, Django and more).

## Sample `compose.yaml`

This example runs a web app and a database. It uses an explicit network, persistent storage, and a health check so the web service waits for the database.

```yaml
name: my-app-stack

services:
  # Web application
  web:
    image: node:20-alpine
    container_name: web_app
    restart: unless-stopped
    ports:
      - "8080:3000"          # HOST:CONTAINER
    environment:
      - NODE_ENV=production
      - DATABASE_URL=postgres://user:password@db:5432/mydb
    volumes:
      - ./app:/usr/src/app   # Bind mount: syncs local code into the container
    networks:
      - app-network
    depends_on:
      db:
        condition: service_healthy   # Start only after the DB is ready

  # Database
  db:
    image: postgres:16-alpine
    container_name: postgres_db
    restart: unless-stopped
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
      POSTGRES_DB: mydb
    volumes:
      - db-data:/var/lib/postgresql/data   # Named volume: survives container removal
    networks:
      - app-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user -d mydb"]
      interval: 10s
      timeout: 5s
      retries: 5

# Persistent storage
volumes:
  db-data:
    driver: local

# Isolated network
networks:
  app-network:
    driver: bridge
```

## Key Settings

| Key | Purpose |
|---|---|
| `name` | Project name, used as a prefix for containers, networks and volumes |
| `services` | The containers to build and run |
| `ports` | Maps `HOST:CONTAINER`. Here, the app is at http://localhost:8080 |
| `depends_on` + `service_healthy` | Delays `web` until the database health check passes |
| `volumes` | A bind mount (`./app`) syncs local code. A named volume (`db-data`) keeps database data when containers are recreated |
| `networks` | Keeps traffic between containers on a private virtual network |

## Common Commands

Run these in the folder containing `compose.yaml`:

```bash
docker compose up -d     # Start the stack in the background
docker compose ps        # Check status
docker compose logs -f   # Follow logs
docker compose down      # Stop and remove containers
```

## Notes on the Sample

- **Secrets:** The hardcoded passwords are for illustration only. For real deployments, use an `.env` file, Docker secrets, or your platform's secret store.
- **Bind mount:** `./app:/usr/src/app` suits development. For production, bake the code into an image instead.

There are three common ways to pass secrets in Compose, from simplest to most robust.

## 1. `.env` file (variable substitution)

Compose automatically reads a `.env` file in the same folder as `compose.yaml`.

**.env**
```bash
POSTGRES_USER=user
POSTGRES_PASSWORD=s3cr3t-change-me
POSTGRES_DB=mydb
```

**compose.yaml**
```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}

  web:
    image: node:20-alpine
    environment:
      DATABASE_URL: postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
```

To fail fast if a value is missing, use `${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}`.

## 2. `env_file` (pass a whole file into the container)

```yaml
services:
  web:
    image: node:20-alpine
    env_file:
      - ./web.env
```

Every `KEY=value` line in `web.env` becomes an environment variable inside the container.

## 3. Docker secrets (file-based, recommended)

Secrets are mounted as files at `/run/secrets/<name>`, so they don't appear in `docker inspect` output or in the process environment.

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: user
      POSTGRES_DB: mydb
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password   # official image supports *_FILE
    secrets:
      - db_password

  web:
    image: node:20-alpine
    secrets:
      - db_password   # app reads /run/secrets/db_password at startup

secrets:
  db_password:
    file: ./secrets/db_password.txt
```

Create the secret file without a trailing newline:

```bash
mkdir -p secrets
printf 's3cr3t-change-me' > secrets/db_password.txt
chmod 600 secrets/db_password.txt
```

In your app code, read the file instead of an env var (Node example):

```js
const password = require('fs').readFileSync('/run/secrets/db_password', 'utf8').trim();
```

## Don't forget

Keep secrets out of git:

```bash
# .gitignore
.env
*.env
secrets/
```

Commit a `.env.example` with placeholder values so others know which variables are needed.

| Method | Visible in `docker inspect` | Best for |
|---|---|---|
| `.env` / `environment` | Yes | Local development |
| `env_file` | Yes | Many variables per service |
| Docker secrets (file) | No | Production and shared environments |

For production on a cluster, use your platform's secret store (Docker Swarm secrets, Kubernetes Secrets, AWS Secrets Manager, Vault) rather than files on disk.
