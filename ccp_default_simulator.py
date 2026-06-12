"""
CCP Default Waterfall Simulator
================================
Simulates the default of a Clearing Member at a Central Counterparty (CCP).
Models a simple derivatives portfolio, computes stress losses, and steps through
the default waterfall: Initial Margin → Default Fund → Skin-in-the-Game → Mutualized Fund.

Author: Athul
Reference: Eurex Clearing default management framework
"""

import math
import random
from dataclasses import dataclass, field
from typing import List

# ─────────────────────────────────────────────
# 1. PORTFOLIO BUILDING BLOCKS
# ─────────────────────────────────────────────

@dataclass
class Future:
    name: str
    notional: float          # contract value in EUR
    position: int            # +ve = long, -ve = short
    current_price: float
    tick_size: float = 0.01

    def pnl(self, shocked_price: float) -> float:
        price_change = shocked_price - self.current_price
        return self.position * self.notional * price_change / self.current_price

    def delta(self) -> float:
        return float(self.position)  # delta = 1 per contract for futures


@dataclass
class VanillaOption:
    name: str
    notional: float
    position: int            # +ve = long, -ve = short
    option_type: str         # 'call' or 'put'
    spot: float
    strike: float
    time_to_expiry: float    # in years
    vol: float               # implied vol (e.g. 0.20 = 20%)
    risk_free_rate: float = 0.04

    def _d1_d2(self, spot=None):
        S = spot or self.spot
        K = self.strike
        T = self.time_to_expiry
        r = self.risk_free_rate
        v = self.vol
        if T <= 0 or S <= 0:
            return 0, 0
        d1 = (math.log(S / K) + (r + 0.5 * v**2) * T) / (v * math.sqrt(T))
        d2 = d1 - v * math.sqrt(T)
        return d1, d2

    @staticmethod
    def _norm_cdf(x: float) -> float:
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2)))

    def price(self, spot=None) -> float:
        S = spot or self.spot
        K = self.strike
        T = self.time_to_expiry
        r = self.risk_free_rate
        d1, d2 = self._d1_d2(S)
        if self.option_type == 'call':
            return S * self._norm_cdf(d1) - K * math.exp(-r * T) * self._norm_cdf(d2)
        else:
            return K * math.exp(-r * T) * self._norm_cdf(-d2) - S * self._norm_cdf(-d1)

    def pnl(self, shocked_spot: float, shocked_vol: float = None) -> float:
        vol = shocked_vol or self.vol
        original = VanillaOption(
            self.name, self.notional, self.position, self.option_type,
            self.spot, self.strike, self.time_to_expiry, self.vol, self.risk_free_rate
        )
        shocked = VanillaOption(
            self.name, self.notional, self.position, self.option_type,
            shocked_spot, self.strike, self.time_to_expiry, vol, self.risk_free_rate
        )
        return self.position * self.notional * (shocked.price() - original.price())

    def delta(self) -> float:
        d1, _ = self._d1_d2()
        if self.option_type == 'call':
            return self.position * self._norm_cdf(d1)
        else:
            return self.position * (self._norm_cdf(d1) - 1)

    def gamma(self) -> float:
        d1, _ = self._d1_d2()
        T = self.time_to_expiry
        if T <= 0:
            return 0
        return self.position * (math.exp(-0.5 * d1**2) / math.sqrt(2 * math.pi)) / (self.spot * self.vol * math.sqrt(T))

    def vega(self) -> float:
        d1, _ = self._d1_d2()
        T = self.time_to_expiry
        return self.position * self.spot * math.sqrt(T) * (math.exp(-0.5 * d1**2) / math.sqrt(2 * math.pi))


# ─────────────────────────────────────────────
# 2. CLEARING MEMBER
# ─────────────────────────────────────────────

@dataclass
class ClearingMember:
    name: str
    initial_margin: float        # IM posted with CCP (EUR)
    default_fund_contribution: float  # DFC posted (EUR)
    portfolio_futures: List[Future] = field(default_factory=list)
    portfolio_options: List[VanillaOption] = field(default_factory=list)

    def portfolio_summary(self) -> dict:
        total_delta = sum(f.delta() for f in self.portfolio_futures)
        total_delta += sum(o.delta() for o in self.portfolio_options)
        total_gamma = sum(o.gamma() for o in self.portfolio_options)
        total_vega = sum(o.vega() for o in self.portfolio_options)
        return {
            "Net Delta": round(total_delta, 4),
            "Net Gamma": round(total_gamma, 6),
            "Net Vega":  round(total_vega, 2),
        }

    def stress_loss(self, price_shock_pct: float, vol_shock_pct: float) -> float:
        """Compute total portfolio loss under a price + vol shock."""
        loss = 0.0
        for f in self.portfolio_futures:
            shocked_price = f.current_price * (1 + price_shock_pct)
            loss -= f.pnl(shocked_price)   # loss = negative PnL
        for o in self.portfolio_options:
            shocked_spot = o.spot * (1 + price_shock_pct)
            shocked_vol  = o.vol + vol_shock_pct
            loss -= o.pnl(shocked_spot, shocked_vol)
        return max(loss, 0.0)   # only positive losses matter


# ─────────────────────────────────────────────
# 3. CCP DEFAULT WATERFALL
# ─────────────────────────────────────────────

@dataclass
class CCPWaterfall:
    ccp_name: str
    skin_in_the_game: float          # CCP's own capital at risk (EUR)
    total_default_fund: float        # Sum of all members' DFCs (EUR)

    def run(self, defaulted_member: ClearingMember, gross_loss: float) -> None:
        sep = "─" * 62

        print(f"\n{'═' * 62}")
        print(f"  CCP DEFAULT WATERFALL SIMULATOR — {self.ccp_name}")
        print(f"{'═' * 62}")

        # ── Portfolio Summary ──────────────────────────────────────
        print(f"\n{'[ DEFAULTED MEMBER PORTFOLIO ]':^62}")
        print(sep)
        print(f"  Member : {defaulted_member.name}")
        greeks = defaulted_member.portfolio_summary()
        for k, v in greeks.items():
            print(f"  {k:<20}: {v:>12}")

        print(f"\n  Instruments:")
        for f in defaulted_member.portfolio_futures:
            direction = "LONG" if f.position > 0 else "SHORT"
            print(f"    {f.name:<28} {direction}  {abs(f.position)} contracts @ {f.current_price:.2f}")
        for o in defaulted_member.portfolio_options:
            direction = "LONG" if o.position > 0 else "SHORT"
            print(f"    {o.name:<28} {direction}  {abs(o.position)} contracts  K={o.strike:.0f}  σ={o.vol*100:.0f}%")

        # ── Stress Loss ────────────────────────────────────────────
        print(f"\n{'[ STRESS SCENARIO ]':^62}")
        print(sep)
        print(f"  Gross Stress Loss       : EUR {gross_loss:>14,.2f}")
        print(f"  Initial Margin Posted   : EUR {defaulted_member.initial_margin:>14,.2f}")

        # ── Waterfall Steps ────────────────────────────────────────
        print(f"\n{'[ DEFAULT WATERFALL ]':^62}")
        print(sep)

        remaining = gross_loss
        step = 1

        # Step 1: Initial Margin
        im_used = min(remaining, defaulted_member.initial_margin)
        remaining -= im_used
        covered = "✔  FULLY COVERED" if remaining == 0 else f"✘  SHORTFALL: EUR {remaining:,.2f}"
        print(f"\n  STEP {step}: Initial Margin (IM)")
        print(f"    Available  : EUR {defaulted_member.initial_margin:>14,.2f}")
        print(f"    Absorbed   : EUR {im_used:>14,.2f}")
        print(f"    Status     : {covered}")

        if remaining == 0:
            self._print_footer(gross_loss, 0)
            return

        # Step 2: CCP Skin-in-the-Game
        step += 1
        sitg_used = min(remaining, self.skin_in_the_game)
        remaining -= sitg_used
        covered = "✔  FULLY COVERED" if remaining == 0 else f"✘  SHORTFALL: EUR {remaining:,.2f}"
        print(f"\n  STEP {step}: CCP Skin-in-the-Game (SitG)")
        print(f"    Available  : EUR {self.skin_in_the_game:>14,.2f}")
        print(f"    Absorbed   : EUR {sitg_used:>14,.2f}")
        print(f"    Status     : {covered}")

        if remaining == 0:
            self._print_footer(gross_loss, 0)
            return

        # Step 3: Defaulted Member's Default Fund Contribution
        step += 1
        dfc_used = min(remaining, defaulted_member.default_fund_contribution)
        remaining -= dfc_used
        covered = "✔  FULLY COVERED" if remaining == 0 else f"✘  SHORTFALL: EUR {remaining:,.2f}"
        print(f"\n  STEP {step}: Defaulted Member's Default Fund Contribution")
        print(f"    Available  : EUR {defaulted_member.default_fund_contribution:>14,.2f}")
        print(f"    Absorbed   : EUR {dfc_used:>14,.2f}")
        print(f"    Status     : {covered}")

        if remaining == 0:
            self._print_footer(gross_loss, 0)
            return

        # Step 4: Mutualized Default Fund (other members)
        step += 1
        mutualized_pool = self.total_default_fund - defaulted_member.default_fund_contribution
        mutual_used = min(remaining, mutualized_pool)
        remaining -= mutual_used
        covered = "✔  FULLY COVERED" if remaining == 0 else f"⚠  UNCOVERED LOSS: EUR {remaining:,.2f}  → CCP RECOVERY TOOLS"
        print(f"\n  STEP {step}: Mutualized Default Fund (other members' DFCs)")
        print(f"    Available  : EUR {mutualized_pool:>14,.2f}")
        print(f"    Absorbed   : EUR {mutual_used:>14,.2f}")
        print(f"    Status     : {covered}")

        self._print_footer(gross_loss, remaining)

    def _print_footer(self, gross_loss: float, uncovered: float) -> None:
        print(f"\n{'─' * 62}")
        print(f"  Total Gross Loss        : EUR {gross_loss:>14,.2f}")
        print(f"  Uncovered Loss          : EUR {uncovered:>14,.2f}")
        if uncovered == 0:
            print(f"  Outcome                 : Waterfall absorbed all losses.")
        else:
            print(f"  Outcome                 : Waterfall exhausted. CCP would")
            print(f"                            activate recovery tools (VMGH,")
            print(f"                            partial tear-up, or assessment).")
        print(f"{'═' * 62}\n")


# ─────────────────────────────────────────────
# 4. SCENARIO RUNNER
# ─────────────────────────────────────────────

def run_scenarios():
    # ── Build defaulted member's portfolio ────────────────────────
    member = ClearingMember(
        name="Alpha Bank AG (Clearing Member)",
        initial_margin=45_000_000,          # EUR 45m IM
        default_fund_contribution=12_000_000 # EUR 12m DFC
    )

    # Futures positions — net LONG equity, net SHORT bonds
    # In a market crash: equity longs bleed heavily, bond shorts partially offset
    member.portfolio_futures = [
        Future("DAX Future (Jun26)",    notional=125_000, position=800,  current_price=18_500),
        Future("EURO STOXX 50 (Jun26)", notional=10_000,  position=2000, current_price=4_950),
        Future("Bund Future (Jun26)",   notional=100_000, position=-200, current_price=131.5),
    ]

    # Options — short gamma (sold calls + sold puts = short vol)
    # Vol spike hurts both short call and short put positions
    member.portfolio_options = [
        VanillaOption("DAX Call 19000 Sep26",  notional=25, position=-500,
                      option_type='call', spot=18_500, strike=19_000,
                      time_to_expiry=0.25, vol=0.18),
        VanillaOption("DAX Put 17500 Sep26",   notional=25, position=-400,
                      option_type='put',  spot=18_500, strike=17_500,
                      time_to_expiry=0.25, vol=0.20),
        VanillaOption("ESTX50 Call 5100 Dec26",notional=10, position=-800,
                      option_type='call', spot=4_950,  strike=5_100,
                      time_to_expiry=0.50, vol=0.16),
    ]

    # ── CCP parameters ────────────────────────────────────────────
    ccp = CCPWaterfall(
        ccp_name="Eurex Clearing AG (Simulated)",
        skin_in_the_game=10_000_000,     # EUR 10m SitG
        total_default_fund=180_000_000   # EUR 180m total default fund
    )

    # ── Three stress scenarios ─────────────────────────────────────
    scenarios = [
        ("SCENARIO A: Moderate Stress  (−5% price, +5pp vol)",    -0.05,  0.05),
        ("SCENARIO B: Severe Stress    (−12% price, +10pp vol)",   -0.12,  0.10),
        ("SCENARIO C: Extreme Stress   (−25% price, +20pp vol)",   -0.25,  0.20),
        ("SCENARIO D: Catastrophic     (−40% price, +35pp vol)",   -0.40,  0.35),
    ]

    for label, price_shock, vol_shock in scenarios:
        print(f"\n{'#' * 62}")
        print(f"  {label}")
        print(f"{'#' * 62}")
        gross_loss = member.stress_loss(price_shock, vol_shock)
        ccp.run(member, gross_loss)


# ─────────────────────────────────────────────
# 5. ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    run_scenarios()
