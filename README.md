CCP Default Waterfall Simulator

A Python simulation of a Central Counterparty (CCP) default management framework, modelling the sequential loss absorption waterfall triggered when a Clearing Member defaults — built with reference to Eurex Clearing AG's default management process.

Motivation

When a Clearing Member defaults, a CCP must absorb the resulting market losses in a defined, legally structured sequence. This project simulates that process end-to-end: from pricing a realistic derivatives portfolio, computing stress losses under multiple shock scenarios, and stepping through the default waterfall layer by layer.

The project is to understand the Default Management function at CCP, where the core mandate is precisely this — maintaining operational readiness to liquidate a defaulted member's portfolio swiftly and safely.

What It Models
Portfolio

The defaulted member holds a mixed derivatives book across three asset classes:

Instrument	Direction	Rationale
DAX Futures	Long	Equity directional exposure
EURO STOXX 50 Futures	Long	Broad European equity beta
Bund Futures	Short	Rate hedge (partial offset)
DAX Call options (OTM)	Short	Short gamma / vol seller
DAX Put options (OTM)	Short	Short gamma / vol seller
ESTX50 Call options (OTM)	Short	Short vega exposure

The portfolio is intentionally net long equity + short volatility — a combination that suffers compounding losses when markets crash and implied vol spikes simultaneously. This is a realistic risk profile that CCP default management desks are specifically designed to handle.

Greeks Computed
Delta — linear price sensitivity
Gamma — convexity (rate of delta change)
Vega — sensitivity to implied volatility
Option Pricing

Vanilla options are priced using the Black-Scholes model, implemented from scratch (no external libraries):

C = S·N(d1) − K·e^(−rT)·N(d2)
d1 = [ln(S/K) + (r + σ²/2)·T] / (σ·√T)
d2 = d1 − σ·√T
The Default Waterfall

Loss absorption follows the CCP waterfall in strict sequential order:

Gross Stress Loss
        │
        ▼
① Initial Margin (IM) of the defaulted member
        │  if insufficient ↓
        ▼
② Defaulted Member's Default Fund Contribution (DFC)
        │  if insufficient ↓
        ▼
③ CCP Skin-in-the-Game (the CCP's own dedicated capital)
        │  if insufficient ↓
        ▼
④ Mutualized Default Fund (other members' DFCs)
        │  if insufficient ↓
        ▼
⑤ Assessments, second skin-in-the-game, recovery tools ← not modelled here

The defaulter pays first (its margin, then its own default fund contribution). The CCP's own capital (Skin-in-the-Game) sits before the other members' contributions, which aligns the CCP's incentives with prudent risk management. This follows the structure of Eurex Clearing's published waterfall in simplified form; it omits assessments, the second skin-in-the-game and recovery tools.

Stress Scenarios

Four scenarios are run against the same portfolio:

Scenario	Price Shock	Vol Shock	Waterfall Triggered
A: Moderate	−5%	+5pp	IM only
B: Severe	−12%	+10pp	IM only
C: Extreme	−25%	+20pp	IM → defaulter's DFC
D: Catastrophic	−40%	+35pp	IM → DFC → SitG → Mutualized Fund
Sample Output (Scenario D)
##############################################################
  SCENARIO D: Catastrophic     (−40% price, +35pp vol)
##############################################################

══════════════════════════════════════════════════════════════
  CCP DEFAULT WATERFALL SIMULATOR — Eurex Clearing AG (Simulated)
══════════════════════════════════════════════════════════════

                [ DEFAULTED MEMBER PORTFOLIO ]                
──────────────────────────────────────────────────────────────
  Member : Alpha Bank AG (Clearing Member)
  Net Delta           :    2083.6893
  Net Gamma           :    -0.755498
  Net Vega            :  -4094359.07

  Instruments:
    DAX Future (Jun26)           LONG  800 contracts @ 18500.00
    EURO STOXX 50 (Jun26)        LONG  2000 contracts @ 4950.00
    Bund Future (Jun26)          SHORT  200 contracts @ 131.50
    DAX Call 19000 Sep26         SHORT  500 contracts  K=19000  σ=18%
    DAX Put 17500 Sep26          SHORT  400 contracts  K=17500  σ=20%
    ESTX50 Call 5100 Dec26       SHORT  800 contracts  K=5100  σ=16%

                     [ STRESS SCENARIO ]                      
──────────────────────────────────────────────────────────────
  Gross Stress Loss       : EUR  92,950,437.60
  Initial Margin Posted   : EUR  45,000,000.00

                    [ DEFAULT WATERFALL ]                     
──────────────────────────────────────────────────────────────

  STEP 1: Initial Margin (IM)
    Available  : EUR  45,000,000.00
    Absorbed   : EUR  45,000,000.00
    Status     : ✘  SHORTFALL: EUR 47,950,437.60

  STEP 2: Defaulted Member's Default Fund Contribution
    Available  : EUR  12,000,000.00
    Absorbed   : EUR  12,000,000.00
    Status     : ✘  SHORTFALL: EUR 35,950,437.60

  STEP 3: CCP Skin-in-the-Game (SitG)
    Available  : EUR  10,000,000.00
    Absorbed   : EUR  10,000,000.00
    Status     : ✘  SHORTFALL: EUR 25,950,437.60

  STEP 4: Mutualized Default Fund (other members' DFCs)
    Available  : EUR 168,000,000.00
    Absorbed   : EUR  25,950,437.60
    Status     : ✔  FULLY COVERED

──────────────────────────────────────────────────────────────
  Total Gross Loss        : EUR  92,950,437.60
  Uncovered Loss          : EUR           0.00
  Outcome                 : Waterfall absorbed all losses.
══════════════════════════════════════════════════════════════
How to Run

No external libraries required — pure Python 3.

bash
python ccp_default_simulator.py
Limitations

This is a simplified teaching model, not Eurex's methodology:

Initial margin is an input (EUR 45m), not calculated from a margin model, and there is no margin period of risk.
One shock applies to every instrument. In reality a fall in equities usually lifts Bund prices, so the short Bund future would lose, not gain. The Bund leg is a simplification.
Instant revaluation: losses are computed on the shocked prices at one point in time. Close-out costs, auction outcomes, liquidity and hedging are not modelled.
Black-Scholes assumes European exercise, constant rates and no dividends; options on futures would normally use Black-76.
Greeks reported are delta, gamma and vega (not theta or rho). They are shown for information and are not used in the loss calculation, which re-prices every position.
Contract sizes (notional) are illustrative, not real Eurex contract specifications.
Not modelled: assessments, second skin-in-the-game, recovery tools, multiple member defaults, default fund sizing (Cover 2), correlation between assets.
Built with AI assistance as a learning project. A small check script (test_ccp_simulator.py, plain Python asserts) covers put-call parity, Greeks vs numerical derivatives, futures P&L and waterfall conservation; it is not a full test suite.
Project Structure
ccp_default_simulator.py
│
├── Future                  # Linear futures position + P&L
├── VanillaOption           # B-S pricing, Greeks, shocked P&L
├── ClearingMember          # Portfolio holder + stress loss computation
├── CCPWaterfall            # Sequential waterfall logic + terminal output
└── run_scenarios()         # Entry point — 4 stress scenarios
Background

Built as a portfolio project to demonstrate applied knowledge of:

CCP risk architecture and default management frameworks
Derivatives pricing (Black-Scholes) and risk sensitivities (Greeks)
Stress testing methodology used in post-trade market infrastructure

Author: Athul | MSc International Business | CFA Level 1
**Author:** Athul | MSc International Business | CFA Level 1
