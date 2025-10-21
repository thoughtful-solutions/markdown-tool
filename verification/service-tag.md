# V: Service Tag Querying

## Description

Verifies the ability to accurately query and filter the service inventory based on metadata tags. This ensures that reporting and automation can correctly identify services belonging to specific domains, such as Finance or Development, for governance and management purposes.

## Metadata

- **Category**: Operations
- **Display Control**: Pie Chart
- **Thresholds**: N/A
- **Maturity Level**: Medium

## Features
```gherkin
FEATURE: Query Service Inventory by Tags

  SCENARIO: Verify service tags and role counts for a specific service
    GIVEN an inventory of Entra ID services
    WHEN list for the services 
    AND  for each service provide a list of roles
    THEN provide an list count of roles per service
```

