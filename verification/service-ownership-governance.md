# V: Service Ownership Governance

## Description

Verifies that every service has clear, accountable ownership with appropriate personnel assigned. This ensures that identity lifecycle management, security configurations, and operational responsibilities can be effectively executed, preventing orphaned services and security blind spots. This verification directly supports the **Securable** and **Discoverable** architecture rules by ensuring every service has an accountable owner for IdP integration and access management, and clear accountability prevents orphaned services with unmanaged credentials.

## Metadata
- **Category**: Operations
- **Display Control**: Traffic Light
- **Thresholds**:
    - **Green**: > 95% of active services have valid ownership
    - **Amber**: 90% - 95%
    - **Red**: < 90%
- **Maturity Level**: Foundation

## Features

```gherkin
FEATURE: Service Ownership Verification

  SCENARIO: Active services have assigned individual owners
    GIVEN a service inventory from the CMDB
    WHEN filtering for services with Status = "Active"
    THEN each active service must have a non-empty "Responsible Person" field
    AND the responsible person must NOT be "Config-Manager" or "Contract-Staff"
    AND the percentage of active services with valid ownership should be > 95%

  SCENARIO: New services receive ownership assignment within SLA
    GIVEN a service inventory from the CMDB
    WHEN filtering for services with Status = "New"
    THEN each service with Status = "New" for > 7 days must have assigned ownership
    AND flag services exceeding the 7-day ownership assignment SLA
    
  SCENARIO: Identify orphaned services requiring action
    GIVEN a service inventory from the CMDB
    WHEN checking for potential orphaned services
    THEN flag services where ANY of the following is true:
      AND Status is "Inactive" AND Responsible Person is empty
      AND Status is "Archived" AND last-modified date > 90 days ago
      AND Status is "Active" AND Responsible Person is "Config-Manager"
    AND produce a risk report listing these services with required actions

  SCENARIO: Ownership distribution analysis
    GIVEN a service inventory from the CMDB
    WHEN analysing service ownership
    THEN produce a report showing:
      AND Count of services per responsible person
      AND Responsible persons with > 10 services (potential overload)
      AND Responsible persons with only archived services (cleanup needed)
      AND Services grouped by CI Type and ownership status
    
  SCENARIO: Critical services have senior ownership
    GIVEN a service inventory from the CMDB
    WHEN filtering services with BCM Class 0-2 (critical)
    THEN verify these services have assigned ownership
    AND flag critical services with generic or missing ownership for immediate escalation
```
