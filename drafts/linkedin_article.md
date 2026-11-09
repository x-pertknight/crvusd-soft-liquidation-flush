# crvUSD in the 8 November flush. Empty PegKeepers and BTC selling routed through Yield Basis

When ETH fell 6% in fifteen minutes on the night of 8 November, transactions that passed through Yield Basis pools sold a net 3.85M crvUSD into the crvUSD peg pools. The PegKeepers, the contracts built to absorb that kind of flow, held no crvUSD in those pools to withdraw.

I rebuilt the event block by block from Ethereum logs and archive state. Before touching the data, I read the Curve and Yield Basis docs and governance threads, and I logged 39 predictions with a timestamp. Everything below recomputes from raw files in a public repo with one command.

## How the peg is supposed to hold

crvUSD is minted against collateral in Curve's mint markets. Two mechanisms defend its peg.

The first is the PegKeepers. Each one is paired with a stablecoin pool (USDC, USDT, pyUSD, frxUSD, GHO). When crvUSD trades above 1 dollar, a PegKeeper mints crvUSD and deposits it into its pool. When crvUSD trades below 1, it can withdraw what it deposited earlier. A PegKeeper can only pull out crvUSD it put in. If it holds nothing, it can do nothing.

The second is the borrow rate. It rises when crvUSD trades below 1, which pushes borrowers to buy crvUSD back and repay.

Then there is LLAMMA, Curve's soft liquidation AMM. When collateral falls into a borrower's price range, arbitrageurs buy that collateral from LLAMMA and pay in crvUSD. So in a drop, LLAMMA creates demand for crvUSD. Hard liquidators also need crvUSD.

Yield Basis adds a different flow. It holds 2x leveraged Curve LP positions in BTC and ETH pools paired with crvUSD, funded by a crvUSD credit line from Curve. Those pools are also ordinary trading venues. When BTC is sold through them, crvUSD comes out and has to go somewhere, usually into crvUSD/USDC or crvUSD/USDT. LlamaRisk's H2 2025 report noted that Yield Basis flows sometimes sell crvUSD below peg and that PegKeeper reserve depth had become a binding constraint.

## What happened

[Chart C1: crvUSD price per PegKeeper pool, with ETH below]

crvUSD was already below peg before anything happened. At 20:00 UTC the TVL-weighted price across the five PegKeeper pools was 0.9979.

ETH dropped from 2,224 to 2,089 USD between 21:41 and 21:56 UTC. BTC fell 2.4% between 21:45 and 22:00. The weighted crvUSD price fell to 0.9942 within a minute of the ETH low. One pool, pyUSD, printed 0.9893 for a single block.

The price did not come back. It stayed below 0.997 for 6.1 of the 8 hours I measured and was still at 0.9967 at 04:00 UTC, six hours after the low. The crvUSD price aggregator, the smoothed price the protocol itself uses, bottomed at 0.9951 in my samples. That matches the figure that circulated after the event.

[Chart C2: PegKeeper debt over 30 days]

All five PegKeepers held zero debt at 20:00 UTC. There was no Provide or Withdraw event in the whole window. Over the previous 30 days only the USDT PegKeeper had held debt, up to 33.75M crvUSD, and it reached zero by 30 October. I did not study why. Zero debt fits the price record. The crvUSD aggregator price was below 1 in 119 of 121 six-hourly samples over those 30 days, and in all 40 samples since 30 October. PegKeepers only deposit when crvUSD is above 1. The borrow rate did move, from 6.3% to 7.7% in the WETH market.

[Chart C3: net crvUSD flow by actor class]

I sorted every crvUSD transfer in and out of the five peg pools by transaction. Each transaction got one class, using rules I fixed before looking at the data. A transaction that swaps through a Yield Basis pool counts as Yield Basis. One with a LLAMMA trade counts as soft liquidation arbitrage, and so on.

The result is lopsided.
- Transactions through Yield Basis pools sold a net 3.85M crvUSD into the peg pools. Between 21:45 and 22:00 alone the figure was 4.26M, partly offset later.
- The typical one sold BTC into a Yield Basis pool, took crvUSD out and sold it for USDC or USDT in the same transaction. The logs cannot say whether that was arbitrage or an ordinary sale routed through the cheapest path.
- The BTC pools carried it, 3.64M of the 3.85M. Transactions touching the WETH pools contributed about 0.21M, even though ETH fell more.
- 88 senders were involved. The largest accounted for 14% of the selling. The five largest transactions accounted for 40%, all within a few minutes.
- Other traders bought 2.19M back. LLAMMA arbitrage, liquidators and borrowers were small net buyers, as the docs predict.

The second largest bar on the chart is not a sale. Liquidity providers deposited a net 2.05M crvUSD into the peg pools. Most of it came in one deposit into the pyUSD pool at 23:38 UTC, 1.91M crvUSD together with 0.24M pyUSD, close to the pool's existing mix of about 88% crvUSD. Because the mix barely changed, the pyUSD pool price moved only from 0.9956 to 0.9953, and the weighted price moved less than 0.2 basis points in that block.

## The 4.10M claim

[Chart C4: reconciliation]

After the event a figure circulated, "net -4.10M crvUSD sold into peg pools by arbs via YB". I could not find its primary source, so I do not know its window or definition. My main measure gives 3.85M, 6% below. That meets the rule I set before seeing the data.

It does not prove much. The 15 minutes of the drop alone give 4.26M. Gross sells give 4.59M. USDC and USDT pools only give 2.94M. The direction is robust. The exact size depends on the definition, and I cannot tell which one the claim used.

## Soft liquidation was barely tested

[Chart C5: soft liquidation by market]

This is where I expected the story to be, and it was not. Only about 50k USD of collateral was converted in the mint markets, over 43 trades between 22:02 and 23:05. The measured result was a small loss in WETH and a small gain in WBTC, both against an oracle that was still catching up with the drop. I would not read a percentage into it. There were three hard liquidations, one with 10.8k crvUSD of debt and two dust positions. A 6% ETH move did not push many crvUSD loans into their bands. This event says little about how good LLAMMA is.

## What I got wrong

I logged 39 predictions before fetching data. 14 hit (10 if I drop the weak tests), 12 missed, and 13 could not be tested in this release.

- I expected the PegKeepers to withdraw 2M to 20M. They had nothing to withdraw.
- I expected the 4.10M claim to fall apart once both Yield Basis legs were netted. My main measure came within 6%.
- I fixed the flush hour at 22:30 to 23:30 UTC from the "around 23:00" in my notes. That was probably local time. The drop came an hour earlier. I kept the hour as registered and scored against it.

[Chart C6: predictions scorecard]

## Limitations

- This is one event. It ranks nothing. A comparison with Aave, Fluid, Liquity v2 and Morpho needs a model, not just a measurement, and is the next phase.
- A swap through a Yield Basis pool may be arbitrage or an ordinary routed sale. The logs do not separate the two.
- Attribution is per transaction. Arbitrage split across transactions is counted as "other" in the main measure.
- Stablecoins are valued at 1 dollar. ETH and BTC prices come from Chainlink, which updates in steps.
- The source of the 4.10M figure and of the 0.9951 print is unverified.

## What it means

The question for crvUSD is not only how soft liquidation behaves. It is what happens when the PegKeepers hold nothing and large BTC flows pass through pools that pay out crvUSD. On 8 November those flows reached the peg pools in the same minutes that the weighted price fell from 0.9979 to 0.9942. One event cannot separate their effect from everything else that moved that night. Six hours later the price had still not returned to where it started. The borrow rate rose. The PegKeepers had nothing to give.

Repo with data, code and every chart
https://github.com/x-pertknight/crvusd-soft-liquidation-flush
