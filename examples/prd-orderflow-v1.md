# OrderFlow — Product Requirements Document (v1.0)

**Owner:** Priya Ramaswamy, Product Lead
**Reviewers:** Alex Chen (Engineering), Marcus Webb (Design), Sarah Liu (Compliance)
**Target launch:** 2026-03-15
**Document version:** 1.0
**Last updated:** 2025-11-04

## 1. Overview

OrderFlow is a B2B checkout platform for mid-market retailers (USD 10M–USD 250M annual revenue) selling on multiple marketplaces. It consolidates orders from Shopify, Amazon, eBay, and Walmart into a single fulfillment queue, applies routing rules, and pushes shipment instructions to the merchant's warehouse management system (WMS).

The v1 release targets US-based merchants only. International expansion is planned for v2 (Q3 2026).

## 2. Goals

- Reduce time-to-ship by 40% versus manual order consolidation.
- Support at least four marketplaces at launch.
- Achieve 99.5% uptime during business hours (06:00–22:00 PT).
- Pass a SOC 2 Type I audit by end of Q2 2026.

## 3. Functional requirements

### 3.1 Order ingestion

- The system must poll each connected marketplace API every 60 seconds for new orders.
- The system must support OAuth 2.0 authorization for marketplace connections.
- The system should deduplicate orders that appear in multiple marketplaces under the same SKU within a 5-minute window.
- The system may retry failed API calls up to three times with exponential backoff (1s, 5s, 25s).

### 3.2 Routing rules

- Merchants must be able to define routing rules in a visual rule builder (no SQL or scripting required).
- Each rule must support up to 10 conditions joined by AND/OR.
- The system must evaluate rules in priority order and apply only the first matching rule.
- Routing decisions must be logged and exportable as CSV.

### 3.3 WMS integration

- The system must push shipment instructions to the merchant's WMS within 30 seconds of order acceptance.
- The system must support ShipStation, ShipBob, and one custom REST webhook target.
- Failed WMS pushes must be queued and retried; merchants must be alerted after three consecutive failures.

### 3.4 Reporting

- Merchants must have a real-time dashboard showing orders received, orders routed, and orders failed in the last 24 hours.
- Merchants should be able to export historical data for any date range up to 365 days.

## 4. Non-functional requirements

- **Performance:** p95 order-to-shipment-instruction latency must be under 90 seconds.
- **Security:** All marketplace tokens must be encrypted at rest using AES-256.
- **Compliance:** The system must log every routing decision for at least seven years (US tax retention requirement).
- **Accessibility:** The merchant dashboard must meet WCAG 2.1 Level AA.

## 5. Out of scope (v1)

- International marketplaces (Amazon EU, Rakuten, MercadoLibre).
- Multi-currency support — USD only at launch.
- Direct-to-consumer (DTC) order ingestion from merchant websites.
- Mobile app — web only at launch.

## 6. Open questions

- Should we offer a free tier with one marketplace connection? Owner: Priya. Due: 2025-11-20.
- WMS integration with custom webhook — do we provide a hosted webhook receiver or require merchants to expose one? Owner: Alex. Due: 2025-12-01.

## 7. Action items

- Priya: finalize pricing tiers by 2025-12-15.
- Alex: deliver technical design doc for the rule engine by 2025-12-08.
- Marcus: deliver mockups for the merchant dashboard by 2025-12-22.
- Sarah: schedule SOC 2 readiness assessment by 2026-01-10.
