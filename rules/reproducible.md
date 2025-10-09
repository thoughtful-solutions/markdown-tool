# R: Reproducible

## Definition

 All infrastructure, application, and data schema environments must be defined and managed exclusively through an approved, version-controlled Infrastructure as Code (IaC) and Configuration as Code (CaC) toolset. All application components must be deployed as idempotent releases from a versioned, trusted artifact repository. For all crucial data, a documented and regularly tested data resilience strategy must be in place, providing timely recovery from both physical failures and logical corruption (e.g., via point-in-time recovery), with all original access controls preserved.

## Rationale

 To ensure consistency, eliminate configuration drift, and enable automated and repeatable changes. This approach secures the supply chain by using trusted artifacts and guarantees business continuity by protecting against a wide range of failure scenarios, from hardware loss to application-level data corruption, while maintaining the intended security posture and data integrity.

## Implications

 Configuration drift causing "it works on my machine" issues; insecure manual configurations; permanent data loss from bugs, human error, or malicious attacks due to an inability to perform point-in-time recovery; security breaches from improperly restored access controls; risk of deploying compromised application versions from untrusted sources.

## Scope

### Organisational Scope

This rule applies to all teams and individuals responsible for provisioning or managing any component of a technology service.

### Technology Scope

This rule applies to all cloud and on-premise resources, including VMs, networks, databases, storage, application artifacts, configurations, data schemas, and their corresponding data resilience mechanisms (e.g., point-in-time recovery, geographic replication). Direct manual changes to any provisioned component are strictly prohibited.

## Exception Process

Exceptions must be formally requested from the Architecture Review Board, require a documented risk assessment, and must include approved compensating controls.


