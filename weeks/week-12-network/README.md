# Week 12: Network Design & Identity

## Goal

Implement network segmentation in Kubernetes with NetworkPolicies enforced by
the Calico CNI, following a Zero Trust model across three isolated
environments:

- `green-dev-dev`
- `green-dev-staging`
- `green-dev-prod`

The Week 12 policies now build on top of the Terraform stack from Week 11,
instead of the older Week 10 manifests. This keeps the network model aligned
with the real namespaces and labels already used by the project.

## Architecture

```text
Partner subnet (10.0.10.0/24) + office VPN (10.0.20.0/24)
                         |
                         v
            [nginx] in namespace green-dev-prod
                         |
                         v
         [simple-app] in namespace green-dev-prod
                         |
                         v
            [redis] in namespace green-dev-prod

green-dev-dev and green-dev-staging run the same stack in separate namespaces
and are isolated from green-dev-prod.
```

## Calico Requirement

NetworkPolicies only work if the cluster uses a compatible CNI.

Start Minikube with Calico:

```bash
minikube delete
minikube start --network-plugin=cni --cni=calico
```

Check that Calico is present:

```bash
kubectl get pods -n kube-system | grep calico
```

## Deployment

First deploy the Week 11 application stack for all three environments.

From `weeks/week-11-iac/terraform/`:

```bash
terraform workspace select dev
terraform apply -var-file ./environments/dev.tfvars -auto-approve

terraform workspace select staging
terraform apply -var-file ./environments/staging.tfvars -auto-approve

terraform workspace select prod
terraform apply -var-file ./environments/prod.tfvars -auto-approve
```

Then apply the Week 12 policies from `weeks/week-12-network/`:

```bash
kubectl apply -f kubernetes/
```

## Verification

```bash
chmod +x verify_week12.sh
./verify_week12.sh
```

The verifier is designed to check:

- Minikube context and Calico presence
- the three target namespaces
- the expected NetworkPolicies in each namespace
- allowed traffic paths:
  - `nginx -> simple-app`
  - `simple-app -> redis`
- DNS resolution
- blocked cross-environment traffic
- the partner and office CIDR rule for `prod`

## Files

| File | Description |
|---|---|
| `00-default-deny.yml` | Default deny for ingress and egress in `dev`, `staging`, and `prod` |
| `01-env-isolation.yml` | Restricts `nginx` and `simple-app` egress to only the next allowed hop inside the same environment |
| `02-frontend-to-backend.yml` | Allows `nginx -> simple-app` ingress on port `5000` inside each namespace |
| `03-backend-to-redis.yml` | Allows `simple-app -> redis` ingress on port `6379` inside each namespace |
| `04-allow-nginx-ingress.yml` | Allows ingress to `prod` nginx only from partner and office CIDR ranges |
| `05-allow-dns.yml` | Allows DNS egress to CoreDNS |

## Key Ideas

- `Default deny`: all traffic starts blocked.
- `Per-hop allow rules`: only the exact application path is opened.
- `Namespace isolation`: `dev`, `staging`, and `prod` are separated.
- `Label-driven policy`: the rules depend on:
  - `app=nginx|simple-app|redis`
  - `environment=dev|staging|prod`
- `Partner exposure`: only `prod` gets a specific ingress rule for:
  - `10.0.10.0/24`
  - `10.0.20.0/24`
