# P: Resiliency

## Definition

The ability of a system to withstand, adapt to, and recover from disruptions—whether accidental failures or deliberate attacks—while maintaining its essential functions.

## Rationale

To ensure business continuity, protect revenue streams, and maintain customer trust by guaranteeing that critical services remain available and performant, even when failures occur.

## Implications

* **Business**: Requires the business to define its tolerance for downtime and data loss by setting Recovery Time Objectives (RTOs) and Recovery Point Objectives (RPOs) for critical processes.
* **Application**: Involves designing applications to handle failure gracefully using patterns like circuit breakers, retries, and timeouts.
* **Data**: Mandates robust data backup, replication, and failover strategies across multiple geographic locations.
* **Technology**: Relies on redundant infrastructure, load balancing, and automated failover mechanisms across different hosting environments.
  
## Metrics

* System availability/uptime percentage (e.g., 99.99%).
* Mean Time Between Failures (MTBF).
* Successful completion rate of automated disaster recovery tests.
* Performance degradation during a failure event.

## Implementation Guidelines

* Deploy critical applications across multiple cloud availability zones or regions.
* Implement health checks and auto-scaling for all services.
* Conduct regular disaster recovery (DR) drills and chaos engineering experiments to validate resiliency.
* Automate backup, restore, and failover procedures.

