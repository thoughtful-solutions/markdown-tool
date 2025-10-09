# R: Integratable

## Definition

All shared business capabilities and data must be made available for integration through secure, standardized, and self-describing interfaces. These authoritative interfaces are the only permitted way to access their underlying capabilities. To meet new requirements, these interfaces must be extended in a backward-compatible manner, preventing the creation of duplicative or alternative access patterns.

## Rationale

To foster a loosely-coupled and evolvable architecture where teams can easily and securely integrate with authoritative business capabilities and data. This approach lowers the cognitive overhead for developers, accelerates delivery, and ensures a consistent, high-quality experience for all consumers, preventing the fragmentation of logic and information.

## Implications

High-friction, costly integration projects due to inconsistent and poorly documented interfaces; creation of tightly-coupled, brittle systems that are difficult to change; proliferation of redundant services and data silos because existing capabilities are too difficult to find or reuse; inconsistent security models leading to vulnerabilities.
 
## Scope

### Organisational Scope

This rule applies to all teams that expose or consume any shared business capability or data asset within the organisation.

### Technology Scope

This rule governs the qualities and patterns of all integration points, including APIs and event streams. Interfaces must be self-describing via machine-readable contracts (e.g., OpenAPI) and adhere to the organisation's design guides to ensure a consistent developer experience.

## Exception Process

Exceptions must be formally requested from the Architecture Review Board, require a documented risk assessment, and must include approved compensating controls.


