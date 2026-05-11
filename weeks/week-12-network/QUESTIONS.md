# Week 12: Conceptual Questions

## 1. Why segment networks? What do you protect by doing this?

Network segmentation means dividing a network into smaller isolated parts. This prevents every service, user, or device from being able to reach everything else directly.

It protects sensitive systems such as databases, internal services, admin tools, and monitoring systems. If one machine is compromised, segmentation limits lateral movement and reduces the impact of the attack.

## 2. What's a subnet? CIDR notation?

A subnet is a smaller logical network inside a larger network. Devices in the same subnet can usually communicate directly with each other.

CIDR notation describes the size of a network. For example, `192.168.1.0/24` means that the first 24 bits identify the network, and the remaining bits are used for hosts. In practice, subnets and CIDR help organize IP address ranges clearly.

## 3. Why do organizations use DNS, DHCP, NTP?

Organizations use these services to make networks easier to manage.

DNS translates names into IP addresses, so services can be reached by names instead of raw IPs. DHCP automatically assigns IP addresses and network configuration to devices. NTP synchronizes clocks across systems, which is important for logs, certificates, authentication, monitoring, and debugging.

## 4. What's the difference between authentication and authorization?

Authentication means verifying who someone is. For example, logging in with a username, password, or MFA.

Authorization means deciding what that authenticated user or service is allowed to access. For example, a normal user may access the application, while only an admin can manage users or change infrastructure settings.

## 5. Why might a company use centralized identity?

Centralized identity lets a company manage users and access from one place instead of creating separate accounts on every system.

This makes onboarding, role changes, and offboarding safer and easier. It also enables policies such as single sign-on, multi-factor authentication, password rules, group-based permissions, and audit logging.

## 6. How do you ensure secure communication between networks?

Secure communication is achieved by allowing only the necessary traffic between networks and blocking everything else by default.

This can be done with firewalls, routing rules, Kubernetes NetworkPolicies, VPNs, and TLS encryption. The goal is that each service only talks to the services it really needs, and sensitive traffic is protected and monitored.
