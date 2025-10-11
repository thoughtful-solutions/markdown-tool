# V: Cloud Alignment

## Description

Verifies the portfolio's alignment with the "cloud-first" business strategy by measuring the distribution of service models (IaaS, PaaS, SaaS). This helps track progress towards leveraging provider-scale efficiencies and reducing the on-premise carbon footprint.

## Metadata
- **Category**: Development
- **Display Control**: Pie Chart
- **Thresholds**: N/A
- **Maturity Level**: Medium

## Features
```gherkin
FEATURE: Cloud Service Model Distribution

  SCENARIO: Report on Cloud Service Types
    GIVEN a complete list of deployed services
    WHEN the service type is identified as [IAAS|SAAS|PAAS]
    THEN return the percentage distribution of each service type
```
