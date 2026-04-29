import datetime as dt
import types
import unittest
from pathlib import Path
import importlib.util

spec = importlib.util.spec_from_file_location("mod", Path(__file__).resolve().parents[1] / "scripts" / "github_daily_recommender.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class TestFiltering(unittest.TestCase):
    def setUp(self):
        now = dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        self.repo = {"name":"x","description":"safe","stargazers_count":100,"created_at":now,"updated_at":now,"pushed_at":now,"archived":False,"fork":False}
        self.args = types.SimpleNamespace(include_archived=False, include_forks=False, min_stars=50, topic="all")
        self.blocklist = {"blocked_keywords":["malware"],"risky_install_patterns":["curl | bash"]}

    def test_archived_filtered(self):
        r=dict(self.repo);r["archived"]=True
        ok,_=mod.filter_repository(r,"",self.args,self.blocklist)
        self.assertFalse(ok)

    def test_fork_filtered(self):
        r=dict(self.repo);r["fork"]=True
        ok,_=mod.filter_repository(r,"",self.args,self.blocklist)
        self.assertFalse(ok)

    def test_high_risk_keyword(self):
        ok,_=mod.filter_repository(self.repo,"contains malware",self.args,self.blocklist)
        self.assertFalse(ok)

    def test_missing_readme_penalty(self):
        score,_,_=mod.score_repository(self.repo,"",{"topics":[],"keywords":[]},{"weights":{},"penalties":{"missing_readme":-0.1}},{"blocked_keywords":[],"risky_install_patterns":[]})
        self.assertLess(score,1.0)

    def test_dangerous_install_detection(self):
        risk=mod.detect_risk(self.repo,"run curl | bash",self.blocklist)
        self.assertEqual(risk["level"],"high")

    def test_security_offensive_filter(self):
        self.args.topic="security"
        ok,_=mod.filter_repository(self.repo,"exploit payload",self.args,self.blocklist)
        self.assertFalse(ok)

    def test_no_eda_topic(self):
        t=mod.default_topics().keys()
        for bad in ["eda","openroad","verilog","rtl","vlsi"]:
            self.assertNotIn(bad,t)

if __name__ == "__main__":
    unittest.main()
