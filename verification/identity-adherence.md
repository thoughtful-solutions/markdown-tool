# V: Identity Lifecycle Management

## Description

Verifies that the Joiner, Mover, and Leaver (JML) processes for all human and non-human identities are timely, automated, and auditable. This process is essential for preventing security risks like "orphaned user or machine accounts" and mitigating the "delayed revocation of access for departing employees or retired services". It ensures identity is managed centrally, strengthening security and enabling consistent governance.

## Metadata
- **Category**: Security
- **Display Control**: Traffic Light
- **Thresholds**:
    - **Green**: > 99.5% 
    - **Amber**: 98% - 99.5%
    - **Red**:  < 98%
- **Maturity Level**: Medium

## Features
```gherkin
FEATURE: Automated Identity Lifecycle Audits

  SCENARIO: Timely revocation of access for leavers
    GIVEN the master list of departed employees or retired services
    WHEN the central Identity Provider's logs are audited for the corresponding identities
    THEN each identity's access must be fully disabled within the defined SLA (e.g., 24 hours)

  SCENARIO: Correct initial access for joiners
    GIVEN the list of new employees or services and their assigned roles
    WHEN their provisioned access rights in the central IdP are checked
    THEN the assigned permissions must match the pre-approved "birthright" access for that role and not exceed it

  SCENARIO: Appropriate access adjustment for movers
    GIVEN an employee has moved to a new role within the organisation
    WHEN their identity's access permissions are audited after 72 hours
    THEN permissions from their previous role must be revoked
    AND permissions for their new role must be correctly assigned```

