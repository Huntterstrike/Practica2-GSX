# Week 12 Research: Core Services & Identity Management

This document collects the theoretical material requested by the Week 12
assignment so that the main README can stay focused on the implemented network
design and Kubernetes policies.

## 1. DNS

DNS, or Domain Name System, is the service that translates human-friendly
names into IP addresses. Without DNS, users and systems would need to remember
 raw IP addresses such as `10.96.0.10` instead of names such as
`redis.green-dev-prod.svc.cluster.local` or `intranet.greendevcorp.local`.

An organization needs DNS because almost every modern service depends on names
instead of hard-coded addresses. It improves usability, allows services to
move without changing every client manually, and makes infrastructure easier to
operate. At a high level, DNS works by asking a resolver for the address that
matches a name. The resolver then returns the right IP, either from cache or
by querying authoritative servers.

## 2. DHCP

DHCP, or Dynamic Host Configuration Protocol, automatically gives devices the
network settings they need to join a network. This usually includes an IP
address, subnet mask, default gateway, and DNS server configuration.

Organizations use DHCP because manually assigning addresses to every laptop,
printer, or server quickly becomes error-prone and hard to manage. DHCP makes
large networks practical to operate and reduces conflicts caused by duplicate
IP addresses. At a high level, a device asks for network configuration when it
joins the network, and the DHCP server leases an address from a managed pool.

## 3. NTP

NTP, or Network Time Protocol, keeps clocks synchronized across systems. This
is more important than it first appears because modern systems depend heavily
on accurate timestamps.

Time synchronization matters for security and operations. Logs only make sense
if different machines agree on when something happened. Authentication tokens,
TLS certificates, scheduled jobs, alert correlation, and forensic analysis can
all fail or become confusing when clocks drift apart. In practice, NTP lets
machines regularly adjust their local clock to trusted time sources.

## 4. Authentication vs Authorization

Authentication answers the question: "Who are you?" It is the process of
verifying identity. Examples include a password, MFA, a hardware token, or a
certificate.

Authorization answers the question: "What are you allowed to do?" Once the
identity is known, authorization determines whether that user or service can
access a specific application, dataset, API, or administrative action.

These concepts are related but not interchangeable. A user can be
authenticated successfully and still not be authorized to access a sensitive
resource.

## 5. LDAP

LDAP, or Lightweight Directory Access Protocol, is a protocol for querying and
managing directory information. A directory typically stores structured
identity data such as users, groups, organizational units, and attributes.

LDAP is useful because it gives many systems one common way to look up users
and groups. Historically, it has been widely used for centralized identity in
enterprise environments. Its strength is consistency and interoperability, but
it usually requires more administration than modern cloud identity platforms.

## 6. Active Directory

Active Directory is Microsoft's directory and identity platform built around
directory services, domain membership, group policy, and access control. It is
heavily used in Windows-centric organizations.

The main strength of Active Directory is that it centralizes user accounts,
computer management, and policy enforcement in a way that integrates deeply
with Microsoft ecosystems. In many companies, Active Directory is the backbone
for workstation login, shared drives, permissions, and enterprise
administration.

## 7. SSO

SSO, or Single Sign-On, means a user authenticates once with a central
identity provider and then reuses that identity across multiple systems.

SSO matters because it improves both usability and security. Users handle fewer
passwords, and administrators can apply consistent controls such as MFA,
conditional access, centralized logging, and faster offboarding. In practice,
SSO reduces the number of disconnected accounts that would otherwise have to be
managed separately.

## 8. What Centralized Identity Solves

Centralized identity solves the problem of fragmented account management. If
each service has its own separate users, passwords, and roles, onboarding and
offboarding become slow, errors become common, and auditability becomes weak.

With centralized identity, the company has one authoritative place to manage
users and groups. That improves security, makes permission changes easier, and
helps prove who had access to what. It also reduces the chance of orphaned
accounts surviving after an employee leaves the organization.

## 9. When Small vs Large Companies Need It

A small company may initially survive without a formal centralized identity
system, but the pain grows quickly once the team starts using multiple
services, cloud platforms, and shared internal tools. Around the size of
GreenDevCorp, the operational benefit already becomes noticeable.

A large company almost always needs centralized identity. The scale of
employees, contractors, systems, and compliance requirements makes manual
account management too risky and inefficient.

## 10. Identity Strategy Recommendation for GreenDevCorp

GreenDevCorp has grown past the stage where fully manual account management is
comfortable. With 20+ people, multiple teams, and separate environments, the
best recommendation is a centralized identity provider with:

- SSO
- MFA
- group-based authorization
- audit logging
- easy onboarding and offboarding

The most practical choice would usually be a cloud-first identity platform
already aligned with the company's productivity suite, such as:

- Microsoft Entra ID if the company is Microsoft-oriented
- Google Workspace identity if the company is Google-oriented

This is a better default recommendation than building a self-managed LDAP
environment from the start.

## 11. Trade-Offs of the Recommendation

Benefits:

- simpler account lifecycle management
- stronger security controls
- fewer passwords for users
- easier enforcement of MFA and role-based access
- better auditability

Trade-offs:

- dependence on an external identity provider
- subscription cost
- some integration work for legacy systems
- less direct control than a fully self-hosted directory

For GreenDevCorp, those trade-offs are acceptable because the operational
simplicity and security gains are more valuable than the extra control of a
self-managed LDAP stack.

## 12. Why Advanced LDAP Implementation Was Not Chosen

The assignment marks LDAP cluster integration as optional advanced work. In
this repository, that part was intentionally not implemented.

The reasoning is straightforward:

- the Week 12 core and intermediate goals are already substantial
- the repository already demonstrates real segmentation and access control with
  Kubernetes NetworkPolicies
- for a 20+ person company, architectural reasoning about centralized identity
  is more immediately valuable than deploying a fragile local LDAP lab without
  production-grade integration
