# V: Security Classification Compliance

## Description

Verifies that all services have complete security classifications and that these classifications align appropriately with business criticality. This ensures that security controls, encryption, access management, and monitoring are properly scoped to the sensitivity and importance of each service. This verification directly supports the **Securable** architecture rule by ensuring security requirements are explicitly defined for each service and protection levels match business criticality.

## Metadata
- **Category**: Security
- **Display Control**: Temperature Bar
- **Thresholds**:
    - **Green**: > 95% of services have complete SC classifications AND BCM-SC alignment > 90%
    - **Amber**: 90% - 95% complete OR 80% - 90% alignment
    - **Red**: < 90% complete OR < 80% alignment
- **Maturity Level**: Foundation

## Features

```gherkin
FEATURE: Security Classification Completeness

  SCENARIO: All services have complete security classifications
    GIVEN a service inventory from the CMDB
    WHEN checking security-related fields
    THEN each service must have valid (A-E) values for:
      AND | Field                | Description                           |
      AND | SC General           | Overall security classification       |
      AND | SC Availability      | Availability requirements             |
      AND | SC Confidentiality   | Data confidentiality requirements     |
      AND | SC Integrity         | Data integrity requirements           |
      AND | SC Protection Target | Overall protection target level       |
    AND the percentage of services with complete SC fields should be > 95%
    
  SCENARIO: Services have business continuity classification
    GIVEN a service inventory from the CMDB
    WHEN checking the "BCM Class" field
    THEN each service should have a value between 0 (critical) and 4 (low)
    AND the percentage of services with BCM Class should be > 95%

  SCENARIO: Critical services have appropriate security classifications
    GIVEN a service inventory from the CMDB
    WHEN filtering services with BCM Class 0-2 (critical to important)
    THEN these services should typically have SC Protection Target of A or B
    AND flag any critical services (BCM 0-2) with SC Protection Target of D or E
    AND the percentage of BCM 0-2 services with SC A/B should be > 90%

  SCENARIO: Security classification consistency check
    GIVEN a service inventory from the CMDB
    WHEN comparing SC fields for each service
    THEN SC Protection Target should generally align with other SC classifications
    AND flag services where Protection Target differs by more than 2 levels from average of other SC fields
    
  SCENARIO: Report on security posture distribution
    GIVEN a service inventory from the CMDB
    WHEN analysing security classifications
    THEN produce a distribution report showing:
      AND Count of services at each SC Confidentiality level (A-E)
      AND Count of services at each SC Availability level (A-E)
      AND Count of services at each SC Integrity level (A-E)
      AND Count of services at each BCM Class (0-4)
      AND List of high-risk services (BCM 0-2 with SC D/E)
```

