# Week 11: Conceptual Questions

## 1. What's Infrastructure as Code? Why does it matter?

Infrastructure as Code means defining infrastructure using code files
instead of creating or configuring resources manually. For example,
instead of manually applying Kubernetes manifests one by one, we can
define the desired infrastructure using Terraform or Ansible and
reproduce it with commands.

It matters because infrastructure becomes reproducible,
version-controlled, and easier to understand. If the environment breaks
or needs to be recreated on another machine, we can deploy it again
from the same code. It also reduces manual errors, makes changes easier
to review, and provides a clear record of how the infrastructure
evolved over time.

## 2. What's the difference between Terraform (declarative) and Ansible (procedural)?

Terraform is declarative. This means we describe the desired final
state of the infrastructure, and Terraform decides what actions are
needed to reach that state. For example, we define that a Kubernetes
Deployment, Service, or ConfigMap should exist, and Terraform creates,
updates, or removes resources to match that desired state.

Ansible is procedural. This means we define a sequence of tasks to
execute, such as installing packages, copying files, applying
manifests, or running commands. Ansible is very useful for
configuration management and automation scripts, while Terraform is
usually better suited for managing infrastructure state.

In short, Terraform focuses on "what infrastructure should exist",
while Ansible focuses more on "what steps should be executed".

## 3. Why version-control infrastructure?

Infrastructure should be version-controlled because it is part of the
system, just like application code. Keeping infrastructure files in Git
makes it possible to track who changed what, when it changed, and why.
This is important for collaboration, debugging, and accountability.

Version control also makes infrastructure changes safer. Before
applying changes, the team can review the code, compare differences,
and revert to a previous version if something goes wrong. In this
project, version-controlling the IaC files means that the Kubernetes
stack can be recreated from the repository instead of depending on
manual steps or memory.

## 4. What does a CI/CD pipeline do?

A CI/CD pipeline automates the process of validating, building, and
preparing code for deployment. CI stands for Continuous Integration,
and it usually checks that the code builds correctly, passes
validations, and does not introduce obvious errors. CD stands for
Continuous Delivery or Continuous Deployment, and it focuses on
delivering or deploying the validated changes.

In this project, GitHub Actions is used mainly for CI because
GitHub-hosted runners cannot access the local Minikube cluster. The
pipeline can build Docker images, tag them, push them to a registry,
and validate the Infrastructure as Code configuration. The actual
deployment to Minikube is done locally after the CI pipeline passes.
This gives us an automated validation process while still keeping the
local Kubernetes deployment under our control.

## 5. How do you ensure infrastructure changes are safe?

Infrastructure changes are made safer by validating them before
applying them. With Terraform, this includes commands such as
`terraform fmt`, `terraform init`, `terraform validate`, and especially
`terraform plan`, which shows what will change before anything is
actually modified. With Ansible, this can include syntax checks,
linting, and testing playbooks in a non-production environment first.

Another important safety practice is to avoid hardcoded values and
secrets. Configuration should be handled through variables, and
sensitive data should not be committed to Git. Changes should also be
small, documented, and reviewed before being applied. In this project,
the CI pipeline helps by automatically validating the IaC files and
building deployable container images before the local deployment to
Minikube is performed.
