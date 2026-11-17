# Release 2, addendum 3 (2026-11-17)

Wording and definition fixes after a second outside review. No new data. PREREG_R2_ADDENDUM2.md is not edited (hash unchanged).

1. **Window definition.** Addendum 2 defined a window as a run of blocks whose simulated `update()` returns more than 0. Every withdrawal sets off the 12-second action delay, so the next block returns 0 and splits one opening into short runs. An opening is now a run of consecutive blocks whose simulated call does not revert "peg unprofitable" (it returns more than 0, or returns 0). A run that touches the first or last block read is censored: its true length is longer. The median and the "one-block opening" arithmetic are dropped. The finding is stated as: how many of the ten openings reach the edge of the 31-block read, and how many close inside it.
2. **Threshold figures** (53.4%, 0.99993) are regenerated from `threshold_evidence` after the label fix; the older 53.1% and 0.99994 came from calls that returned 0.
3. **Simulation coverage** is stated with counts. Of 1,347 snapshots, 671 were simulated: all 641 on the withdrawal side and 30 of the 706 on the deposit-branch side by the balance test (704 labelled deposit-branch, 2 labelled "debt fell"). The other 676 were not simulated. For them the outcome follows from the Regulator code: price below 1, so the deposit allowance is 0 and the call reverts "Regulator ban".
4. **`worst_price_threshold`** is stated as the deployed source has it: the Regulator returns 0 for a deposit if the largest price_oracle among the other pools is below this pool's price_oracle minus the threshold, that is, if this pool prices its coin more than 0.0003 above every other pool.
5. The price read "at the event block" is the state at the end of that block, after the event ran.
