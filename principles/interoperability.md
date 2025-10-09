# P: Interoperability

## Definition

The ability of different systems, applications, and services to securely communicate and use shared information in a coordinated way. It is achieved by leveraging standardized APIs and integration patterns, adhering to a common data model for shared understanding, and utilizing a capable integration platform to manage and secure data flows. This includes the seamless and trusted federation of user identity and access rights across all architectural domains. 

## Rationale

o break down information silos by ensuring data is consistent, understandable, and reusable across different systems and applications. This enables secure, seamless business processes and creates a cohesive application portfolio. A core goal is to provide a frictionless user experience through capabilities like Single Sign-On (SSO), while strengthening security by centralizing identity governance and applying consistent, fine-grained access control to both applications and the data assets they consume.

## Implications

* **Business**: Enables secure value streams that cross organizational boundaries, allowing employees, partners, and customers to interact with multiple systems using a single, trusted digital identity, without manual intervention.
* **Application**: Requires applications to communicate using standardized protocols and exchange information in common, interoperable data formats. They must also externalize authentication and authorization, delegating to an enterprise identity provider to ensure consistent and secure access control.
* **Data**: Data must be structured in common, interoperable formats so it can be understood and reused across the enterprise. Access to this data is then governed by centrally managed identity attributes and roles, ensuring that users and systems can only access the information they are explicitly authorized to view or modify.
* **Technology**:  Relies on an integration platform (API Gateway, event bus) to manage and enforce the use of standard protocols (e.g., HTTPS, AMQP) and data formats (e.g., JSON), alongside a centralized IAM platform for identity federation.
  
## Metrics

* Ratio of reusable service-based integrations to custom point-to-point integrations.
* Percentage of applications integrated with the central enterprise SSO solution.
* Time and cost to integrate a new application or onboard a new external partner with federated identity.
* Reduction in access-related help desk tickets.

## Implementation Guidelines

* Mandate the use of a central Identity Provider (IdP) for all applications.
* Use industry-standard data formats (e.g., JSON) and protocols (e.g., REST, AMQP)
* Implement event-driven architecture patterns to decouple systems
* Adopt an "API-first" design approach for all new services.
* Standardize on specific identity federation protocols (e.g., OIDC for modern applications, SAML for enterprise SaaS).
* Implement a Role-Based Access Control (RBAC) or Attribute-Based Access Control (ABAC) model that is managed centrally.

