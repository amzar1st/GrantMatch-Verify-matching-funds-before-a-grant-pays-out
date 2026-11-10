# Live verification

Verified November 10, 2026 on hosted StudioNet (chain ID **61999**) in **Normal (Full Consensus)** mode. GenLayer Studio's built-in test account signed the deployment and writes.

| Evidence | Link |
| --- | --- |
| Public dashboard | [GrantMatch](https://grantmatch.tinymule33.chatgpt.site/) |
| Default contract | [0x63Befb14BFf4dD7eab772781911eDab9e13Ed45C](https://explorer-studio.genlayer.com/address/0x63Befb14BFf4dD7eab772781911eDab9e13Ed45C) |
| Deployment, finalized success | [0x790a…d1bf](https://explorer-studio.genlayer.com/tx/0x790a035b23bc9f08e5767a49389603276ca79e7a0da8189bbe6f454e5875d1bf) |
| Claim, finalized success | [0x3d02…f6f8](https://explorer-studio.genlayer.com/tx/0x3d021ae089372e2fd0f22bae68030958c9f2b6f86a0c7a2a611a68267112f6f8) |
| Evidence review, finalized success | [0x6abe…0222](https://explorer-studio.genlayer.com/tx/0x6abe5e4e761cdd90ab0f0e9a3eb715bd758bfbde657278ef6712f49416da0222) |
| Duplicate transfer, finalized execution error on an earlier build | [0x81d7…c466](https://explorer-studio.genlayer.com/tx/0x81d7a79749bd5e6a162084ff4f3d58fd8da17bcaf2f8729f580217bd969fc466) |
| Fictional public evidence | [Commit-pinned register](https://raw.githubusercontent.com/amzar1st/GrantMatch-Verify-matching-funds-before-a-grant-pays-out/59786f1896ee2af5ed6906cbcc5cebabb95e90b9/evidence/demo-register.json) |

The finalized claim totaled **$12,000**. The review excluded **$4,000** under `RESTRICTED_TO_OTHER_PROJECT` and returned **$8,000** eligible against **$10,000** required. The finalized result was `THRESHOLD_NOT_MET`.

- Decision SHA-256 is `f5870d520119116c17e1596606797b343bebb4ea62f4a224fbbb247bb0738293`.
- Contract source SHA-256 is `e624a9833d6f1f2cb5a2d6420acba93428840a79da5dbb4597fc90a4cac637cd`. This matches the decoded deployment payload and [the contract file](../contracts/grant_match.py).
- The tracker was exercised against a transaction accepted and awaiting finalization, a finalized success, and a finalized execution error.
- The earlier build used an incompatible HTTP status accessor. The final contract validates the response bytes and SHA-256 digest. Duplicate-rejection logic is unchanged and covered by tests on the final source.

## Reproduce with a new Studio instance

1. Open [GenLayer Studio](https://studio.genlayer.com/run-debug) and upload `contracts/grant_match.py`. Keep Normal (Full Consensus) selected.
2. Deploy with the built-in Studio account. Use its full address as the `recipient` string. Use the following `policy_json` string, adjusting the submission deadline if it has passed.

```json
{"recipient":"harbor-garden","project":"harbor-garden","minimum_cents":1000000,"start":"2025-01-01","end":"2025-12-31","submit_by":"2027-12-31","register_url":"https://raw.githubusercontent.com/amzar1st/GrantMatch-Verify-matching-funds-before-a-grant-pays-out/59786f1896ee2af5ed6906cbcc5cebabb95e90b9/evidence/demo-register.json","register_sha256":"01bae68339849ba6ba2fc6bb25497c37d881b950890d640b8e256b872f9ca83a"}
```

3. Call `submit_claim` with `[{"id":"bank-demo-001","cents":800000},{"id":"bank-demo-002","cents":400000}]`. Wait for a finalized successful receipt.
4. Call `review` and wait for a finalized successful receipt. Select Finalized under Read Methods and call `get_grant`.
5. Enter your new address in the dashboard. Paste each write hash into the tracker to check the consensus status and execution result. The demo above is already finalized and can be viewed without a wallet.

## Release checks

- Nine Python behavior tests, Python compilation, and JavaScript syntax checks passed.
- GenVM Linter 0.11.0 passed AST lint and SDK validation against the pinned runner. The extracted interface contains two write methods and one view method.
- The public dashboard returned HTTP 200 without an authenticated session. A browser run confirmed the default contract read and finalized review, and preview testing confirmed the invalid-address and failed-receipt states.
- The [source-matched release commit](https://github.com/amzar1st/GrantMatch-Verify-matching-funds-before-a-grant-pays-out/commit/2d21b8a86c0b635c7932c5fa938373ec73c7f86b) contains the deployed contract and dashboard source.
