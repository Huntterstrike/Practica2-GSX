# Week 9: Conceptual Questions

## 1. What does docker-compose.yml define?

The `docker-compose.yml` file defines a multi-container application. It
describes which services exist, which images or Dockerfiles they use,
what ports are exposed, which environment variables are set, what
volumes are mounted, and how the services are connected. In practice,
it is the file that lets you start an entire stack with a single
command instead of running containers one by one.

## 2. How do services in Compose communicate?

Services in Docker Compose communicate through an internal network that
Compose creates automatically. Each service can reach another one by
using its service name as the hostname. For example, a frontend or
Nginx container can contact a backend service using
`http://backend:3000` instead of an IP address. This makes service
discovery simple and consistent.

## 3. Why do you need volumes? When do you use them?

Volumes are needed to persist data outside the lifecycle of a
container. Containers are ephemeral, so if a container is deleted or
recreated, the data stored only inside it may disappear. You use
volumes when data must survive restarts, such as for databases,
uploaded files, logs, or shared application state. They are also useful
in development when mounting source code from the host into the
container.

## 4. How do you manage secrets (API keys, passwords)?

Secrets such as API keys and passwords should not be hardcoded in the
image, source code, or committed to Git. In Docker Compose, they are
commonly managed through environment variables and `.env` files during
development. However, real secret values should never be pushed to the
repository, so `.env` should be listed in `.gitignore`. In more serious
production environments, dedicated secret-management solutions are
preferred.

## 5. When is Compose appropriate? When would you use Kubernetes instead?

Docker Compose is appropriate for local development, testing, and small
deployments where you want a simple way to run multiple related
containers on one machine. It is easy to configure and ideal for
development workflows. Kubernetes is more appropriate for larger or
production environments where you need orchestration across multiple
machines, automatic recovery, scaling, rolling updates, and more
advanced management features. In short, Compose is best for simplicity,
while Kubernetes is best for large-scale production systems.
