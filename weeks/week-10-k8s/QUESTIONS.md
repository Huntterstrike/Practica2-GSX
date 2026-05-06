# Week 10: Conceptual Questions

## 1. What's a pod? How is it different from a container?

A pod is the smallest deployable unit in Kubernetes. It is a wrapper
around one or more containers that share the same network namespace, IP
address, and storage volumes. A container is just the application
runtime itself, while a pod is the Kubernetes object that manages how
that container runs inside the cluster. In this project, the `nginx`
and `simple-app` applications each run inside pods, and Kubernetes
manages those pods rather than managing containers directly.

## 2. What's a Deployment? Why would you use it instead of running a pod directly?

A Deployment is a higher-level Kubernetes resource that manages a
desired number of pod replicas and keeps them running over time. If you
create a pod directly and it crashes or is deleted, Kubernetes does not
automatically recreate it in the same controlled way. A Deployment
solves that by handling replica management, self-healing, and rolling
updates. In this project, the `nginx` and `simple-app` workloads use
Deployments because they are stateless application services that may
need updates or scaling.

## 3. How do Services work? Why do you need them for networking?

A Service gives a stable network identity to a group of pods selected
by labels. Pods are ephemeral and their IP addresses can change when
they are restarted, so other components should not talk to pods
directly by IP. Instead, they talk to a Service name such as
`simple-app` or `redis`, and Kubernetes routes the traffic to the
matching pods. This is why Services are essential for networking: they
provide service discovery and stable communication inside the cluster,
and they can also expose applications externally, for example through a
`NodePort` service like `nginx`.

## 4. What happens when you scale a deployment?

When you scale a Deployment, Kubernetes updates the desired number of
replicas and the control plane creates or removes pods until the actual
state matches the requested state. If you scale `nginx` from 1 replica
to 3, Kubernetes starts two additional pods with the same template and
the Service can distribute traffic to them. If you scale back down,
Kubernetes terminates the extra pods. This makes horizontal scaling much
easier than manually starting containers one by one.

## 5. How does Kubernetes recover from failures?

Kubernetes continuously compares the real cluster state with the desired
state defined in the manifests. If a pod crashes, is deleted, or fails
its health checks, Kubernetes creates a replacement or restarts
containers depending on the situation. Readiness probes control whether
a pod should receive traffic, while liveness probes help detect
containers that are stuck or broken and need restarting. In this
project, the probes on `nginx`, `simple-app`, and `redis` are part of
that recovery behavior.

## 6. When is Kubernetes worth the complexity? When is it overkill?

Kubernetes is worth the complexity when you need production-grade
orchestration features such as self-healing, rolling updates, service
discovery, resource control, scaling across multiple nodes, and
management of many applications or teams. It becomes especially useful
when an organization is growing and manual container management no
longer scales. It is overkill for very small projects, simple local
development, classroom demos with one machine, or cases where Docker
Compose already solves the problem with much less operational overhead.
In short, Kubernetes is powerful when you truly need orchestration, but
expensive if the workload is small and simple.
