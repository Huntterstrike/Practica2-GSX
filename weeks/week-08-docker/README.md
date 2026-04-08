# Week 8: Containerization (Docker)

During this week, we containerized the foundational services of GreenDevCorp. The week is split into two complementary parts:
- `nginx/`: web server container based on the Assignment 1 configuration.
- `simple-app/`: minimal HTTP application used as a backend service and as a base for future weeks.

## 1. Nginx Containerization

The goal was to package the Nginx server in a Docker container that mirrors the configuration used in Assignment 1 while following modern containerization standards.

### Dockerfile Rationale
- **Base Image**: `nginx:latest`. As specified in the assignment requirements, we use the official latest Nginx image.
- **Configuration Persistence**: The `default.conf` file replaces the default Nginx configuration within the container at `/etc/nginx/conf.d/default.conf`.
- **Ports**: Port `80` is exposed for external HTTP traffic.

### Configuration Strategy
The `default.conf` has been designed to support both static content delivery and future backend integration:
- **Static Content**: Served from `/usr/share/nginx/html`.
- **Reverse Proxy**: The `/api` location proxies to `http://simple-app:5000/`, preparing the service for Docker Compose in Week 9.
- **Error Handling**: Custom `50x.html` handling preserves a consistent experience.

### Build & Test Locally

```bash
docker build -t nginx-gsx ./nginx
docker run -d -p 8080:80 --name nginx-server nginx-gsx
curl -I http://localhost:8080
```

### Push to Docker Hub

```bash
docker tag nginx-gsx:latest your_username/nginx-gsx:v1
docker push your_username/nginx-gsx:v1
```

## 2. Simple App Containerization

The second deliverable is a minimal HTTP backend that can run identically on any machine and can later be wired behind Nginx or deployed with Compose and Kubernetes.

### Application Design
- **Language**: Python.
- **Framework**: Python standard library only (`http.server`), so the image has no external runtime dependencies.
- **Route `/`**: returns `Hello from container`.
- **Route `/health`**: returns `OK` for basic health checks.
- **Port**: The service listens on port `5000`, matching the Nginx reverse proxy configuration already prepared for the following weeks.

### Dockerfile Rationale
- **Base Image**: `python:3.12-alpine`, chosen because it is small and already includes Python.
- **Working Directory**: `WORKDIR /app` keeps the runtime files in a predictable location.
- **Security**: A dedicated non-root user (`app`) runs the process.
- **Reproducibility**: The image contains only one application file, making the build predictable and easy to explain.
- **Configuration**: The app reads `PORT` and `APP_MESSAGE` from environment variables, avoiding hardcoded runtime values.

### Build & Test Locally

```bash
docker build -t simple-app-gsx ./simple-app
docker run --rm -p 5000:5000 --name simple-app-server simple-app-gsx
```

In another terminal:

```bash
curl http://localhost:5000/
curl http://localhost:5000/health
```

Expected responses:
- `/` -> `Hello from container`
- `/health` -> `OK`

### Push to Docker Hub

```bash
docker login
docker tag simple-app-gsx:latest your_username/simple-app-gsx:v1
docker push your_username/simple-app-gsx:v1
```

### Files Included
- `simple-app/app.py`: minimal HTTP server.
- `simple-app/Dockerfile`: image definition for the backend service.
- `simple-app/.dockerignore`: excludes cache files, virtual environments, Git metadata, and local placeholder files.

## 3. Docker Ignore Strategy

There is a shared `.dockerignore` in `week-08-docker/`, but Docker only applies the `.dockerignore` that belongs to the active build context.

That means:
- `docker build ./nginx` uses `nginx/` as context, so the parent `.dockerignore` is not applied.
- `docker build ./simple-app` uses `simple-app/` as context, so the parent `.dockerignore` is not applied there either.

For that reason, `simple-app/` includes its own `.dockerignore`. The parent `.dockerignore` was also kept with generic rules in case the team later decides to build from `week-08-docker/` using `docker build -f simple-app/Dockerfile .`.

## 4. Design Decisions & Trade-offs

- **Official base images instead of full OS images**: Smaller images, faster builds, and fewer unnecessary packages.
- **Python standard library instead of Flask/Express**: Fewer dependencies and a simpler explanation for the basic deliverable.
- **Port 5000 for the backend**: Aligns the simple app with the Nginx reverse proxy already configured.
- **Non-root execution**: Better default security posture with almost no extra complexity.

## 5. Deliverables Checklist

- [x] Dockerfile for Nginx application
- [x] Dockerfile for simple application
- [x] Simple HTTP application created and documented
- [x] Nginx configuration defined
- [x] Local build commands documented for both services
- [ ] Both images built successfully locally
- [ ] Both images pushed to Docker Hub and verified on another machine
