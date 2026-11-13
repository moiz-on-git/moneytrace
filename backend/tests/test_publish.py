from __future__ import annotations

import json
import shutil
import unittest
from pathlib import Path
from unittest.mock import patch

from moneytrace.llm import fallback_brief
from moneytrace.publish import build_api, publish
from tests.test_pipeline import build_fixture_snapshot


class ApiShapeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshot = build_fixture_snapshot()
        cls.api = build_api(cls.snapshot, fallback_brief(cls.snapshot), {"model": "test/model", "usage": {"cost": 0.0012}})

    def test_schema_and_session(self):
        self.assertEqual(self.api["schema"], 1)
        self.assertTrue(self.api["session"]["date"])
        self.assertIn("disclaimer", self.api)

    def test_sections_present(self):
        for key in ("tape", "flows", "sectors", "drivers", "stacks", "macro", "crypto", "brief", "meta"):
            self.assertIn(key, self.api)
        self.assertGreaterEqual(len(self.api["tape"]), 1)
        self.assertGreaterEqual(len(self.api["sectors"]), 1)
        self.assertGreaterEqual(len(self.api["flows"]["in"]), 1)

    def test_json_safe(self):
        text = json.dumps(self.api)
        self.assertNotIn("NaN", text)
        self.assertNotIn("Infinity", text)

    def test_rates_use_basis_points(self):
        rates = [m for m in self.api["macro"] if m["kind"] == "rate"]
        self.assertTrue(rates, "fixture should include a rate instrument")
        self.assertIsNone(rates[0]["chg"])
        self.assertIsNotNone(rates[0]["level"])

    def test_flow_shape_is_stable(self):
        flow = self.api["flows"]["in"][0]
        self.assertEqual(set(flow), {"symbol", "name", "group", "chg", "flow", "rvol", "chg5"})

    def test_share_is_bounded(self):
        for driver in self.api["drivers"]:
            self.assertGreaterEqual(driver["share"], 0)
            self.assertLessEqual(driver["share"], 100)


class PublishTests(unittest.TestCase):
    def test_writes_files_and_sorts_index(self):
        snapshot = build_fixture_snapshot()
        brief = fallback_brief(snapshot)
        tmp = Path(__file__).resolve().parent.parent / "data" / "_unittest_api"
        sessions_dir = tmp / "sessions"
        shutil.rmtree(tmp, ignore_errors=True)
        sessions_dir.mkdir(parents=True)

        try:
            with patch("moneytrace.publish.API_DIR", tmp), patch("moneytrace.publish.API_SESSIONS_DIR", sessions_dir):
                paths = publish(snapshot, brief, {"model": "m"})
                self.assertEqual(len(paths), 3)
                payload = json.loads((tmp / "latest.json").read_text(encoding="utf-8"))
                date = payload["session"]["date"]
                self.assertTrue((sessions_dir / f"{date}.json").exists())

                older = json.loads(json.dumps(snapshot))
                older["session"]["session_date"] = "2020-01-02"
                publish(older, brief, {"model": "m"})

                index = json.loads((tmp / "index.json").read_text(encoding="utf-8"))
                self.assertGreaterEqual(len(index["sessions"]), 2)
                dates = [s["date"] for s in index["sessions"]]
                self.assertEqual(dates, sorted(dates, reverse=True))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
