# github_daily_recommender

一个安全、可审计、可本地运行的 OpenClaw Skill：只读访问 GitHub，搜索近期热门/实用开源项目并生成每日推荐报告。

## 功能列表
- 每日推荐、按主题推荐、按关键词搜索、近期热门模式。
- 多查询策略合并去重。
- 可配置评分模型（stars、stars/day、主题匹配、README质量等）。
- 高风险项目过滤与风险提示。
- 输出 Markdown、JSON、控制台摘要。

## 安装方式
- Python 3.9+（仅标准库，无第三方依赖）。
- 将目录放到 OpenClaw skills 目录。

## 放置到 OpenClaw skills 目录
- 复制 `github_daily_recommender/` 到 `$CODEX_HOME/skills/`（或你的 skills 目录）。

## GitHub Token 配置
PowerShell:
```powershell
$env:GITHUB_TOKEN="ghp_xxx"
```
建议使用系统环境变量，不要写入配置文件。

## 使用示例
```bash
python scripts/github_daily_recommender.py --mode daily --topic all --days 7 --limit 10
python scripts/github_daily_recommender.py --mode topic --topic productivity --days 14 --limit 10
python scripts/github_daily_recommender.py --mode topic --topic windows --days 30 --limit 10
python scripts/github_daily_recommender.py --mode topic --topic browser --days 30 --limit 10
python scripts/github_daily_recommender.py --mode topic --topic file_management --days 30 --limit 10
python scripts/github_daily_recommender.py --mode topic --topic daily_life --days 90 --limit 10 --min-stars 10
python scripts/github_daily_recommender.py --mode search --keyword "windows automation" --days 30 --limit 10
python scripts/github_daily_recommender.py --mode search --keyword "clipboard manager" --days 90 --limit 10
```

## 输出说明
- Markdown 默认输出到 `reports/github_daily_recommendations_yyyyMMdd.md`
- JSON 默认输出到 `reports/github_daily_recommendations_yyyyMMdd.json`

## 评分函数说明
评分是估算值，不是 GitHub 官方趋势：
`score = 0.25*log_stars + 0.20*stars_per_day + 0.15*recency + 0.15*topic_match + 0.10*readme_quality + 0.05*license + 0.05*usability + 0.05*description`。

## 安全策略
- 只做搜索、分析、推荐。
- 不 clone、不安装、不执行任何项目代码。
- 不做 GitHub 写操作。
- 不读取本机敏感凭据。

## 常见问题
- 无 `GITHUB_TOKEN` 时：可运行，但可能触发 rate limit。
- README 获取失败：报告中会显示 `README unavailable`。

## 后续扩展
- 接入 Hacker News / Reddit / Product Hunt（默认不实现）
- 用户偏好学习、每周总结、观察列表、趋势分析、中文摘要
