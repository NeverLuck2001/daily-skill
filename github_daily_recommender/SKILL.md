---
name: github_daily_recommender
description: Search GitHub for recent popular, interesting, and productivity-enhancing open-source projects and generate daily recommendation reports.
---

## 何时使用
- 用户想要“今日 GitHub 热门推荐 / 开发效率工具推荐 / Windows 效率项目推荐”。
- 用户需要按主题、关键词生成可审计的 Markdown/JSON 报告。

## 何时不要使用
- 用户要求自动 clone、安装、运行项目代码。
- 用户要求 GitHub 写操作（star/fork/issue/PR/comment/release/delete）。

## 安全规则
- 只读访问 GitHub API。
- 不 clone、不安装、不执行任何第三方代码。
- 不读取本机敏感凭据，不泄露 GITHUB_TOKEN。
- 过滤破解、恶意、灰产、凭据窃取、攻击性项目。
- 对管理员权限/敏感权限要求必须标记风险。

## 可用模式
- `daily`：每日综合推荐。
- `topic`：按主题推荐。
- `search`：按关键词推荐。
- `trending`：近期热门综合。

## 参数说明
- `--topic` 默认 `all`
- `--days` 默认 `7`
- `--limit` 默认 `10`，最大 `50`
- `--min-stars` 默认 `50`
- `--keyword` 关键词
- `--dry-run` 仅输出查询计划

## 常用命令
- `python scripts/github_daily_recommender.py --mode daily --topic all --days 7 --limit 10`
- `python scripts/github_daily_recommender.py --mode topic --topic windows --days 30 --limit 10`
- `python scripts/github_daily_recommender.py --mode search --keyword "clipboard manager" --days 90 --limit 10`

## 输出文件
- Markdown: `reports/github_daily_recommendations_yyyyMMdd.md`
- JSON: `reports/github_daily_recommendations_yyyyMMdd.json`

## Agent 总结规范
当用户请求每日推荐时：
1. 若未指定主题，使用 `topic=all`。
2. 默认 `days=7`、`limit=10`。
3. 执行脚本并读取 Markdown 摘要。
4. 在聊天中展示总览、前 5 项、一句话理由、效率/生活价值、安全提醒、报告路径。
5. 不自动 clone/安装/运行任何项目。

## 高风险项目处理原则
- 命中高风险关键词直接过滤。
- 出现 `curl | bash`、`iwr | iex` 等模式标记“谨慎，不建议直接运行”。
