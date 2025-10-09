# V: Identity Adherence

## Description

Audits all integrated SaaS applications to ensure they are managed via the central Identity Provider (IdP), which is the only permitted way to manage authentication. This prevents orphaned accounts and ensures consistent, auditable, and fine-grained access control across the application portfolio.

## Metadata
- **Category**: Security
- **Display Control**: Traffic Light
- **Thresholds**:
    - **Green**: > 99% 
    - **Amber**: 95% - 98% 
    - **Red**: < 95% 
- **Maturity Level**: Medium

## Features
```gherkin
FEATURE: SaaS Integration Audit

  SCENARIO: Generate an inventory of Enterprise Applications used for SSO
    GIVEN I am authenticated with elevated permissions to the Entra ID tenant
    WHEN I request the list of all HTTP-Auth Applications
    THEN the system must provide a report detailing each Application Name and its SSO Status
    AND the report must be saved as a CSV file for auditing
```

