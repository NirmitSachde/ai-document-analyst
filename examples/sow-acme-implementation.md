# Statement of Work — Acme Corp ↔ Northbeam Consulting

**Project:** OrderFlow implementation and merchant migration
**SOW number:** SOW-2026-014
**Effective date:** 2026-02-01
**Estimated completion:** 2026-05-30
**Total fixed price:** USD 184,500

## 1. Parties

This Statement of Work ("SOW") is entered into between **Acme Corp.** ("Client") and **Northbeam Consulting LLC** ("Provider") under the Master Services Agreement dated 2025-08-12.

## 2. Background

Client operates 14 retail brands across the United States and is migrating from a legacy in-house order management system to OrderFlow, a third-party SaaS platform. Provider will deliver implementation, data migration, and training services as described below.

## 3. Scope of work

### 3.1 Discovery and planning (weeks 1–3)

- Conduct three on-site workshops at Client's Austin, TX headquarters.
- Document the current-state order routing logic across all 14 brands.
- Produce a target-state design document for OrderFlow rule configuration.
- Deliverable: signed-off design document by 2026-02-21.

### 3.2 Configuration and integration (weeks 4–10)

- Configure OrderFlow rules for all 14 brands.
- Integrate with Client's existing ShipBob and ShipStation accounts.
- Build one custom REST webhook receiver for Client's proprietary WMS, "AcmeWarehouse-3000."
- Migrate the last 24 months of historical order data into OrderFlow's reporting tables.

### 3.3 User acceptance testing (weeks 11–13)

- Run a parallel-shipment pilot for two brands ("Acme Outdoor" and "Acme Pet Supplies") for 14 calendar days.
- Document any discrepancies between legacy and OrderFlow routing decisions.
- Pilot acceptance criteria: under 1% material discrepancy across 5,000+ orders.

### 3.4 Cutover and training (weeks 14–17)

- Cut all 14 brands over to OrderFlow in three phased waves.
- Deliver 8 hours of live training to Client's operations team (max 20 attendees per session).
- Provide a recorded library of standard operating procedures.

## 4. Pricing

| Phase                          | Fixed fee (USD) | Payment trigger                |
| ------------------------------ | --------------- | ------------------------------ |
| Discovery and planning         | 24,500          | On signed design document      |
| Configuration and integration  | 95,000          | 50% on start of phase, 50% on UAT entry |
| User acceptance testing        | 35,000          | On pilot acceptance            |
| Cutover and training           | 30,000          | On final cutover               |
| **Total**                      | **184,500**     |                                |

Out-of-pocket travel expenses are reimbursable at cost up to USD 12,000 over the project duration. Any amount above that requires written approval from Client's project sponsor.

## 5. Assumptions

- Client will make at least one operations team member available for 50% of their working time across the project.
- Client will provide read-only access to all marketplace and WMS systems by 2026-02-08.
- All Client deliverables (e.g. rule sign-offs) will be returned within 5 business days; delays beyond 5 business days may trigger a schedule extension.

## 6. Out of scope

- DTC website integration (Client's Shopify storefronts) — covered under separate SOW.
- Custom report development beyond OrderFlow's standard reporting suite.
- Ongoing managed services post-cutover — handled under a separate Managed Services Agreement.

## 7. Compliance and security

- Provider personnel must complete Client's vendor security training before accessing any production system.
- Provider must comply with Client's data handling policy (DOC-SEC-014, v3).
- Provider must immediately notify Client of any suspected data breach involving Client data and must cooperate with any required forensic investigation.

## 8. Signatures

| Party       | Name              | Title                    | Date       |
| ----------- | ----------------- | ------------------------ | ---------- |
| Client      | Diana Whitfield   | VP Operations, Acme Corp |            |
| Provider    | Marcus Thompson   | Principal, Northbeam     |            |
