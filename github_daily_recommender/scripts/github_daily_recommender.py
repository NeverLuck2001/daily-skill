#!/usr/bin/env python3
"""GitHub daily recommender skill script.

安全设计：
- 仅使用 GitHub 只读 API。
- 不执行第三方项目代码，不 clone、不安装。
- 输出 Markdown/JSON 报告，便于审计。
"""

import argparse
import base64
import datetime as dt
import hashlib
import json
import math
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

GITHUB_SEARCH_API = "https://api.github.com/search/repositories"
GITHUB_API_BASE = "https://api.github.com"
USER_AGENT = "github_daily_recommender/1.0"
DEFAULT_PER_QUERY = 30
ALLOWED_DAYS = [1, 3, 7, 14, 30, 90]


def load_json(path: Path, default: Any) -> Any:
    """Load JSON from disk; return default on error or missing file."""
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path: Path, data: Any) -> None:
    """Save JSON to disk with UTF-8 and pretty format."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def github_request(url: str, token: Optional[str] = None) -> Dict[str, Any]:
    """Perform a GitHub GET request and parse JSON safely."""
    headers = {"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore") if hasattr(e, "read") else ""
        raise RuntimeError(f"GitHub API error: HTTP {e.code}; {body[:200]}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error: {e}")
    except json.JSONDecodeError:
        raise RuntimeError("Invalid JSON response from GitHub API")


def default_topics() -> Dict[str, Any]:
    """Built-in fallback topics config."""
    return {
        "all": {"description": "综合推荐", "topics": ["productivity", "automation", "developer-tools"], "keywords": ["productivity tool", "desktop enhancement"], "preferred_languages": []},
        "ai": {"description": "AI/LLM/Agent", "topics": ["llm", "agent", "rag", "ai", "machine-learning", "inference"], "keywords": ["large language model", "agent", "rag"], "preferred_languages": ["Python", "TypeScript", "Rust", "Go"]},
        "devtools": {"description": "开发工具", "topics": ["developer-tools", "cli", "vscode", "debugging"], "keywords": ["developer productivity", "terminal tool"], "preferred_languages": ["Rust", "Go", "Python", "TypeScript"]},
        "productivity": {"description": "生产力", "topics": ["productivity", "automation", "workflow", "clipboard", "launcher", "todo"], "keywords": ["productivity tool", "workflow automation", "clipboard manager"], "preferred_languages": ["Python", "TypeScript", "Rust", "Go", "PowerShell", "AutoHotkey"]},
        "windows": {"description": "Windows 工具", "topics": ["windows", "powershell", "autohotkey", "desktop", "utility"], "keywords": ["windows automation", "desktop enhancement", "window manager"], "preferred_languages": ["C#", "C++", "PowerShell", "AutoHotkey", "Rust", "Python"]},
        "browser": {"description": "浏览器增强", "topics": ["browser-extension", "chrome-extension", "webextension", "tab-manager", "bookmark-manager"], "keywords": ["browser productivity", "tab manager", "bookmark manager"], "preferred_languages": ["TypeScript", "JavaScript"]},
        "file_management": {"description": "文件管理", "topics": ["file-manager", "backup", "sync", "duplicate-files", "rename"], "keywords": ["file organizer", "bulk rename", "duplicate files"], "preferred_languages": ["Python", "Rust", "Go", "C#"]},
        "media": {"description": "媒体工具", "topics": ["image-processing", "video-processing", "screenshot", "screen-recorder"], "keywords": ["subtitle tool", "media converter"], "preferred_languages": ["Python", "C++", "Rust"]},
        "knowledge": {"description": "知识管理", "topics": ["markdown", "notes", "knowledge-management", "pkm"], "keywords": ["personal knowledge management", "note taking"], "preferred_languages": ["TypeScript", "Python"]},
        "automation": {"description": "自动化", "topics": ["automation", "workflow", "powershell", "autohotkey"], "keywords": ["desktop automation", "task automation"], "preferred_languages": ["Python", "PowerShell", "AutoHotkey"]},
        "selfhosted": {"description": "自部署", "topics": ["self-hosted", "homelab", "nas", "personal-cloud"], "keywords": ["self hosted", "homelab"], "preferred_languages": ["Go", "Rust", "Python"]},
        "security": {"description": "防御安全", "topics": ["security", "privacy", "audit", "hardening", "password-manager"], "keywords": ["security audit", "privacy tool", "defensive security"], "preferred_languages": ["Rust", "Go", "Python"]},
        "daily_life": {"description": "日常生活", "topics": ["habit-tracker", "personal-finance", "calendar", "todo", "recipe", "health"], "keywords": ["life tracker", "personal dashboard", "habit tracker"], "preferred_languages": ["TypeScript", "Python", "JavaScript"]},
        "interesting": {"description": "有趣项目", "topics": ["visualization", "interactive", "toy-project"], "keywords": ["creative coding", "interactive tool"], "preferred_languages": ["TypeScript", "Python", "Rust"]},
        "python": {"description": "Python 工具", "topics": ["python", "automation", "cli"], "keywords": ["python utility", "python automation"], "preferred_languages": ["Python"]},
        "ml": {"description": "机器学习", "topics": ["machine-learning", "deep-learning", "inference"], "keywords": ["model training", "inference optimization"], "preferred_languages": ["Python", "C++", "Rust"]},
    }


def build_search_queries(mode, topic, keyword, days, min_stars, language, include_forks, include_archived):
    """Build multiple GitHub search query plans."""
    after = (dt.datetime.utcnow() - dt.timedelta(days=days)).strftime("%Y-%m-%d")
    base = [f"stars:>{min_stars}", f"created:>{after}"]
    if not include_archived:
        base.append("archived:false")
    if not include_forks:
        base.append("fork:false")
    if language:
        base.append(f"language:{language}")
    base_clause = " ".join(base)

    queries = [
        {"query": base_clause, "sort": "stars", "order": "desc"},
        {"query": base_clause.replace("created:", "updated:"), "sort": "updated", "order": "desc"},
        {"query": base_clause.replace("created:", "pushed:"), "sort": "updated", "order": "desc"},
    ]
    if topic and topic != "all":
        queries.append({"query": f"topic:{topic} {base_clause}", "sort": "stars", "order": "desc"})
    if keyword:
        queries.append({"query": f'"{keyword}" {base_clause}', "sort": "best match", "order": "desc"})
    if mode == "daily" and topic in (None, "all"):
        for t in ["productivity", "automation", "developer-tools"]:
            queries.append({"query": f"topic:{t} {base_clause.replace('created:', 'pushed:')}", "sort": "updated", "order": "desc"})
    return queries


def search_repositories(query, sort, order, per_page, token):
    q = urllib.parse.urlencode({"q": query, "sort": sort, "order": order, "per_page": per_page})
    data = github_request(f"{GITHUB_SEARCH_API}?{q}", token)
    return data.get("items", [])


def merge_and_dedupe_repos(results):
    seen, merged = set(), []
    for lst in results:
        for repo in lst:
            key = repo.get("full_name") or repo.get("html_url")
            if key and key not in seen:
                seen.add(key)
                merged.append(repo)
    return merged


def fetch_readme(owner, repo, token):
    """Fetch README text with multiple fallbacks."""
    paths = [f"/repos/{owner}/{repo}/readme", f"/repos/{owner}/{repo}/contents/README.md", f"/repos/{owner}/{repo}/contents/readme.md", f"/repos/{owner}/{repo}/contents/README.rst", f"/repos/{owner}/{repo}/contents/README.txt"]
    for p in paths:
        try:
            payload = github_request(f"{GITHUB_API_BASE}{p}", token)
            if payload.get("download_url"):
                raw = github_request(payload["download_url"], None)
                if isinstance(raw, dict):
                    pass
            content = payload.get("content")
            if content:
                return base64.b64decode(content).decode("utf-8", errors="ignore")
        except Exception:
            continue
    return ""

def analyze_readme(text):
    """Extract short README signals."""
    low = text.lower() if text else ""
    signals = {
        "has_install": any(k in low for k in ["install", "installation", "setup"]),
        "has_usage": any(k in low for k in ["usage", "example", "quick start"]),
        "has_features": "feature" in low,
        "has_screenshot": any(k in low for k in ["screenshot", "demo", "preview"]),
        "mentions_admin": any(k in low for k in ["administrator", "sudo", "root", "admin permission"]),
    }
    summary = []
    if signals["has_features"]:
        summary.append("README 提供了特性说明")
    if signals["has_install"]:
        summary.append("包含安装步骤")
    if signals["has_usage"]:
        summary.append("包含使用示例")
    if signals["has_screenshot"]:
        summary.append("包含截图或演示信息")
    return {"signals": signals, "summary": summary[:4]}


def detect_risk(repo, readme_text, blocklist):
    text = " ".join([repo.get("name", ""), repo.get("description") or "", readme_text or ""]).lower()
    risks = []
    for k in blocklist.get("blocked_keywords", []):
        if k.lower() in text:
            risks.append(f"命中高风险关键词: {k}")
    for p in blocklist.get("risky_install_patterns", []):
        if p.lower() in text:
            risks.append(f"命中危险安装模式: {p}")
    level = "high" if risks else "low"
    return {"level": level, "notes": risks}


def compute_stars_per_day(repo):
    created = dt.datetime.strptime(repo["created_at"], "%Y-%m-%dT%H:%M:%SZ")
    days = max(1, (dt.datetime.utcnow() - created).days)
    return round(repo.get("stargazers_count", 0) / days, 4)

def compute_recency_score(repo):
    pushed = dt.datetime.strptime(repo.get("pushed_at") or repo.get("updated_at"), "%Y-%m-%dT%H:%M:%SZ")
    age = max(0, (dt.datetime.utcnow() - pushed).days)
    return max(0.0, min(1.0, 1.0 - age / 90.0))

def compute_topic_match_score(repo, topic_config, readme_text):
    hay = " ".join([repo.get("name", ""), repo.get("description") or "", " ".join(repo.get("topics", [])), readme_text or ""]).lower()
    targets = [t.lower() for t in topic_config.get("topics", []) + topic_config.get("keywords", [])]
    if not targets:
        return 0.5
    hits = sum(1 for t in targets if t in hay)
    return min(1.0, hits / max(1, len(targets)))

def compute_readme_quality_score(readme_text):
    if not readme_text:
        return 0.0
    low = readme_text.lower()
    score = 0.2
    if len(readme_text) > 800:
        score += 0.2
    for k in ["install", "usage", "example", "feature", "screenshot", "demo"]:
        if k in low:
            score += 0.1
    return min(1.0, score)

def compute_usability_score(repo, readme_analysis):
    s = 0.2
    if repo.get("description"):
        s += 0.2
    sig = readme_analysis.get("signals", {})
    if sig.get("has_install"):
        s += 0.2
    if sig.get("has_usage"):
        s += 0.2
    if sig.get("has_screenshot"):
        s += 0.2
    return min(1.0, s)

def score_repository(repo, readme_text, topic_config, scoring_config, blocklist):
    """Score repository with transparent weighted formula."""
    weights = scoring_config.get("weights", {})
    penalties = scoring_config.get("penalties", {})
    stars = repo.get("stargazers_count", 0)
    log_stars = math.log(stars + 1) / math.log(100000 + 1)
    spd = min(1.0, compute_stars_per_day(repo) / 20.0)
    recency = compute_recency_score(repo)
    tmatch = compute_topic_match_score(repo, topic_config, readme_text)
    rscore = compute_readme_quality_score(readme_text)
    ran = analyze_readme(readme_text)
    usability = compute_usability_score(repo, ran)
    license_score = 1.0 if repo.get("license") else 0.0
    desc_score = 1.0 if (repo.get("description") or "").strip() else 0.0
    risk = detect_risk(repo, readme_text, blocklist)

    score = (
        weights.get("log_stars", 0.25) * log_stars
        + weights.get("stars_per_day", 0.2) * spd
        + weights.get("recency", 0.15) * recency
        + weights.get("topic_match", 0.15) * tmatch
        + weights.get("readme_quality", 0.1) * rscore
        + weights.get("license", 0.05) * license_score
        + weights.get("usability", 0.05) * usability
        + weights.get("description", 0.05) * desc_score
    )
    if repo.get("fork"):
        score += penalties.get("fork", -0.3)
    if repo.get("archived"):
        score += penalties.get("archived", -1.0)
    if not readme_text:
        score += penalties.get("missing_readme", -0.1)
    if not repo.get("description"):
        score += penalties.get("missing_description", -0.1)
    if risk["level"] == "high":
        score += penalties.get("high_risk", -1.0)
    return max(0.0, min(1.0, score)), {"stars": log_stars, "stars_per_day": spd, "recency": recency, "topic_match": tmatch, "readme_quality": rscore, "license": license_score, "usability": usability, "description": desc_score}, risk

def filter_repository(repo, readme_text, args, blocklist):
    text = f"{repo.get('name','')} {repo.get('description') or ''} {readme_text or ''}".lower()
    if repo.get("archived") and not args.include_archived:
        return False, "archived"
    if repo.get("fork") and not args.include_forks:
        return False, "fork"
    if repo.get("stargazers_count", 0) < args.min_stars and not (repo.get("description") or "").strip():
        return False, "low quality"
    if any(k.lower() in text for k in blocklist.get("blocked_keywords", [])):
        return False, "high risk"
    if args.topic == "security" and any(k in text for k in ["exploit", "rce", "payload", "phishing"]):
        return False, "offensive security"
    return True, "ok"

def rank_repositories(repos):
    return sorted(repos, key=lambda x: x["score"], reverse=True)

def generate_markdown_report(data):
    lines = [
        "# GitHub 每日项目推荐报告",
        "",
        f"生成时间：{data['generated_at']}  ",
        f"主题：{data['topic']}  ",
        f"搜索窗口：最近 {data['days']} 天  ",
        f"最低 stars：{data['min_stars']}  ",
        "数据来源：GitHub Search API  ",
        "说明：热度评分为估算值，并非 GitHub 官方趋势榜。",
        "",
        "## 今日摘要",
        f"- 今日共检索到 {data['total_candidates']} 个候选项目",
        f"- 过滤掉 {data['filtered_count']} 个低质量或高风险项目",
        f"- 最终推荐 {len(data['recommendations'])} 个项目",
        "",
        "## 推荐项目总览",
        "| 排名 | 项目 | 语言 | Stars | 估算 Stars/Day | 更新时间 | 推荐指数 | 标签 |",
        "|---|---|---|---:|---:|---|---:|---|",
    ]
    for r in data["recommendations"]:
        lines.append(f"| {r['rank']} | {r['full_name']} | {r['language'] or '-'} | {r['stars']} | {r['stars_per_day']:.2f} | {r['updated_at'][:10]} | {r['score']:.2f} | {', '.join(r['topics'][:3])} |")
    return "\n".join(lines) + "\n"

def generate_json_report(data):
    return json.dumps(data, ensure_ascii=False, indent=2)

def main():
    root = Path(__file__).resolve().parents[1]
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=["daily", "topic", "search", "trending"], default="daily")
    p.add_argument("--topic", default="all")
    p.add_argument("--days", type=int, default=7, choices=ALLOWED_DAYS)
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--min-stars", type=int, default=50)
    p.add_argument("--language", default="")
    p.add_argument("--keyword", default="")
    p.add_argument("--include-forks", action="store_true")
    p.add_argument("--include-archived", action="store_true")
    p.add_argument("--output", default="")
    p.add_argument("--json-output", default="")
    p.add_argument("--cache", dest="cache", action="store_true", default=True)
    p.add_argument("--cache-ttl-hours", type=int, default=6)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    args.limit = max(1, min(50, args.limit))

    today = dt.datetime.utcnow().strftime("%Y%m%d")
    output = Path(args.output) if args.output else root / "reports" / f"github_daily_recommendations_{today}.md"
    json_output = Path(args.json_output) if args.json_output else root / "reports" / f"github_daily_recommendations_{today}.json"
    topics = load_json(root / "config" / "topics.json", default_topics())
    scoring = load_json(root / "config" / "scoring.json", {"weights": {}, "penalties": {}})
    blocklist = load_json(root / "config" / "blocklist.json", {"blocked_keywords": [], "risky_install_patterns": []})
    if args.topic not in topics:
        args.topic = "all"
    topic_cfg = topics.get(args.topic, topics.get("all", {}))

    queries = build_search_queries(args.mode, args.topic, args.keyword, args.days, args.min_stars, args.language, args.include_forks, args.include_archived)
    if args.dry_run:
        print(json.dumps({"ok": True, "mode": args.mode, "queries": queries}, ensure_ascii=False, indent=2))
        return

    token = os.environ.get("GITHUB_TOKEN")
    warnings = []
    if not token:
        warnings.append("未设置 GITHUB_TOKEN，可能触发 rate limit。")

    all_results = []
    for q in queries:
        try:
            all_results.append(search_repositories(q["query"], q["sort"], q["order"], DEFAULT_PER_QUERY, token))
        except Exception as e:
            warnings.append(str(e))
    merged = merge_and_dedupe_repos(all_results)

    scored, filtered = [], []
    for repo in merged:
        owner, name = repo["full_name"].split("/", 1)
        readme = ""
        try:
            readme = fetch_readme(owner, name, token)
        except Exception:
            pass
        ok, reason = filter_repository(repo, readme, args, blocklist)
        if not ok:
            filtered.append((repo, reason))
            continue
        score, breakdown, risk = score_repository(repo, readme, topic_cfg, scoring, blocklist)
        scored.append({
            "full_name": repo["full_name"], "html_url": repo.get("html_url"), "description": repo.get("description") or "", "language": repo.get("language"),
            "stars": repo.get("stargazers_count", 0), "forks": repo.get("forks_count", 0), "open_issues": repo.get("open_issues_count", 0),
            "license": (repo.get("license") or {}).get("spdx_id") if isinstance(repo.get("license"), dict) else None,
            "topics": repo.get("topics", []), "created_at": repo.get("created_at"), "updated_at": repo.get("updated_at"), "pushed_at": repo.get("pushed_at"),
            "stars_per_day": compute_stars_per_day(repo), "score": round(score, 4), "score_breakdown": breakdown,
            "summary": "; ".join(analyze_readme(readme)["summary"]) if readme else "README unavailable",
            "recommendation_reason": ["近期活跃", "主题匹配度较好"],
            "productivity_value": "可用于提升日常效率，减少重复操作。",
            "daily_life_value": "对日常数字工作流有辅助价值。",
            "risk_level": risk["level"], "risk_notes": risk["notes"],
            "next_action": "read-readme" if risk["level"] == "low" else "skip"
        })

    ranked = rank_repositories(scored)[: args.limit]
    for i, r in enumerate(ranked, 1):
        r["rank"] = i

    payload = {
        "ok": True,
        "generated_at": dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "mode": args.mode,
        "topic": args.topic,
        "days": args.days,
        "min_stars": args.min_stars,
        "total_candidates": len(merged),
        "filtered_count": len(filtered),
        "recommendations": ranked,
        "warnings": warnings,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    json_output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(generate_markdown_report(payload), encoding="utf-8")
    json_output.write_text(generate_json_report(payload), encoding="utf-8")
    print(json.dumps({"ok": True, "report": str(output), "json": str(json_output), "count": len(ranked), "warnings": warnings}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
