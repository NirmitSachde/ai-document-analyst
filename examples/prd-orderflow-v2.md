# OrderFlow — Product Requirements Document (v2.0)

**Owner:** Priya Ramaswamy, Product Lead
**Reviewers:** Alex Chen (Engineering), Marcus Webb (Design), Sarah Liu (Compliance)
**Target launch:** 2026-04-30
**Document version:** 2.0
**Last updated:** 2026-01-22

> **Change log:** v2 expands US-only support to include Canada at launch, adds a new "smart routing" requirement (3.5), tightens the WMS push latency target (3.3), and drops the freemium tier idea. See the `/compare` view for a structured diff.

## 1. Overview

OrderFlow is a B2B checkout platform for mid-market retailers (USD 10M–USD 250M annual revenue) selling on multiple marketplaces. It consolidates orders from Shopify, Amazon, eBay, and Walmart into a single fulfillment queue, applies routing rules, and pushes shipment instructions to the merchant's warehouse management system (WMS).

The v2 release targets the **United States and Canada**. EU expansion is planned for v3 (Q4 2026).

## 2. Goals

- Reduce time-to-ship by 50% versus manual order consolidation.
- Support at least four marketplaces at launch.
- Achieve 99.9% uptime during business hours (06:00–22:00 PT).
- Pass a SOC 2 Type II audit by end of Q3 2026.

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
- Routing decisions must be logged and exportable as CSV or JSON.

### 3.3 WMS integration

- The system must push shipment instructions to the merchant's WMS within **15 seconds** of order acceptance.
- The system must support ShipStation, ShipBob, Veeqo, and one custom REST webhook target.
- Failed WMS pushes must be queued and retried; merchants must be alerted via Slack or email after two consecutive failures.

### 3.4 Reporting

- Merchants must have a real-time dashboard showing orders received, orders routed, and orders failed in the last 24 hours.
- Merchants should be able to export historical data for any date range up to 730 days.

### 3.5 Smart routing (NEW)

- The system must offer an opt-in machine-learning routing mode that suggests the warehouse most likely to fulfill each order on time.
- The model must be retrained nightly using the merchant's last 90 days of shipment data.
- Merchants must be able to override smart routing on a per-order basis.

## 4. Non-functional requirements

- **Performance:** p95 order-to-shipment-instruction latency must be under 45 seconds.
- **Security:** All marketplace tokens must be encrypted at rest using AES-256-GCM.
- **Compliance:** The system must log every routing decision for at least seven years (US/CA tax retention).
- **Accessibility:** The merchant dashboard must meet WCAG 2.1 Level AA.

## 5. Out of scope (v2)

- EU marketplaces (Amazon EU, Rakuten, OTTO).
- Direct-to-consumer (DTC) order ingestion from merchant websites.
- Mobile app — web only at launch.

> The freemium tier proposed in v1 has been removed from scope. Pricing starts at USD 99/month.

## 6. Open questions

- Smart routing model — do we host it ourselves on GPU instances, or use a managed service like SageMaker? Owner: Alex. Due: 2026-02-10.

## 7. Action items

- Priya: finalize CA-specific pricing (CAD billing) by 2026-02-20.
- Alex: deliver technical design doc for the smart routing model by 2026-02-15.
- Marcus: update mockups for the smart routing toggle by 2026-02-28.
- Sarah: schedule SOC 2 Type II readiness assessment by 2026-03-15.
