# V: Cloud Strategy Alignment

## Description

Verifies the organisation's progress towards its "cloud-first" strategy by measuring the distribution of service deployment models. This tracks the journey from on-premise infrastructure to cloud-native services, helping to achieve provider-scale efficiencies, reduce operational overhead, and support sustainability goals through reduced on-premise carbon footprint. This verification supports the **Integratable** and **Reproducible** architecture rules by tracking adoption of standardised cloud service models and identifying services that can leverage cloud-native integration patterns.

## Metadata
- **Category**: Development
- **Display Control**: Pie Chart
- **Thresholds**:
    - **Green**: > 60% cloud-based services (SaaS + PaaS + IaaS)
    - **Amber**: 40% - 60% cloud-based
    - **Red**: < 40% cloud-based
- **Maturity Level**: Medium

## Features

```gherkin
FEATURE: Cloud Service Model Distribution

  SCENARIO: Report on service deployment model distribution
    GIVEN a service inventory from the CMDB
    WHEN services are classified by their Operating Model
    THEN produce a report showing counts and percentages for:
      AND SaaS services (fully managed cloud)
      AND PaaS services (platform cloud)
      AND IaaS services (infrastructure cloud)
      AND IT Services (internal, potentially hybrid)
      AND Technical Services (infrastructure/platform)
      AND BANK_PARENT (parent company hosted)
      AND Undeclared (services without operating model)
    AND calculate total cloud-based percentage (SaaS + PaaS + IaaS)

  SCENARIO: Track cloud adoption trend
    GIVEN service inventory data with timestamps
    WHEN comparing Operating Model distribution over time
    THEN calculate the trend in cloud adoption percentage
    AND flag if trend is declining or stagnant (< 2% improvement per quarter)
    
  SCENARIO: Identify cloud migration candidates
    GIVEN a service inventory from the CMDB
    WHEN filtering for IT Services and Technical Services without cloud operating model
    AND cross-referencing with BCM Class (prioritise critical services)
    THEN produce a prioritised list of services for cloud migration assessment
    AND group by responsible person for action planning

  SCENARIO: Validate operating model declarations
    GIVEN a service inventory from the CMDB
    WHEN checking services declared as SaaS
    THEN verify service names contain known SaaS vendor names (VENDOR_*)
    AND flag services declared as SaaS but appear to be internal products
    AND verify consistency of operating model within service families
```

