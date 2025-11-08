## Project Overview: Enterprise Architecture Documentation & Governance System

This project is a comprehensive **Enterprise Architecture (EA) documentation and governance system** 
built using Python CLI tools. It creates a structured, validated, and measurable framework for managing 
enterprise architecture artefacts with automated compliance checking and dashboard generation.

## What It Does

### Core Functionality

1. **Documentation Structure Enforcement**
   - Validates markdown documents against defined specifications (using `spec.yaml` files)
   - Ensures all architecture documents follow consistent structure and formatting
   - Enforces required sections, heading levels, and content patterns

2. **Relationship Management**
   - Tracks and validates hyperlinks between related architecture documents
   - Ensures bidirectional relationships where appropriate
   - Prevents broken links and maintains document traceability

3. **Automated Verification & Testing**
   - Executes Gherkin-based scenarios embedded in verification documents
   - Runs shell scripts to validate actual system state against architecture requirements
   - Generates test results and compliance metrics

4. **Dashboard Generation**
   - Creates static HTML dashboards with visual charts (pie charts, traffic lights, temperature bars)
   - Aggregates verification results into category-based views
   - Provides real-time visibility of architecture compliance

### Architecture Taxonomy

The system organises enterprise architecture into four key layers:

1. **Domains** - Core architecture areas:
   - Business Architecture
   - Application Architecture  
   - Data Architecture
   - Technology Architecture

2. **Principles** - Strategic guidelines:
   - Sustainability, Resiliency, Agility
   - Business Alignment, Supportability, Interoperability

3. **Rules** - Enforceable standards:
   - Discoverable, Integratable, Reproducible, Securable

4. **Verification** - Measurable compliance checks:
   - Identity Lifecycle Management
   - Privilege Governance
   - Cloud Alignment
   - Service Inventory

## Why It Exists

### Business Drivers

1. **Consistency at Scale**
   - Large enterprises struggle to maintain consistent documentation across teams
   - Manual review processes don't scale and lead to drift
   - This system enforces standards automatically

2. **Traceability & Governance**
   - Regulatory compliance requires demonstrable controls
   - Architecture decisions must link to business strategy
   - The system creates an audit trail from principles to implementation

3. **Continuous Compliance**
   - Traditional architecture reviews are periodic and retrospective
   - This system enables continuous validation against live systems
   - Real-time dashboards show compliance status

4. **Knowledge Management**
   - Architecture knowledge is often siloed or lost when people leave
   - Structured documentation with enforced relationships preserves institutional knowledge
   - Self-describing, discoverable architecture assets

### Technical Benefits

1. **Static Generation**
   - No runtime dependencies for viewing documentation
   - Can be hosted on simple web servers or SharePoint
   - Version controlled in Git for collaboration

2. **Extensible Framework**
   - New verification scenarios can be added without changing core tools
   - Custom display controls for different metrics
   - Shell script implementations allow integration with any system

3. **DevOps Integration**
   - CLI tools integrate with CI/CD pipelines
   - Automated validation on every commit
   - Fail builds when architecture standards are violated

## Key Components Explained

### 1. **md_validator.py** - The Document Police
   - Validates markdown structure against `spec.yaml` specifications
   - Manages bidirectional links via `links.yaml` files
   - Provides CRUD operations for markdown files
   - Returns different exit codes for CI/CD integration

### 2. **gherkin-runner.py** - The Compliance Executor
   - Extracts Gherkin scenarios from verification documents
   - Maps steps to shell script implementations
   - Passes context between steps (e.g., `GIVEN_STDOUT`)
   - Generates JSON output for dashboard consumption

### 3. **build_chart.py** - The Visualiser
   - Parses verification files to extract metadata
   - Generates appropriate HTML visualisations based on display control type
   - Creates category-organised dashboard structure

### 4. **Implementation Scripts** - The System Inspectors
   - Shell scripts in `gherkin-implements/` that query real systems
   - Example: `service-inventory.gherkin` queries Entra ID (Azure AD) data
   - Transform system data into dashboard-ready JSON

## Use Case Example

Consider the **Identity Lifecycle Management** verification:

1. A markdown file defines the verification with Gherkin scenarios
2. The scenario checks if departed employees have access revoked within 24 hours
3. Shell scripts query the actual Entra ID system
4. Results are validated against defined thresholds (Green >99.5%, Amber 98-99.5%, Red <98%)
5. A traffic light dashboard shows current compliance status
6. Links connect this verification to related rules and principles

This creates a complete chain from business principle → architectural rule → technical verification → operational dashboard.

## Summary

This is a sophisticated **architecture governance platform** that bridges the gap between documentation and reality. 
It transforms static architecture documents into a living, validated, and measurable system that provides continuous 
assurance that the implemented technology aligns with strategic intent. The use of standard formats (Markdown, YAML, Gherkin) 
and static generation makes it accessible whilst the automated validation ensures rigour at scale.