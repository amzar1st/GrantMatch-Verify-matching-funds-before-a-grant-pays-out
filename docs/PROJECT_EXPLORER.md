# GrantMatch Project Explorer draft

| Field | Value |
| --- | --- |
| Project name | GrantMatch |
| Suggested primary tag | Oracles / Real-World Data, depending on the available menu |
| Suggested topics | Grants, evidence verification |
| One-liner | GrantMatch verifies whether a grant recipient secured the matching funds required for a payout. |
| Category | Builder → Projects |

## Overview

GrantMatch helps grant programs verify that a recipient secured the matching funds required for payout. A funder locks the recipient, threshold, dates, and a commit-pinned public funding register on GenLayer. The recipient submits transfer references and amounts. Validators independently retrieve the register, verify its SHA-256 digest, and check each contribution for settlement, matching project, recipient, amount, and date. Duplicate transfer IDs are rejected. The dashboard shows finalized totals, exclusion reasons, evidence hashes, and transaction status. In the fictional StudioNet demo, a $12,000 claim includes a $4,000 transfer restricted to another project, leaving $8,000 eligible against a $10,000 threshold. GrantMatch records payout eligibility for the funder to act on.

## Links

Use the public dashboard, source repository, StudioNet explorer contract and review transaction, and live verification guide.

- [Public dashboard](https://grantmatch.tinymule33.chatgpt.site/)
- [GitHub repository](https://github.com/amzar1st/GrantMatch-Verify-matching-funds-before-a-grant-pays-out)
- [StudioNet contract](https://explorer-studio.genlayer.com/address/0x63Befb14BFf4dD7eab772781911eDab9e13Ed45C)
- [Finalized validator review](https://explorer-studio.genlayer.com/tx/0x6abe5e4e761cdd90ab0f0e9a3eb715bd758bfbde657278ef6712f49416da0222)
- [Live verification](LIVE_VERIFICATION.md)
