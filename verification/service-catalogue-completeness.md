# V: Service Catalogue Completeness

## Description

Verifies that all services are properly registered in the central service catalogue with complete, accurate metadata. This ensures services are discoverable, properly classified, and have clear ownership - fundamental requirements for governance, security, and operational management. This verification directly supports the **Discoverable** architecture rule by ensuring services have unique identifiers, all required metadata is present, clear ownership enables accountability, and proper classification enables filtering and reporting.

## Metadata
- **Category**: Operations
- **Display Control**: Traffic Light
- **Thresholds**:
    - **Green**: > 95% of services have complete metadata
    - **Amber**: 90% - 95%
    - **Red**: < 90%
- **Maturity Level**: Foundation

## Features

```gherkin
FEATURE: Service Registration Completeness

  SCENARIO: All services have unique identifiers
    GIVEN a service inventory from the CMDB
    WHEN each service is checked for unique identification
    THEN each service must have a populated "Number" field matching pattern CI-XXXXXXXX
    AND no duplicate "Number" values should exist
    AND 100% of services must have this field populated

  SCENARIO: All services have required metadata
    GIVEN a service inventory from the CMDB
    WHEN checking registration completeness
    THEN each service must have the following fields populated:
      AND Field             | Validation Rule                    |
      AND Name              | Not empty, min 3 characters        |
      AND CI Type           | One of: Business Service, Technical Service |
      AND Number            | Matches CI-XXXXXXXX pattern        |
      AND Description       | Not empty, min 10 characters       |
      AND Status            | One of: Active, Inactive, Archived, New |
    AND the percentage of services with complete metadata should be > 95%

  SCENARIO: Active services have assigned ownership
    GIVEN a service inventory from the CMDB
    WHEN filtering for services with Status = "Active"
    THEN each active service must have a non-empty "Responsible Person" field
    AND the responsible person must not be "Config-Manager" or "Contract-Staff"
    AND the percentage of active services with valid ownership should be > 95%

  SCENARIO: Services have operating model classification
    GIVEN a service inventory from the CMDB
    WHEN checking the "Operating Model" field
    THEN services should have one of the following values:
      AND SaaS
      AND PaaS
      AND IaaS
      AND IT Service
      AND IT Service-ITMA
      AND IT Service-BMA
      AND Technical Service
      AND BANK_PARENT
    AND the percentage of services with declared operating model should be > 90%
    
  SCENARIO: Identify orphaned or at-risk services
    GIVEN a service inventory from the CMDB
    WHEN checking for governance gaps
    THEN flag services where ANY of the following is true:
      AND Status is "Inactive" or "Archived" AND Responsible Person is empty
      AND Status is "Active" AND more than 3 required fields are empty
      AND Number field is empty or duplicated
    AND produce a risk report listing these services
```
