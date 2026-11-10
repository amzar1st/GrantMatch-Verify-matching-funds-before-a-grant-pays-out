import { network } from "./network.mjs";

const byId = (id) => document.getElementById(id);
const addressInput = byId("address");
const hashInput = byId("hash");
const dollars = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 });
const currency = (cents) => cents == null ? "—" : dollars.format(cents / 100);
const reasons = {
  ELIGIBLE: "Eligible",
  RESTRICTED_TO_OTHER_PROJECT: "Restricted to another project",
  RECORD_MISSING: "Missing from the register",
  WRONG_RECIPIENT: "Wrong recipient",
  NOT_SETTLED: "Transfer has not settled",
  AMOUNT_OR_CURRENCY_MISMATCH: "Amount or currency mismatch",
  OUTSIDE_FUNDING_WINDOW: "Outside funding window",
};
const terminalFailures = new Set(["CANCELED", "CANCELLED", "UNDETERMINED", "REJECTED"]);
let sdkPromise;
let readGeneration = 0;
let trackingGeneration = 0;

function studioClient() {
  sdkPromise ??= Promise.all([
    import("https://esm.sh/genlayer-js@1.1.8?bundle"),
    import("https://esm.sh/genlayer-js@1.1.8/chains?bundle"),
    import("https://esm.sh/genlayer-js@1.1.8/types?bundle"),
  ]).then(([sdk, { studionet }, types]) => ({
    client: sdk.createClient({ chain: studionet }),
    types,
    isSuccessful: sdk.isSuccessful,
  })).catch((error) => {
    sdkPromise = undefined;
    throw error;
  });
  return sdkPromise;
}

function addDetail(key, value) {
  const dt = document.createElement("dt");
  const dd = document.createElement("dd");
  dt.textContent = key;
  dd.textContent = value;
  byId("policy").append(dt, dd);
}

function render(address, state) {
  const { policy, claim, decision } = state;
  const verdict = byId("verdict");
  verdict.textContent = decision
    ? (decision.status === "THRESHOLD_MET" ? "Threshold met" : "Threshold not met")
    : (claim.length ? "Claim locked" : "Awaiting claim");
  verdict.dataset.tone = decision ? (decision.status === "THRESHOLD_MET" ? "pass" : "fail") : "";
  byId("claimed").textContent = currency(decision?.claimed_cents ?? (claim.length ? claim.reduce((total, row) => total + row.cents, 0) : null));
  byId("eligible").textContent = currency(decision?.eligible_cents);
  byId("threshold").textContent = currency(policy.minimum_cents);
  const records = byId("records");
  records.replaceChildren();
  for (const entry of decision?.entries ?? claim) {
    const row = records.insertRow();
    for (const value of [entry.id, currency(entry.cents), reasons[entry.reason] ?? "Awaiting review", entry.record?.project ?? "—"]) {
      row.insertCell().textContent = value;
    }
  }
  if (!records.rows.length) {
    const cell = records.insertRow().insertCell();
    cell.colSpan = 4;
    cell.textContent = "No contribution records have been submitted.";
  }
  byId("policy").replaceChildren();
  addDetail("Recipient wallet", state.recipient_wallet);
  addDetail("Funder wallet", state.funder);
  addDetail("Project", policy.project);
  addDetail("Funding window", `${policy.start} through ${policy.end}`);
  addDetail("Submit by (UTC)", policy.submit_by);
  addDetail("Register SHA-256", policy.register_sha256);
  if (decision) {
    addDetail("Policy SHA-256", decision.policy_sha256);
    addDetail("Claim SHA-256", decision.claim_sha256);
    addDetail("Decision SHA-256", state.decision_sha256);
  }
  byId("explorer").href = `${network.explorer}/address/${address}`;
  const register = byId("register");
  register.hidden = !/^https:\/\/raw\.githubusercontent\.com\//.test(policy.register_url);
  if (!register.hidden) register.href = policy.register_url;
  byId("results").hidden = false;
}

async function readGrant() {
  if (!addressInput.reportValidity()) return;
  const generation = ++readGeneration;
  const address = addressInput.value;
  const verdict = byId("verdict");
  byId("results").hidden = true;
  verdict.textContent = "Connecting";
  verdict.dataset.tone = "";
  byId("read-status").textContent = "Reading finalized state from StudioNet…";
  try {
    const { client, types } = await studioClient();
    const response = await client.readContract({
      address, functionName: "get_grant", args: [],
      transactionHashVariant: types.TransactionHashVariant.LATEST_FINAL,
    });
    if (generation !== readGeneration) return;
    render(address, JSON.parse(response));
    byId("read-status").textContent = address.toLowerCase() === network.address.toLowerCase()
      ? "Live StudioNet read · Fictional Harbor Garden demonstration"
      : "Live StudioNet read · User-supplied contract address";
  } catch (error) {
    if (generation !== readGeneration) return;
    byId("results").hidden = true;
    verdict.textContent = "Read unavailable";
    byId("read-status").textContent = `Could not read finalized state. ${error.shortMessage ?? error.message}`;
  }
}

function enumName(value, enumeration) {
  return String(typeof value === "number" ? (enumeration?.[value] ?? value) : (value ?? "Unknown")).toUpperCase();
}

async function trackTransaction() {
  if (!hashInput.reportValidity()) return;
  const generation = ++trackingGeneration;
  const hash = hashInput.value;
  const status = byId("tx-status");
  const explorer = byId("tx-explorer");
  explorer.href = `${network.explorer}/tx/${hash}`;
  explorer.hidden = false;
  status.textContent = "Looking up transaction…";
  try {
    const { client, types, isSuccessful } = await studioClient();
    for (let attempt = 0; attempt < 36 && generation === trackingGeneration; attempt++) {
      const transaction = await client.getTransaction({ hash });
      if (generation !== trackingGeneration) return;
      if (transaction) {
        const stage = enumName(transaction.statusName ?? transaction.status, types.TransactionStatus);
        const leaderOutcome = transaction.consensus_data?.leader_receipt?.[0]?.execution_result;
        const outcome = enumName(
          transaction.txExecutionResultName ?? transaction.executionResultName ?? transaction.execution_result
            ?? transaction.executionResult ?? leaderOutcome,
          types.ExecutionResult,
        );
        if (stage === "FINALIZED") {
          const success = ["SUCCESS", "FINISHED_WITH_RETURN"].includes(outcome) || (typeof isSuccessful === "function"
            ? isSuccessful(transaction)
            : false);
          status.textContent = success ? "Finalized · Execution succeeded"
            : outcome === "UNKNOWN" ? "Finalized · Execution outcome unavailable"
              : `Finalized · Execution result: ${outcome}`;
          return;
        }
        if (terminalFailures.has(stage)) {
          status.textContent = `${stage} · No successful finalized result`;
          return;
        }
        status.textContent = stage === "ACCEPTED"
          ? "Accepted by consensus · Awaiting finalization"
          : `${stage} · Awaiting finalization`;
      } else {
        status.textContent = "Waiting for the transaction to appear on StudioNet…";
      }
      await new Promise((resolve) => setTimeout(resolve, 2500));
    }
    if (generation === trackingGeneration) status.textContent = "Tracking paused. Check the explorer or track the same hash again.";
  } catch (error) {
    if (generation === trackingGeneration) status.textContent = `Transaction lookup failed. ${error.shortMessage ?? error.message}`;
  }
}

addressInput.value = new URL(location.href).searchParams.get("contract") ?? network.address;
byId("lookup").addEventListener("submit", (event) => { event.preventDefault(); readGrant(); });
byId("track").addEventListener("submit", (event) => { event.preventDefault(); trackTransaction(); });
for (const [label, hash] of Object.entries(network.demo)) {
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = label;
  button.addEventListener("click", () => { hashInput.value = hash; trackTransaction(); });
  byId("demo-tx").append(button);
}
readGrant();
