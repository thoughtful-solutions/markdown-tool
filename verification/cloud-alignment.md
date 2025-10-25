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
FEATURE: Service Model Classification

  SCENARIO: Report on service model distribution
    GIVEN an inventory of Entra ID services
    WHEN services are classified by their type
    THEN produce a JSON report of the counts for SaaS, PaaS/IaaS, and Local services
```
