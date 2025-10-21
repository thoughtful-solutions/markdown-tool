# V: Privilege Governance

## Description

Measures the effectiveness of the enterprise-wide privilege governance framework. It verifies that critical, discoverable assets are under central management and enforces a continuous audit of privileged human and non-human identities to uphold a least-privilege security model

## Metadata
- **Category**: Risk
- **Display Control**: Temperature Bar
- **Thresholds**:
    - **Green**: > 98% 
    - **Amber**: 90% - 98% 
    - **Red**: < 90% 
- **Maturity Level**: Medium

## Features
```gherkin
FEATURE: Privilege Governance Audit

  SCENARIO: Verify Critical Applications are Under Central Governance
    GIVEN I am authenticated with elevated permissions to the CMDB and Entra ID
    WHEN I request a list of all Enterprise Applications marked as "Critical"
    AND they have the "AccessManagementTool" attribute configured
    THEN each application must have a synchronization status of "Active" with the Identity Governance system

  SCENARIO: Count privileged human users per service group

  SCENARIO: Count privileged non-human identities per service group

```

