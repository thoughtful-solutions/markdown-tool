# R: Discoverable

## Definition

All deployed applications, services, APIs, and shared data resources must be assigned a unique name that conforms to the organisation's naming ontology. This name must clearly place the asset within a human- and machine-readable hierarchy, indicating its business domain and function. The asset, identified by this canonical name, must then be registered in the central Service & Asset Catalog with all required metadata, including dependencies and operational links.

## Rationale

To enable predictable and intuitive discovery of all technology assets. A consistent naming hierarchy allows anyone (or any system) to locate relevant capabilities and data without prior knowledge, simplifying development, reducing redundant work, and providing a clear, structured map of the organisation's technology landscape.

## Implications

Inability to find or reuse existing services due to ambiguous or inconsistent naming, leading to redundant functionality; a chaotic and difficult-to-navigate service catalog that hinders productivity; prolonged incident resolution times due to unclear dependencies; creation of "shadow IT" because official services are too hard to find.
 
## Scope

### Organisational Scope

: This rule applies to all teams that develop and deploy any technology asset.

### Technology Scope

This rule governs the naming and classification of all REST APIs, gRPC services, asynchronous services, and shared data stores. The asset's canonical name must be used consistently across all tooling, including source code, CI/CD pipelines, and observability platforms, to ensure a unified view of the system.

## Exception Process

Exceptions must be formally requested from the Architecture Review Board, require a documented risk assessment, and must include approved compensating controls.


