# GrantMatch

GrantMatch verifies whether a grant recipient secured the matching funds required for payout. It makes each included and excluded contribution traceable to a public funding register.

## Workflow

1. The funder deploys one contract per grant, designating the recipient wallet and locking the USD threshold, funding window, UTC submission deadline, and a commit-pinned evidence register with its SHA-256 digest.
2. The recipient signs a single claim in GenLayer Studio using its built-in account. Each claim row identifies a canonical transfer and the amount in integer USD cents.
3. Anyone can request review. The leader and validators independently retrieve and hash the public register, validate its schema, and apply the same eligibility rules. GenLayer strict equivalence compares the full canonical decision. The contract records the eligible total, the outcome, and verification hashes.
4. The public dashboard reads finalized state and tracks Studio write hashes through consensus. A grant administrator can use the finalized result as a payout input.

## Demo

[Open the public dashboard](https://grantmatch.tinymule33.chatgpt.site/).

A fictional Harbor Garden grant requires $10,000. The recipient claimed $12,000. One $4,000 transfer was restricted to another project, leaving $8,000 eligible.

- [Reproduce the deployment and transactions](docs/LIVE_VERIFICATION.md)
- [Trust boundaries and limits](docs/SECURITY.md)
- [Project Explorer submission copy](docs/PROJECT_EXPLORER.md)

## Run locally

```sh
python -m unittest discover -s tests -v
python -m py_compile contracts/grant_match.py
node --check dist/app.mjs
python -m http.server 8080 --directory dist
```

Open `http://localhost:8080`. The browser loads the pinned GenLayerJS version and reads the default StudioNet contract. The dashboard needs internet access to StudioNet and the SDK CDN. A wallet is required only for writes in Studio. The Python test suite uses a GenVM boundary double. The hosted Studio transactions exercise the actual SDK, GenVM, and network.

## Contract API

| Method | Role | Purpose |
| --- | --- | --- |
| Constructor | Funder | Lock a recipient address and JSON policy |
| `submit_claim(claim_json)` | Designated recipient | Lock the claim by the UTC deadline |
| `review()` | Anyone | Fetch the register and reach consensus on eligibility |
| `get_grant()` | Anyone | Read policy, claim, verdict, and decision digest |
