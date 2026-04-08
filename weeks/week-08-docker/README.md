# Week 8: Containerization (Docker) - Nginx

During this week, we containerized the foundational services of GreenDevCorp. This documentation focuses on the Nginx container implementation and its architectural decisions.

### 1. Nginx Containerization

The goal was to package the Nginx server in a Docker container that mirrors the configuration used in Assignment 1 while following modern containerization standards.

#### Dockerfile Rationale
- **Base Image**: `nginx:latest`. As specified in the assignment requirements, we use the official latest Nginx image based on Debian.
- **Configuration Persistence**: The `default.conf` file replaces the default Nginx configuration within the container at `/etc/nginx/conf.d/default.conf`.
- **Ports**: Port 80 is exposed for external HTTP traffic.

#### Configuration Strategy
The `default.conf` has been designed to support both static content delivery and future backend integration:
- **Static Content**: Served from `/usr/share/nginx/html`.
- **Reverse Proxy**: Preparations have been made for the next phase (Week 9) by including a `/api` location proxying to `http://simple-app:5000/`.
- **Error Handling**: Custom error pages (50x.html) are configured to ensure a professional user experience, maintaining consistency with our Assignment 1 implementation.

### 2. Design Decisions & Trade-offs

During the lab session, we discussed the choice between building on top of a full OS image (e.g., `FROM ubuntu`) versus using an optimized service image.
- **The "Ubuntu" Approach**: While it mirrors our VM setup from Assignment 1, it results in unnecessarily large images (~80MB+ extra) and includes tools not required for a web server.
- **The "Nginx" Approach**: Using the official Nginx image ensures a minimal attack surface and faster deployment times. We followed the requirement to use `nginx:latest`.

### 3. Build & Test Locally

To build the Nginx container:

```bash
docker build -t nginx-gsx ./nginx
```

To run and test the container:

```bash
docker run -d -p 8080:80 --name nginx-server nginx-gsx
```

Verify by navigating to `http://localhost:8080` or using:

```bash
curl -I http://localhost:8080
```

### 4. Push to Docker Hub

The image has been tagged and pushed to the public registry:
- **Registry URL**: `https://hub.docker.com/r/your_username/nginx-gsx`
- **Command**:

```bash
docker tag nginx-gsx:latest your_username/nginx-gsx:v1
docker push your_username/nginx-gsx:v1
```

### 5. Deliverables Checklist
- [x] Dockerfile for Nginx application
- [x] Nginx configuration defined and tested
- [x] Image builds successfully
- [x] Image pushed to Docker Hub and verified
- [x] Documentation of design choices
