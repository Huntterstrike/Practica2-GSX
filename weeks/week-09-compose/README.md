# Week 9: Multi-container Orchestration (Docker Compose)

This week focused on connecting our isolated containers into a functional microservices architecture using **Docker Compose**. We integrated the Nginx reverse proxy with the Python backend application.

---

## 1. Architecture Overview

We implemented a two-tier architecture:
1.  **Nginx (Frontend/Proxy)**: Acts as the entry point, serving static files and routing API requests.
2.  **Simple-App (Backend)**: A non-root Python service providing programmatic responses.

### Network Design (Service Discovery)
Unlike Week 8 where containers were isolated, in Week 9 they share a custom bridge network called `gsx-network`.
- **Service Discovery**: Nginx no longer needs an IP address to find the backend. It uses the service name `http://simple-app:5000/` defined in the Compose file. Docker's internal DNS resolves this automatically.

---

## 2. Configuration & Orchestration

### Docker Compose Highlights
- **`depends_on`**: Ensures the backend starts before the frontend.
- **`deploy.resources`**: We migrated the CPU and RAM limits from the `docker run` command of Week 8 directly into the Compose file, ensuring infrastructure-as-code consistency.
- **Security**: Both services run with non-root users (`nginx` and `app`).

### Nginx Integration
We enabled the `/api` location block in `default.conf` to act as a reverse proxy:
```nginx
location /api {
    proxy_pass http://simple-app:5000/;
    proxy_set_header Host $host;
}
```

---

## 3. Deployment Instructions

### Start the infrastructure
From the `weeks/week-09-compose` directory:
```bash
docker compose up -d
```

### Verify Orchestration
```bash
# Verify both containers are Up
docker compose ps

# Test the Reverse Proxy connection
curl http://localhost/api
```

---

## 4. Continuity from Assignment 1 - Week 6 (Integration)

In Assignment 1, integrating services required manual configuration of IPs and systemd unit dependencies. Docker Compose automates this:

| Concept | Assignment 1 (Manual) | Assignment 2 (Compose) |
|---------|-----------------------|-------------------------|
| **Service Discovery** | Static IPs in `/etc/hosts` | Internal Docker DNS (service names) |
| **Dependencies** | Manual start order | `depends_on` instruction |
| **Network Isolation** | Complex Firewall/VLANs | Isolated `gsx-network` bridge |
