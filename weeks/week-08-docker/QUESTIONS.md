# Week 8: Conceptual Questions

## 1. What is a container? How is it different from a virtual machine?

A container is a lightweight, standalone package that includes
everything needed to run an application, such as code, runtime, and
libraries. Unlike a VM, which emulates full hardware and runs a
complete OS on top of a hypervisor, containers share the host OS
kernel. This makes them significantly faster to start and more
efficient in resource usage.

## 2. What does a Dockerfile do? Why is each line important?

A Dockerfile is the "recipe" for building a Docker image. Each
instruction, such as `FROM`, `COPY`, or `RUN`, creates a new layer in
the image. Each line matters because it defines the exact execution
environment and enables reproducibility. Docker caches layers, so if a
line changes, only the affected layers are rebuilt.

## 3. Why would you use multistage builds?

Multistage builds optimize the final image size. A heavy first stage
contains all build tools and dependencies, while a second lightweight
stage only copies the final binary or the necessary files. Everything
used during the build process is discarded, resulting in a much smaller
and more secure production image.

## 4. What makes a container image "good"?

- **Small**: Less download time and disk usage. This is why we chose
  `nginx:latest` over `FROM ubuntu + apt install nginx`.
- **Fast**: Starts in seconds.
- **Secure**: No unnecessary tools, runs with least privilege.
- **Reproducible**: Using specific tags ensures consistent behavior
  across environments.

## 5. What are container registries for?

They are central stores, such as Docker Hub or GHCR, where images are
stored, versioned, and distributed. They allow any team member or
cluster node to pull a ready-to-run image without needing the original
source code.

## 6. How does Docker replace systemd from Assignment 1?

In Assignment 1, we used `systemd` to ensure Nginx started on boot and
restarted on failure. In Docker, this is handled by the restart policy,
for example `--restart always`. Logging, previously managed by
`journald`, is now captured by the Docker logging driver via
stdout/stderr and can be inspected with `docker logs`.
