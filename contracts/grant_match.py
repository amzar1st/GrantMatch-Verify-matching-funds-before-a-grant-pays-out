# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *
import hashlib
import json
import re
from datetime import date, datetime, timezone

ID = r"[a-z0-9][a-z0-9-]{0,63}"
MAX_CENTS = 100_000_000_000
MAX_CLAIMS = 20
MAX_BYTES = 32_768
KEYS = {"id", "recipient", "project", "currency", "cents", "settled", "status"}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def parse(text):
    return json.loads(text, object_pairs_hook=unique_keys)


def identifier(value):
    return isinstance(value, str) and re.fullmatch(ID, value) is not None


def cents(value):
    return type(value) is int and 0 < value <= MAX_CENTS


def iso_day(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("Use a YYYY-MM-DD date")
    return date.fromisoformat(value)


def now():
    return int(datetime.fromisoformat(gl.message_raw["datetime"].replace("Z", "+00:00")).timestamp())


def policy_from(text):
    if len(text) > 1800:
        raise ValueError("Policy too long")
    policy = parse(text)
    fields = {"recipient", "project", "minimum_cents", "start", "end", "submit_by",
              "register_url", "register_sha256"}
    if not isinstance(policy, dict) or set(policy) != fields:
        raise ValueError("Unexpected policy fields")
    if not identifier(policy["recipient"]) or not identifier(policy["project"]):
        raise ValueError("Invalid recipient or project ID")
    if not cents(policy["minimum_cents"]):
        raise ValueError("Invalid minimum in cents")
    if not iso_day(policy["start"]) <= iso_day(policy["end"]) <= iso_day(policy["submit_by"]):
        raise ValueError("Invalid date order")
    if not isinstance(policy["register_url"], str) or not re.fullmatch(
        r"https://raw\.githubusercontent\.com/[A-Za-z0-9_-]{1,39}/[A-Za-z0-9_-]{1,100}/"
        r"[0-9a-f]{40}/(?:[A-Za-z0-9_-]{1,50}/){0,4}[A-Za-z0-9_-]{1,50}\.json",
        policy["register_url"],
    ):
        raise ValueError("Use a commit-pinned raw GitHub JSON URL")
    if not isinstance(policy["register_sha256"], str) or not re.fullmatch(
        r"[0-9a-f]{64}", policy["register_sha256"]
    ):
        raise ValueError("Invalid register SHA-256")
    return policy


def claim_from(text):
    if len(text) > 2500:
        raise ValueError("Claim too long")
    entries = parse(text)
    if not isinstance(entries, list) or not 1 <= len(entries) <= MAX_CLAIMS:
        raise ValueError("Submit 1 to 20 funding records")
    ids = set()
    for entry in entries:
        if (not isinstance(entry, dict) or set(entry) != {"id", "cents"}
                or not identifier(entry["id"]) or not cents(entry["cents"])):
            raise ValueError("Use a canonical transfer ID and positive integer cents")
        if entry["id"] in ids:
            raise ValueError("Duplicate transfer ID")
        ids.add(entry["id"])
    return sorted(entries, key=lambda entry: entry["id"])


def verified_register(raw, expected_hash):
    if len(raw) > MAX_BYTES or digest(raw) != expected_hash:
        raise ValueError("Register failed its size or integrity check")
    payload = parse(raw.decode("utf-8"))
    if (not isinstance(payload, dict) or set(payload) != {"schema", "records"}
            or type(payload["schema"]) is not int or payload["schema"] != 1
            or not isinstance(payload["records"], list) or len(payload["records"]) > 100):
        raise ValueError("Invalid register schema")
    records = {}
    for row in payload["records"]:
        if (not isinstance(row, dict) or set(row) != KEYS or not identifier(row["id"])
                or not identifier(row["recipient"]) or not identifier(row["project"])
                or row["id"] in records or not cents(row["cents"])
                or row["status"] not in ("SETTLED", "PENDING", "REVERSED")
                or not isinstance(row["currency"], str)
                or not re.fullmatch(r"[A-Z]{3}", row["currency"])):
            raise ValueError("Invalid or repeated authoritative record")
        iso_day(row["settled"])
        records[row["id"]] = row
    return records


def classify(policy, entry, row):
    if row is None:
        return "RECORD_MISSING"
    if row["recipient"] != policy["recipient"]:
        return "WRONG_RECIPIENT"
    if row["project"] != policy["project"]:
        return "RESTRICTED_TO_OTHER_PROJECT"
    if row["status"] != "SETTLED":
        return "NOT_SETTLED"
    if row["currency"] != "USD" or row["cents"] != entry["cents"]:
        return "AMOUNT_OR_CURRENCY_MISMATCH"
    if not policy["start"] <= row["settled"] <= policy["end"]:
        return "OUTSIDE_FUNDING_WINDOW"
    return "ELIGIBLE"


class GrantMatch(gl.Contract):
    funder: Address
    recipient: str
    policy_json: str
    claim_json: str
    decision_json: str
    decision_sha256: str

    def __init__(self, recipient: str, policy_json: str):
        if not re.fullmatch(r"0x[0-9a-fA-F]{40}", recipient) or int(recipient, 16) == 0:
            raise gl.UserError("Invalid recipient wallet")
        policy = policy_from(policy_json)
        deadline = datetime.combine(iso_day(policy["submit_by"]), datetime.max.time(), timezone.utc)
        if now() > int(deadline.timestamp()):
            raise gl.UserError("Submission deadline already passed")
        self.funder = gl.message.sender_address
        self.recipient = recipient.lower()
        self.policy_json = canonical(policy)
        self.claim_json = ""
        self.decision_json = ""
        self.decision_sha256 = ""

    @gl.public.write
    def submit_claim(self, claim_json: str) -> None:
        if str(gl.message.sender_address).lower() != self.recipient:
            raise gl.UserError("Only the designated recipient may submit")
        if self.claim_json:
            raise gl.UserError("Claim is already locked")
        policy = parse(self.policy_json)
        deadline = datetime.combine(iso_day(policy["submit_by"]), datetime.max.time(), timezone.utc)
        if now() > int(deadline.timestamp()):
            raise gl.UserError("Submission deadline passed")
        self.claim_json = canonical(claim_from(claim_json))

    @gl.public.write
    def review(self) -> None:
        if not self.claim_json or self.decision_json:
            raise gl.UserError("Review requires a locked and undecided claim")
        policy = parse(self.policy_json)
        claim = parse(self.claim_json)

        def independently_review():
            response = gl.nondet.web.get(policy["register_url"])
            if not response.body:
                raise gl.UserError("Authoritative register unavailable")
            records = verified_register(response.body, policy["register_sha256"])
            assessed = []
            total = 0
            for entry in claim:
                row = records.get(entry["id"])
                reason = classify(policy, entry, row)
                assessed.append({**entry, "reason": reason, "record": row})
                if reason == "ELIGIBLE":
                    total += entry["cents"]
            return canonical({
                "status": "THRESHOLD_MET" if total >= policy["minimum_cents"] else "THRESHOLD_NOT_MET",
                "eligible_cents": total,
                "claimed_cents": sum(entry["cents"] for entry in claim),
                "minimum_cents": policy["minimum_cents"],
                "policy_sha256": digest(canonical(policy).encode("utf-8")),
                "claim_sha256": digest(canonical(claim).encode("utf-8")),
                "register_sha256": policy["register_sha256"],
                "entries": assessed,
            })

        decision = gl.eq_principle.strict_eq(independently_review)
        self.decision_json = decision
        self.decision_sha256 = digest(decision.encode("utf-8"))

    @gl.public.view
    def get_grant(self) -> str:
        return canonical({
            "funder": str(self.funder),
            "recipient_wallet": str(self.recipient),
            "policy": parse(self.policy_json),
            "claim": parse(self.claim_json) if self.claim_json else [],
            "decision": parse(self.decision_json) if self.decision_json else None,
            "decision_sha256": self.decision_sha256,
        })
