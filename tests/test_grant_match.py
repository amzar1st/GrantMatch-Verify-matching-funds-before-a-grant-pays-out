"""Contract behavior tests with a minimal GenVM boundary double."""
import json
import sys
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
RECIPIENT = "0x" + "a" * 40
FUNDER = "0x" + "b" * 40
REGISTER = (ROOT / "evidence/demo-register.json").read_bytes()


class UserError(Exception):
    pass


genlayer = ModuleType("genlayer")
genlayer.Address = str
genlayer.gl = SimpleNamespace(
    Contract=object,
    UserError=UserError,
    public=SimpleNamespace(write=lambda fn: fn, view=lambda fn: fn),
    message=SimpleNamespace(sender_address=FUNDER),
    message_raw={"datetime": "2026-11-10T12:00:00Z"},
    nondet=SimpleNamespace(web=SimpleNamespace()),
    eq_principle=SimpleNamespace(strict_eq=lambda fn: fn()),
)
sys.modules["genlayer"] = genlayer
from contracts import grant_match as gm


class GrantMatchTests(unittest.TestCase):
    def setUp(self):
        self.policy = {
            "recipient": "harbor-garden", "project": "harbor-garden", "minimum_cents": 1_000_000,
            "start": "2025-01-01", "end": "2025-12-31", "submit_by": "2027-12-31",
            "register_url": "https://raw.githubusercontent.com/a/b/" + "a" * 40 + "/register.json",
            "register_sha256": gm.digest(REGISTER),
        }
        self.entries = [{"id": "bank-demo-002", "cents": 400_000}, {"id": "bank-demo-001", "cents": 800_000}]
        gm.gl.message.sender_address = FUNDER
        gm.gl.message_raw["datetime"] = "2026-11-10T12:00:00Z"
        gm.gl.nondet.web.get = lambda url: SimpleNamespace(status_code=200, body=REGISTER)
        self.contract = gm.GrantMatch(RECIPIENT, json.dumps(self.policy))

    def submit(self):
        gm.gl.message.sender_address = RECIPIENT
        self.contract.submit_claim(json.dumps(self.entries))

    def test_demo_lifecycle(self):
        self.submit()
        self.contract.review()
        result = json.loads(self.contract.get_grant())
        self.assertEqual(result["decision"]["claimed_cents"], 1_200_000)
        self.assertEqual(result["decision"]["eligible_cents"], 800_000)
        self.assertEqual(result["decision"]["status"], "THRESHOLD_NOT_MET")
        self.assertEqual(result["decision"]["entries"][1]["reason"], "RESTRICTED_TO_OTHER_PROJECT")
        self.assertEqual(result["decision_sha256"], gm.digest(self.contract.decision_json.encode()))
        with self.assertRaises(UserError):
            self.contract.review()

    def test_threshold_equality(self):
        self.policy["minimum_cents"] = 800_000
        self.contract = gm.GrantMatch(RECIPIENT, json.dumps(self.policy))
        self.submit()
        self.contract.review()
        self.assertEqual(json.loads(self.contract.decision_json)["status"], "THRESHOLD_MET")

    def test_unauthorized_and_late_submissions(self):
        with self.assertRaises(UserError):
            self.contract.submit_claim(json.dumps(self.entries))
        gm.gl.message_raw["datetime"] = "2028-01-01T00:00:00Z"
        with self.assertRaises(UserError):
            self.submit()

    def test_wrong_amount_and_missing_record(self):
        self.entries = [{"id":"bank-demo-001","cents":800_001}, {"id":"missing","cents":200}]
        self.submit()
        self.contract.review()
        result = json.loads(self.contract.decision_json)
        self.assertEqual(result["eligible_cents"], 0)
        self.assertEqual([item["reason"] for item in result["entries"]],
                         ["AMOUNT_OR_CURRENCY_MISMATCH", "RECORD_MISSING"])

    def test_pending_or_wrong_recipient_or_outside_window(self):
        row = gm.parse(REGISTER)["records"][0]
        entry = self.entries[1]
        for change, reason in [
            ({"status": "REVERSED"}, "NOT_SETTLED"),
            ({"recipient": "other"}, "WRONG_RECIPIENT"),
            ({"settled": "2024-12-31"}, "OUTSIDE_FUNDING_WINDOW"),
            ({"currency": "EUR"}, "AMOUNT_OR_CURRENCY_MISMATCH"),
        ]:
            with self.subTest(reason=reason):
                self.assertEqual(gm.classify(self.policy, entry, row | change), reason)

    def test_unavailable_or_tampered_evidence_leaves_claim_retryable(self):
        self.submit()
        for status, body, error in [(503, b"", UserError), (200, REGISTER + b" ", ValueError)]:
            gm.gl.nondet.web.get = lambda url: SimpleNamespace(status_code=status, body=body)
            with self.assertRaises(error):
                self.contract.review()
            self.assertEqual(self.contract.decision_json, "")
        gm.gl.nondet.web.get = lambda url: SimpleNamespace(status_code=200, body=REGISTER)
        self.contract.review()
        self.assertTrue(self.contract.decision_json)

    def test_duplicate_ids_fields_and_claim_replay(self):
        with self.assertRaises(ValueError):
            gm.claim_from(json.dumps([self.entries[0]] * 2))
        with self.assertRaises(ValueError):
            gm.claim_from('[{"id":"a","id":"b","cents":100}]')
        row = gm.parse(REGISTER)["records"][0]
        raw = gm.canonical({"schema": 1, "records": [row, row]}).encode()
        with self.assertRaises(ValueError):
            gm.verified_register(raw, gm.digest(raw))
        self.submit()
        with self.assertRaises(UserError):
            self.submit()

    def test_unpinned_host_and_malformed_amounts(self):
        for url in ("https://localhost/register.json", self.policy["register_url"].replace("a"*40, "main")):
            with self.assertRaises(ValueError):
                gm.policy_from(json.dumps(self.policy | {"register_url": url}))
        for amount in (True, 0, -1, 1.25, gm.MAX_CENTS + 1):
            with self.assertRaises(ValueError):
                gm.claim_from(json.dumps([{"id": "x", "cents": amount}]))

    def test_review_requires_claim_and_valid_recipient(self):
        with self.assertRaises(UserError):
            self.contract.review()
        for invalid in (RECIPIENT[:20], "0x" + "0" * 40):
            with self.assertRaises(UserError):
                gm.GrantMatch(invalid, json.dumps(self.policy))


if __name__ == "__main__":
    unittest.main()
