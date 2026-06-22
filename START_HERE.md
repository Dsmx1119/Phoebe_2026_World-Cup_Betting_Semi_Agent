# Start Here

## 一行用法

```bash
python -m sportmira.cli analyze --match "Korea vs Czechia" --bankroll 30 --max-bets 3
python -m sportmira.cli parse-odds --screenshot examples/screenshots/sample.png
python -m sportmira.cli review --match "Korea vs Czechia" --actual-score "2-1"
```

## Full Task Card

输入可以很不完整，例如：

- `SportMira, 看一下 Korea vs Czechia`
- `SportMira, 研究一下 Mexico vs South Africa`
- `SportMira, 用这张盘口截图分析这场`
- `SportMira, 这场我有30u，只买2-3种，怎么分配`

SportMira 会自动：

1. 识别任务类型。
2. 采集公开来源，失败则记录原因。
3. 解析盘口截图或网页盘口。
4. 估计基础概率和 EV。
5. 加入相关性保护和仓位约束。
6. 输出中文 betting memo。
7. 保存报告、投注卡和赛后复盘。

## Help Matrix

| 你想做什么 | 命令 |
|---|---|
| 快速研究一场比赛 | `analyze --match "Team A vs Team B"` |
| 带截图解析盘口 | `analyze --match "Team A vs Team B" --screenshot odds.png` |
| 只解析盘口截图 | `parse-odds --screenshot odds.png` |
| 只买 2-3 种 | `analyze --match "Team A vs Team B" --bankroll 30 --max-bets 3` |
| 赛后复盘 | `review --match "Team A vs Team B" --actual-score "2-1"` |
