# V: Cloud Strategy Alignment

## Description

Verifies that the organisation's cloud service portfolio aligns with the enterprise cloud-first strategy. This verification analyses the distribution of hosting models across both business and technical services, tracking progress towards the target state architecture. It identifies services that are migration candidates, measures overall cloud adoption rates, and highlights alignment with strategic technology choices. The verification provides actionable insights for architecture governance and investment planning.

## Metadata
- **Category**: Operations
- **Display Control**: Pie Chart
- **Thresholds**: N/A
- **Maturity Level**: Medium

## Features
```gherkin
FEATURE: Cloud Strategy Alignment Monitoring

  SCENARIO: Analyse hosting model distribution across business services
    GIVEN a CMDB inventory of business services
    WHEN services are grouped by their hosting model classification
    THEN produce a count distribution report showing Cloud SaaS, Cloud PaaS/IaaS, On-Premise, and Hybrid services

  SCENARIO: Analyse hosting model distribution across technical services
    GIVEN a CMDB inventory of technical services
    WHEN services are grouped by their hosting model classification
    THEN produce a count distribution report showing Cloud SaaS, Cloud PaaS/IaaS, On-Premise, and Hybrid services

  SCENARIO: Identify on-premise migration candidates
    GIVEN a combined inventory of all services
    WHEN services with hosting model "On-Premise" or "Hybrid" are filtered
    AND services are sorted by business criticality
    THEN produce a prioritised migration candidate list with service names and current hosting status

  SCENARIO: Calculate overall cloud adoption percentage
    GIVEN a complete inventory of all services
    WHEN cloud-hosted services are counted
    AND the percentage of services running in the cloud is calculated
    THEN produce a cloud adoption score with threshold status
```
