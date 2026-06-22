# SportMira Match Betting Memo: Korea vs Czechia

## 1. 直接结论

* 主判断：当前数据或价格不足，不建议为了下单而下单。（judgment，不是 guaranteed betting advice）
* 最佳盘口：No bet / 等待更清晰赔率
* 不建议买的盘口：没有模型覆盖、没有赔率、或 EV 不足的盘口。
* 建议仓位：0u
* 预测比分：1-1（inference: Poisson baseline）
* stale_after：2026-06-12T20:03:20+00:00

## 2. 当前盘口快照

| Market | Selection | Odds | Implied Prob | No-vig Prob | Notes |
|---|---:|---:|---:|---:|---|
| missing | - | - | - | - | 没有可用 odds snapshot；不能推荐无赔率市场。 |

## 3. 球队近况与打法

* Korea：last 5 matches / goals / cards / formation 未可靠结构化解析；见 E1。模型只使用低置信 baseline 或市场先验。
* Czechia：last 5 matches / goals / cards / formation 未可靠结构化解析；见 E1。不得把缺失数据当事实。
* physicality / set-piece reliance：当前为 inference unavailable，需赛前新闻和阵容确认。

## 4. 裁判报告

* referee identity：未确认；见 E4。
* yellow/red/penalty tendency：数据缺失时只使用 cards baseline，置信度 low。
* physical contact tolerance：inference unavailable until referee announced。

## 5. 战术对位

* 控球权：inference，缺少可靠阵容和近期打法数据时不做强断言。
* high-quality chances：以 Poisson baseline + market prior 近似，不等于真实 xG。
* transition risk：若首发边后卫/中卫组合变化，必须刷新。
* set-piece mismatch：当前无事实来源支持，保持 low confidence。
* late-game paths：早球会推高 over/open-game path；长时间 0-0 会强化 draw/under 相关性。

## 6. 模型概率

| Market | Model Prob | Market Implied Prob | Edge | Confidence |
|---|---:|---:|---:|---:|
| 1x2 home | 38.6% | - | - | low |
| 1x2 draw | 27.6% | - | - | low |
| 1x2 away | 33.8% | - | - | low |
| total_goals over 1.5 | 69.2% | - | - | low |
| total_goals under 1.5 | 30.8% | - | - | low |
| total_goals over 2.0 | 43.0% | - | - | low |
| total_goals under 2.0 | 30.8% | - | - | low |
| total_goals over 2.25 | 43.0% | - | - | low |
| total_goals under 2.25 | 57.0% | - | - | low |
| total_goals over 2.5 | 43.0% | - | - | low |
| total_goals under 2.5 | 57.0% | - | - | low |
| total_goals over 2.75 | 43.0% | - | - | low |
| total_goals under 2.75 | 57.0% | - | - | low |
| total_goals over 3.5 | 22.1% | - | - | low |
| total_goals under 3.5 | 77.9% | - | - | low |
| total_cards over 3.5 | 60.5% | - | - | low |
| total_cards under 3.5 | 39.5% | - | - | low |
| total_cards over 4.5 | 41.0% | - | - | low |

## 7. 投注建议

| Bet | Odds | Stake | Reason | Main Risk |
|---|---:|---:|---|---|
| No bet | - | 0u | 没有满足赔率、EV、置信度和相关性约束的投注。 | 强行下单会把 research 变成猜测。 |

## 8. 相关性和风险

* 没有可用赔率，SportMira 不会推荐无赔率市场。
* what scoreline kills the card：与推荐方向相反的早球、红牌或战术退守会破坏模型假设。
* early event invalidates thesis：首发重大变化、盘口大幅移动、早红牌、早 penalty。

## 9. must_refresh_if

* starting lineups differ materially
* referee announced or changes
* odds move more than 8-10% from captured snapshot
* key player ruled out or unexpectedly starts
* weather/venue/kickoff changes
* live red card or early penalty changes match state

## 10. Evidence Log

| id | claim | source_name | source_url | accessed_at | confidence | used_in |
|---|---|---|---|---|---|---|
| E1 | team_form returned status=missing; notes=No reliable structured free form data was parsed; model must use low-confidence baseline or market prior. | team_form | public_sources_best_effort | 2026-06-12T08:03:20+00:00 | low | data_collection |
| E2 | football_results returned status=unavailable; notes=requests not installed | football_results | https://en.wikipedia.org/w/index.php?search=Korea+Czechia+recent+results+football | 2026-06-12T08:03:20+00:00 | low | data_collection |
| E3 | news_preview returned status=unavailable; notes=requests not installed | news_preview | https://duckduckgo.com/html/?q=Korea+vs+Czechia+expected+lineups+injuries+preview | 2026-06-12T08:03:20+00:00 | low | data_collection |
| E4 | referee_profile returned status=missing; notes=Referee could not be identified from public structured sources; must_refresh_if referee announced or changes. | referee_profile | referee_not_announced_or_not_collected | 2026-06-12T08:03:20+00:00 | low | data_collection |
| E5 | venue_weather returned status=missing; notes=Venue was not provided; weather must be refreshed if venue/kickoff is known. | venue_weather | venue_missing | 2026-06-12T08:03:20+00:00 | low | data_collection |
| E6 | whoscored_public returned status=unavailable; notes=WhoScored is JS-heavy and may restrict automated access; SportMira MVP does not bypass protections. | whoscored_public | https://www.whoscored.com/ | 2026-06-12T08:03:20+00:00 | low | data_collection |
| E7 | search_web returned status=unavailable; notes=requests not installed | search_web | https://duckduckgo.com/html/?q=Korea+Czechia+football+preview+odds+lineups | 2026-06-12T08:03:20+00:00 | low | data_collection |

> SportMira 只提供研究备忘录，不自动下注，不保证结果。