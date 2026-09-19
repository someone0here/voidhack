# Architecture & System Design

## System Overview
The Cyber Fraud Correlator is a dual-tier analytical system designed to ingest, normalize, and cross-correlate disparate evidentiary data sources—including telecom call detail records (CDR) and IP detail records (IPDR), bank and Unified Payments Interface (UPI) transaction ledgers, email communication headers, and Android forensic extraction dumps. Operating via an asynchronous FastAPI backend and a high-density React/TypeScript investigative console, the platform constructs an in-memory multidimensional entity graph to reveal hidden identifier overlaps (e.g., shared IMEI/IMSI pairs, mule account routes, common IP addresses, and communication clusters), computes deterministic risk scoring models, and compiles an automated, court-admissible one-page investigative summary brief.

## Data Flow
*(Living documentation placeholder: To be documented and expanded as ingestion pipelines, correlation graph engines, and reporting modules are implemented in subsequent phases.)*

1. **Ingestion & Normalization** *(Planned)*: Raw file parsing, schema normalization, and localized encrypted persistence.
2. **Entity Resolution & Linkage** *(Planned)*: Ingestion into NetworkX graph model with identity resolution across disparate records.
3. **Risk Scoring Engine** *(Planned)*: Graph centrality, velocity analysis, and behavioral fraud scoring heuristics.
4. **Investigative Brief Generation** *(Planned)*: Dynamic PDF synthesis via ReportLab for field and court distribution.
