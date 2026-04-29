import datetime as dt
import unittest
from pathlib import Path
import importlib.util

spec = importlib.util.spec_from_file_location("mod", Path(__file__).resolve().parents[1] / "scripts" / "github_daily_recommender.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class TestScoring(unittest.TestCase):
    def setUp(self):
        now = dt.datetime.utcnow()
        self.repo = {
            "name": "good-tool",
            "full_name": "a/good-tool",
            "description": "A productivity tool",
            "stargazers_count": 1000,
            "forks_count": 100,
            "open_issues_count": 5,
            "created_at": (now - dt.timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "updated_at": (now - dt.timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "pushed_at": (now - dt.timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "topics": ["productivity", "automation"],
            "license": {"spdx_id": "MIT"},
        }

    def test_stars_per_day(self):
        self.assertGreater(mod.compute_stars_per_day(self.repo), 50)

    def test_recency_score(self):
        self.assertGreater(mod.compute_recency_score(self.repo), 0.8)

    def test_topic_match_score(self):
        cfg = {"topics": ["productivity"], "keywords": ["tool"]}
        self.assertGreater(mod.compute_topic_match_score(self.repo, cfg, "usage demo"), 0.5)

    def test_usability_score(self):
        analysis = {"signals": {"has_install": True, "has_usage": True, "has_screenshot": True}}
        self.assertGreaterEqual(mod.compute_usability_score(self.repo, analysis), 0.8)

    def test_score_repository(self):
        score, _, _ = mod.score_repository(self.repo, "install usage feature screenshot", {"topics": ["productivity"], "keywords": []}, {"weights": {}, "penalties": {}}, {"blocked_keywords": [], "risky_install_patterns": []})
        self.assertGreater(score, 0.4)


if __name__ == "__main__":
    unittest.main()
