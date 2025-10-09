# S: Securable

## Definition

A least-privilege security model must be enforced across all system components. All authentication and authorisation for any principal (human and non-human) must be managed via the central enterprise Identity Provider (IdP). All data must be encrypted in transit and at rest, and all network traffic must be restricted by default. A continuous process for vulnerability scanning and dependency management must be in place.

## Rationale

To provide a single point for managing identities, enforcing access policies, and auditing access, while reducing the attack surface through encryption and network controls. This treats security as a continuous lifecycle activity, protecting against both initial configuration errors and newly discovered vulnerabilities over time.

## Implications

Inconsistent or weak password policies; orphaned user or machine accounts; data breaches from unencrypted data or exploits against unpatched vulnerabilities; unauthorised lateral movement within the network; delayed revocation of access for departing employees or retired services.

## Scope

### Organisational Scope

This rule applies to all applications, infrastructure, and data resources, both internal and external-facing.

### Technology Scope

This rule applies to all applications, APIs, operating systems, and network components. Storing credentials locally is prohibited. It mandates the use of standard protocols like OIDC and mTLS, approved encryption standards, and automated tooling for vulnerability scanning and dependency management.

## Exception Process

Exceptions must be formally requested from the Architecture Review Board, require a documented risk assessment, and must include approved compensating controls.

