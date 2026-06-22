# Phoebe

Phoebe 是一个免费、local-first 的足球/足球博彩研究 agent。它借鉴 Mira 投研系统的工作流：先路由任务，再收集多源证据，保留 evidence log，区分 fact / inference / judgment，计算隐含概率、模型概率、EV 和仓位建议，最后输出中文 betting memo。

Phoebe 不是自动下注工具，也不会保证盈利。它只做研究、记录和复盘，不连接 sportsbook，不绕过登录、付费墙、CAPTCHA 或网站保护。

Phoebe的前身是SportsMira，所以在文件中看到SportsMira请自动认为是Phoebe
## 安装

推荐 Python 3.11+：

```bash
cd sportmira
python -m venv .venv
source .venv/bin/activate
pip install -e ".[ocr,browser,test]"
```

最小离线模式不强制安装依赖；核心 CLI 有标准库 fallback：

```bash
cd sportmira
python -m sportmira.cli analyze --match "Korea vs Czechia" --bankroll 30 --max-bets 3
```

## Ollama 设置

SportMira 默认优先尝试本地 Ollama：

```bash
ollama pull qwen2.5:7b-instruct
export SPORTMIRA_OLLAMA_MODEL=qwen2.5:7b-instruct
```

如果 Ollama 不可用，SportMira 会自动使用 deterministic template fallback，仍然生成低置信报告。

## Tesseract OCR 设置

盘口截图解析需要可选 OCR 依赖：

```bash
pip install -e ".[ocr]"
brew install tesseract tesseract-lang
```

没有 OCR 时，`parse-odds` 会输出清晰的安装提示，不会崩溃。

## 示例

```bash
python -m sportmira.cli analyze --match "Korea vs Czechia" --bankroll 30 --unit u --max-bets 3 --language zh
python -m sportmira.cli analyze --match "Korea vs Czechia" --screenshot ./odds.png --bankroll 30 --unit u --max-bets 3
python -m sportmira.cli parse-odds --screenshot ./odds.png
python -m sportmira.cli review --match "Korea vs Czechia" --actual-score "2-1" --cards "1-0" --red-cards "0-0"
```

## 限制

- 不使用付费 API，不使用 OpenAI API。
- 公共网页采集是 best-effort；来源失败时会保留 unavailable 记录并降低置信度。
- 所有事实性内容必须带 source metadata；缺失数据会标记为 missing / inference。
- 模型只是透明 baseline，不是确定性预测。
- SportMira 永不自动下单。
