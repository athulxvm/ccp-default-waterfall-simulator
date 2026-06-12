# CCP Default Waterfall Simulator

A Python simulation of a Central Counterparty (CCP) default management framework, modelling the sequential loss absorption waterfall triggered when a Clearing Member defaults — built with reference to Eurex Clearing AG's default management process.

---

## Motivation

When a Clearing Member defaults, a CCP like Eurex Clearing must absorb the resulting market losses in a defined, legally structured sequence. This project simulates that process end-to-end: from pricing a realistic derivatives portfolio, computing stress losses under multiple shock scenarios, and stepping through the default waterfall layer by layer.

The project is inspired by the Credit Risk & Default Management function at Eurex Clearing, where the core mandate is precisely this — maintaining operational readiness to liquidate a defaulted member's portfolio swiftly and safely.

---

## What It Models

### Portfolio
The defaulted member holds a mixed derivatives book across three asset classes:

| Instrument | Direction | Rationale |
|---|---|---|
| DAX Futures | Long | Equity directional exposure |
| EURO STOXX 50 Futures | Long | Broad European equity beta |
| Bund Futures | Short | Rate hedge (partial offset) |
| DAX Call options (OTM) | Short | Short gamma / vol seller |
| DAX Put options (OTM) | Short | Short gamma / vol seller |
| ESTX50 Call options (OTM) | Short | Short vega exposure |

The portfolio is intentionally **net long equity + short volatility** — a combination that suffers compounding losses when markets crash and implied vol spikes simultaneously. This is a realistic risk profile that CCP default management desks are specifically designed to handle.

### Greeks Computed
- **Delta** — linear price sensitivity
- **Gamma** — convexity (rate of delta change)
- **Vega** — sensitivity to implied volatility

### Option Pricing
Vanilla options are priced using the **Black-Scholes model**, implemented from scratch (no external libraries):

```
C = S·N(d1) − K·e^(−rT)·N(d2)
d1 = [ln(S/K) + (r + σ²/2)·T] / (σ·√T)
d2 = d1 − σ·√T
```

---

## The Default Waterfall

Loss absorption follows the CCP waterfall in strict sequential order:

```
Gross Stress Loss
        │
        ▼
① Initial Margin (IM)
        │  if insufficient ↓
        ▼
② CCP Skin-in-the-Game
        │  if insufficient ↓
        ▼
③ Defaulted Member's Default Fund Contribution (DFC)
        │  if insufficient ↓
        ▼
④ Mutualized Default Fund (other members' DFCs)
        │  if insufficient ↓
        ▼
⑤ Recovery Tools (VMGH, partial tear-up) ← not modelled here
```

The CCP Skin-in-the-Game sits at Step 2 — before the mutualized fund — to align the CCP's own incentives with prudent risk management.

---

## Stress Scenarios

Four scenarios are run against the same portfolio:

| Scenario | Price Shock | Vol Shock | Waterfall Triggered |
|---|---|---|---|
| A: Moderate | −5% | +5pp | IM only |
| B: Severe | −12% | +10pp | IM only |
| C: Extreme | −25% | +20pp | IM → SitG |
| D: Catastrophic | −40% | +35pp | IM → SitG → DFC → Mutualized Fund |

---

## Sample Output (Scenario D)

```
##############################################################
  SCENARIO D: Catastrophic     (−40% price, +35pp vol)
##############################################################

══════════════════════════════════════════════════════════════
  CCP DEFAULT WATERFALL SIMULATOR — Eurex Clearing AG (Simulated)
══════════════════════════════════════════════════════════════

  Member : Alpha Bank AG (Clearing Member)
  Net Delta           :    2083.6893
  Net Gamma           :    -0.755498
  Net Vega            :  -4094359.07

  Gross Stress Loss       : EUR   92,950,437.60
  Initial Margin Posted   : EUR   45,000,000.00

  STEP 1: Initial Margin (IM)
    Available  : EUR  45,000,000.00
    Absorbed   : EUR  45,000,000.00
    Status     : ✘  SHORTFALL: EUR 47,950,437.60

  STEP 2: CCP Skin-in-the-Game (SitG)
    Available  : EUR  10,000,000.00
    Absorbed   : EUR  10,000,000.00
    Status     : ✘  SHORTFALL: EUR 37,950,437.60

  STEP 3: Defaulted Member's Default Fund Contribution
    Available  : EUR  12,000,000.00
    Absorbed   : EUR  12,000,000.00
    Status     : ✘  SHORTFALL: EUR 25,950,437.60

  STEP 4: Mutualized Default Fund (other members' DFCs)
    Available  : EUR 168,000,000.00
    Absorbed   : EUR  25,950,437.60
    Status     : ✔  FULLY COVERED

  Outcome : Waterfall absorbed all losses.
══════════════════════════════════════════════════════════════
```

---

## How to Run

No external libraries required — pure Python 3.

```bash
python ccp_default_simulator.py
```

---

## Project Structure

```
ccp_default_simulator.py
│
├── Future                  # Linear futures position + P&L
├── VanillaOption           # B-S pricing, Greeks, shocked P&L
├── ClearingMember          # Portfolio holder + stress loss computation
├── CCPWaterfall            # Sequential waterfall logic + terminal output
└── run_scenarios()         # Entry point — 4 stress scenarios
```

---

## Background

Built as a portfolio project to demonstrate applied knowledge of:
- CCP risk architecture and default management frameworks
- Derivatives pricing (Black-Scholes) and risk sensitivities (Greeks)
- Stress testing methodology used in post-trade market infrastructure

**Author:** Athul | MSc International Business (Financial Markets), Hochschule Mainz | CFA Level 1
