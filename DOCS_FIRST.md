# Docs first. Reading list and what this study will verify

Status: written 2026-11-09 UTC before any chain data was fetched. Section 5 and the link updates were added later the same day.

Method note. Every claim below that the study relies on was checked against the raw text of the cited page on 2026-11-09. Corrections from that check are listed in section 5. Where a page could not be retrieved, it is marked as pending.

## 1. Reading list

### Curve crvUSD, developer docs
| # | Source | URL | Used for |
|---|---|---|---|
| C1 | crvUSD overview | https://docs.curve.finance/developer/crvusd/overview | Architecture, Controller and AMM versions per market |
| C2 | LLAMMA (AMM) reference | https://docs.curve.finance/developer/crvusd/amm | Bands, active band, events, fees |
| C3 | LLAMMA explainer | https://docs.curve.finance/developer/crvusd/llamma-explainer | Soft and de-liquidation, sources of loss, health |
| C4 | Controller | https://docs.curve.finance/developer/crvusd/controller | Health formula, liquidate, discounts, events |
| C5 | Monetary policy overview | https://docs.curve.finance/developer/crvusd/monetary-policy/overview | Rate formula, AggMonetaryPolicy v4 |
| C6 | Oracles overview | https://docs.curve.finance/developer/crvusd/oracles/overview | Collateral oracle families, Chainlink bound, TVL EMA |
| C7 | PegKeepers overview | https://docs.curve.finance/developer/crvusd/pegkeepers/overview | PegKeeperV2 plus Regulator split |
| C8 | PegKeeperV2 | https://docs.curve.finance/developer/crvusd/pegkeepers/peg-keeper-v2 | update(), Provide and Withdraw events, action_delay |
| C9 | PegKeeperRegulator | https://docs.curve.finance/developer/crvusd/pegkeepers/peg-keeper-regulator | provide_allowed and withdraw_allowed checks |
| C10 | Llamalend v2 overview | https://docs.curve.finance/developer/llamalend-v2/overview | Isolated markets versus mint markets |
| C11 | Security and audits | https://docs.curve.finance/developer/security/ | Audit list |
| C12 | Deployments | https://docs.curve.finance/developer/deployments | crvUSD, ControllerFactory, PegKeepers, Regulator, aggregator |

### Curve resources (user docs)
| # | Source | URL | Used for |
|---|---|---|---|
| R1 | Borrowing, borrow rates | https://docs.curve.finance/user/llamalend/borrowing | Rate direction versus peg |
| R1b | crvUSD risks | https://docs.curve.finance/user/security/risks/crvusd | Rate rises as PegKeeper (reserve) debt share falls, hard liquidation at zero health |
| R2 | Loan concepts in depth | https://resources.curve.fi/crvusd/loan-concepts | Health terms, losses on both legs |
| R3 | Loan details | https://resources.curve.fi/crvusd/loan-details/ | Soft liquidation mode, losses only inside bands |
| R4 | Llamalend liquidation guide | https://docs.curve.finance/user/llamalend/guides/borrow/liquidation | Full liquidation when health reaches 0% |
| R5 | Lending overview (former resources site, page since removed) | resources.curve.finance/lending/overview | Stated typical soft liquidation loss. Read on 2026-11-09, no longer on the live docs, not used in any chart |

### Yield Basis docs
| # | Source | URL | Used for |
|---|---|---|---|
| Y1 | How YieldBasis works | https://docs.yieldbasis.com/user/overview/how-yieldbasis-works | 2x leverage, equal value of crvUSD borrowed |
| Y2 | Arbitrage (dev) | https://docs.yieldbasis.com/dev/integration/arbitrage | Direction of arbitrage flows by DTV regime |
| Y3 | Rebalance action flow (dev) | https://docs.yieldbasis.com/dev/action-flows/rebalance | VirtualPool steps, flash loan repayment |
| Y4 | Arbitrage and MEV | https://docs.yieldbasis.com/user/economics/arbitrage-and-mev | Who pays, who keeps the spread |
| Y5 | Compounding leverage | https://docs.yieldbasis.com/user/protocol/compounding-leverage | Safety band, refueling, oracle source |
| Y6 | Oracle design | https://docs.yieldbasis.com/user/economics/oracle-design | price_scale lag, Pyth reports, crvUSD price input |
| Y7 | Contract addresses | https://docs.yieldbasis.com/user/reference/contract-addresses | Markets 0 to 10, Factory, LEVAMM, VirtualPool |

### Governance
| # | Source | URL | Used for |
|---|---|---|---|
| G1 | Create a crvUSD credit line to Yield Basis | https://gov.curve.finance/t/create-a-crvusd-credit-line-to-yield-basis/10774 | 60M line, supply sink argument, risk objections |
| G2 | Increase crvUSD caps for YB pools to 300M crvUSD | https://gov.curve.finance/t/increase-crvusd-caps-for-yb-pools-to-300m-crvusd/10867 | 300M cap |
| G3 | Set of proposals for further increasing YB pool capacity | https://gov.curve.finance/t/set-of-proposals-for-further-increasing-yb-pool-capacity-and-scaling-crvusd/10897 | PegKeeper capacity needed per YB TVL |
| G4 | Increase credit line for Yield Basis to 1B crvUSD | https://gov.curve.finance/t/increase-credit-line-for-yield-basis-to-1b-crvusd/10945 | Observed pool imbalance, parking estimate, LlamaRisk objection |
| G5 | Increase credit line to Yield Basis to 1B crvUSD (first thread) | https://gov.curve.finance/t/increase-credit-line-to-yield-basis-to-1b-crvusd/10930 | Pangea research on peg deviation after YB |
| G6 | LlamaRisk progress update July to December 2025 | https://gov.curve.finance/t/llamarisk-progress-update-july-december-2025/10981 | YB effect on PegKeeper reserves and peg |

### Audits
| # | Auditor | Scope | Date | URL |
|---|---|---|---|---|
| A1 | MixBytes | crvUSD infrastructure | 2023-06-05 | https://docs.curve.finance/pdf/audits/Curve%20Stablecoin%20%28crvUSD%29%20Security%20Audit%20Report.pdf |
| A2 | ChainSecurity | crvUSD infrastructure | 2024-01-24 | https://docs.curve.finance/pdf/audits/ChainSecurity_Curve_Curve_Stablecoin_audit-1.pdf |
| A3 | ChainSecurity | crvUSD infrastructure | 2025-02-21 | https://docs.curve.finance/pdf/audits/ChainSecurity_Curve_Curve_Stablecoin_audit_250221.pdf |
| A4 | ChainSecurity | PegKeeperV2 | 2023-12-12 | https://docs.curve.finance/pdf/audits/ChainSecurity_Curve_PegKeeperV2_audit.pdf |

### Pending, not yet read
- crvUSD whitepaper. The GitHub PDF did not load. Needed for the band math and the original loss simulation.
- Audit PDF contents. Listed, not read.
- LlamaRisk dedicated report on YB flows. G6 says it is "to be published". Not found.
- Pangea research on YB flows and peg (referenced in G4 and G5). Link not found yet.
- Yield Basis math primer, risks page and audits page.
- Exact AggMonetaryPolicy v4 parameters (rate0, sigma, target fraction) for each market. To be read from chain.
- Comparison protocols: Aave v3, Fluid, Liquity v2, Morpho Blue liquidation docs. Read in phase 2 before their data is pulled.

## 2. Mechanism notes that change the analysis

1. Soft liquidation runs per band, not per user, and only when arbitrageurs trade against LLAMMA (C3). Losses come from the gap between the AMM price and the oracle price, on the way down and on the way back up (C3, R2). The docs do not quantify the loss in a fast move (C3). The only number found is "typical losses are <0.1% per day" for mint markets (R5).
2. When collateral falls, arbitrageurs buy collateral from LLAMMA and pay crvUSD (C3). That trade needs crvUSD. So LLAMMA soft liquidation should create crvUSD buy pressure in the peg pools, not sell pressure.
3. Hard liquidation is open to third parties only when full health is below zero, using the per-user liquidation discount (C4). Liquidators must bring crvUSD (C4). This is also buy pressure.
4. PegKeeperV2 can only withdraw crvUSD it previously deposited, only when the price is below 1, and the Regulator can return zero (C8, C9). V1 withdrew one fifth of the imbalance per call with a 15 minute delay (docs.curve.fi PegKeeper page). V2 keeps an action_delay. Whether the one fifth rule and the delay values still hold in V2 will be read from chain.
5. The borrow rate formula is r = rate0 times exp(power), with power = (1 minus price_crvusd) / sigma minus DebtFraction / TargetFraction (C5). v4 uses an EMA of the debt ratio (C5). So the rate rises when crvUSD is below 1 and rises further when PegKeeper debt falls (R1). Both inputs are smoothed, so the rate should lag the price.
6. Yield Basis has two arbitrage venues per market, the Curve pool and the LEVAMM (Y3, Y4). Their directions in a price drop are opposite for crvUSD.
   - Curve pool leg. If the asset falls on external venues, arbitrageurs sell the asset into the YB Curve pool and take crvUSD out. That crvUSD has to go somewhere, most likely the peg pools. This is the sell pressure in G4 and G6.
   - LEVAMM leg. When price falls, DTV goes above 50 percent. Arbitrageurs supply crvUSD and receive the asset. Debt is repaid and crvUSD supply shrinks (Y2). This leg needs crvUSD, so it is buy pressure.
   - The net depends on timing. The LEVAMM uses price_scale, which moves in capped steps and follows its target over hours (Y6). So the LEVAMM leg should lag the Curve pool leg. The brief statement that arbitrageurs supply crvUSD above target DTV and receive it below target matches Y2.
7. Market 10 (WETH) runs YBOraclizedPolicy with signed Pyth reports, while markets 7 to 9 (BTC) run YBTwocryptoPolicy (Y7, Y6). An ETH flush therefore hits a YB market directly, and the ETH market price_scale can move faster than the BTC ones.
8. LlamaRisk already reported that YB sometimes sells crvUSD during below peg conditions and that large PegKeeper reserve changes move almost one for one with YB flows (G6). This study tests that claim on one event. It does not establish causality in general.
9. The YB oracle multiplies by Curve's crvUSD/USD aggregator price (Y6). A crvUSD depeg therefore feeds back into YB LP valuation. Size of this effect to be measured.

## 3. Documented vs to be measured

| Topic | What the docs claim | Source | What this study will measure on chain |
|---|---|---|---|
| Soft liquidation trigger | Conversion happens only through arbitrage trades against LLAMMA, by band | C3 | TokenExchange events per market. Time from oracle entering a band to first conversion in it |
| Soft liquidation loss | Loss exists on both legs, hard to quantify, more bands and better arbitrage reduce it | C3, R2 | Per market loss = oracle value of collateral sold minus crvUSD received, plus the same on de-liquidation. Compared with a hold baseline |
| Effect on crvUSD demand | Arbitrageurs pay crvUSD for collateral in a drop | C3 | Net crvUSD that LLAMMA arbitrage addresses bought or sold in peg pools |
| Hard liquidation | Third party liquidation only when full health is below zero, liquidator repays debt | C4, R4 | Liquidate events, count, debt, implied discount, any position with debt above collateral value |
| Bad debt | Not stated | none | Positions closed or open with negative equity at window end |
| Oracle lag | Collateral oracles use pool EMAs, TVL weights EMA of about 13.9 hours, Chainlink bound of 1.5 percent where enabled | C6 | Oracle price versus external price path. Lag in seconds at the trough |
| PegKeeper action | Withdraw only below 1 and only up to prior deposits. Regulator checks can return zero. Delay between actions | C7, C8, C9 | Provide and Withdraw events, amounts, gaps between calls, debt before and after, calls that returned zero |
| PegKeeper capacity | Reserve depth became a binding constraint | G6 | Debt per PegKeeper at window start and trough. Share of debt withdrawn |
| Borrow rate | Rises when crvUSD is below 1 and when PegKeeper debt falls. Smoothed inputs | C5, R1 | rate() per market before, during and after |
| Peg path | Not documented as a target band | none | Block level price in each PegKeeper pool. Minimum, time below 0.997 and 0.995, recovery time |
| YB regime | DTV above 50 percent after a price drop. Arbitrageurs then supply crvUSD to LEVAMM | Y2 | DTV path per YB market from LEVAMM state. Sign of each LEVAMM trade |
| YB Curve pool leg | Arbitrage keeps the pool near market price | Y3, Y4 | crvUSD taken out of YB Curve pools by arbitrage, and where it was routed |
| YB net effect on peg pools | Governance estimate of temporary crvUSD parking of up to half of YB TVL in the worst case | G4 | Net crvUSD into or out of peg pools by YB related routes, per hour |
| Third party claim | "net -4.10M crvUSD sold into peg pools by arbs via YB" (crvtraders) | brief | Reproduce. Report gross and net, and where the number diverges |
| YB lag | price_scale moves in capped steps and follows its target over hours | Y6 | price_scale versus external price during the flush |
| Llamalend versus mint | Same loan logic and soft liquidation, isolated lenders supply the token | C10 | Same metrics for active Llamalend markets, reported separately |

## 4. Gaps and inconsistencies found in the docs

- C2 contradicts itself on which side of the active band holds which token. The study will use the bands_x and bands_y getters, not the prose.
- C5 does not define DebtFraction, rate0 or sigma values, and does not state the price source. These will be read from the contracts.
- The C4 page states that UserState is emitted with zeroed values only when a loan is fully closed during liquidation and that partial liquidations do not emit it. Event coverage will be checked against verified ABIs before any count relies on it.
- Y1 as retrieved describes arbitrageurs bringing crvUSD in both directions. Y2 shows they receive crvUSD when price rises. Y2 is the more detailed source. The raw Y1 text will be re-read before publication.
- No document quantifies how fast PegKeepers can drain in a sustained one sided flow.

## 5. Raw text check, 2026-11-09

Every claim used in sections 2 and 3 was checked against the raw page text. Results:

| Claim | Result |
|---|---|
| Liquidation runs per band, not per user. Not triggered automatically (C3) | Confirmed verbatim |
| Losses "very hard to quantify" (C3) | Confirmed verbatim |
| Hard liquidation only below 0 percent health (C3). Third party liquidation reverts with "Not enough rekt" unless full health is below zero (C4) | Confirmed in source |
| LLAMMA events TokenExchange, Deposit, Withdraw and Controller event Liquidate(liquidator, user, collateral_received, stablecoin_received, debt) (C2, C4) | Confirmed in source |
| Rate formula r = rate0 times exp(power) and the v4 EMA of the debt ratio (C5) | Confirmed |
| TVL_MA_TIME = 50000 s and the 1.5 percent Chainlink bound (C6) | Confirmed in source |
| PegKeeperV2 update() moves one fifth of the imbalance per call, capped by the Regulator allowance, after action_delay (C8) | Confirmed in source. Correction. If the Regulator allows zero, the call reverts with "Regulator ban". It does not return quietly. So blocked calls leave no event |
| Regulator withdraw check (C9) | Confirmed. Addition. withdraw_allowed returns zero whenever the aggregator price is above 1. The aggregator is an EMA, so withdrawals can start late in a fast depeg |
| YB arbitrage directions (Y2) | Confirmed on the live page. "If the DTV is above 50%", buying LP from the LEVAMM with crvUSD is profitable and "removes debt and collateral". Below 50% the trade runs asset to crvUSD and adds debt |
| YB user page (Y1) | An earlier version of the YB user docs described arbitrageurs "bringing crvUSD in" below target, which conflicted with the code path. The live page no longer says this. Y2 is used throughout |
| price_scale "is not an EMA. It follows its target over hours", only the first pool operation in a block can move it (Y6) | Confirmed verbatim |
| LlamaRisk on YB selling crvUSD below peg, reserves moving almost one for one with YB flows, reserve depth binding (G6) | Confirmed verbatim |
| "typical losses are <0.1% per day" in mint markets (R5) | Read on 2026-11-09 on the former resources site. That page has since been removed and the figure is not on the live docs, so it is not used in any chart |
| Number of PegKeepers | Correction. The Regulator lists five PegKeepers (USDC, USDT, pyUSD, frxUSD, GHO), not four. Read on chain from PegKeeperRegulator 0x36a04CAffc681fa179558B2Aaba30395CDdd855f |
