## **Phoebe** 
[中文说明](README.zh.md) | English
Phoebe is a free, local-first football/soccer betting research agent. 

It borrows the workflow logic of an investment research system: route the task first, collect multi-source evidence, preserve an evidence log, separate facts from inference and judgment, calculate implied probability, model probability, expected value, and bankroll-aware position sizing, then generate a structured betting memo. 

Phoebe is not an auto-betting tool and does not guarantee profit. It is designed for research, documentation, and post-match review only. It does not connect to sportsbooks, bypass logins, bypass paywalls, solve CAPTCHA, or evade website protections. 

## **Installation** 

Python 3.11+ is recommended. 

cd Phoebe python -m venv .venv source .venv/bin/activate pip install -e ".[ocr,browser,test]" 

A minimal offline mode does not require all optional dependencies. The core CLI includes a standardlibrary fallback: 

cd Phoebe python -m phoebe.cli analyze --match "Korea vs Czechia" --bankroll 30 --max-bets 3 

## **Ollama Setup** 

Phoebe tries to use local Ollama by default when available: 

ollama pull qwen2.5:7b-instruct export PHOEBE_OLLAMA_MODEL=qwen2.5:7b-instruct 

If Ollama is unavailable, Phoebe automatically falls back to a deterministic template mode and still generates a lower-confidence report. 

## **Tesseract OCR Setup** 

Odds screenshot parsing requires optional OCR dependencies: 

1 

pip install -e ".[ocr]" brew install tesseract tesseract-lang 

If OCR is not installed, parse-odds will return a clear installation message instead of crashing. 

## **Examples** 

Analyze a match in Chinese: 

python -m phoebe.cli analyze --match "Korea vs Czechia" --bankroll 30 --unit u --max-bets 3 -- language zh 

Analyze a match with an odds screenshot: 

python -m phoebe.cli analyze --match "Korea vs Czechia" --screenshot ./odds.png --bankroll 30 -- unit u --max-bets 3 

Parse odds from a screenshot: 

python -m phoebe.cli parse-odds --screenshot ./odds.png 

Review a completed match: 

python -m phoebe.cli review --match "Korea vs Czechia" --actual-score "2-1" --cards "1-0" --redcards "0-0" 

## **Core Workflow** 

Phoebe follows a structured research process: 

1. Identify the match and betting market. 

2. Collect available public information. 

3. Extract odds data manually or through screenshots. 

4. Build an evidence log with source metadata. 

5. Separate facts, assumptions, inference, and judgment. 

6. Estimate implied probability and model probability. 

7. Calculate expected value. 

8. Generate bankroll-aware bet sizing. 

9. Produce a betting memo. 

10. Review the result after the match. 

## **Design Principles** 

- Local-first and free to run. 

2 

- No paid API dependency by default. 

- No automatic sportsbook execution. 

- Evidence-based reasoning instead of blind prediction. 

- Clear distinction between data, inference, and opinion. 

- Conservative handling of missing or unreliable information. 

- Post-match review for continuous improvement. 

## **Limitations** 

- Phoebe does not use paid APIs or the OpenAI API by default. 

   - Public web collection is best-effort. 

- 

   - If a source fails, Phoebe records it as unavailable and lowers confidence. 

- 

   - All factual claims should include source metadata. 

- 

   - Missing data should be marked as missing or inference . 

- 

   - The model is a transparent baseline, not a deterministic prediction engine. 

- 

   - Phoebe never places bets automatically. 

- 

## **Disclaimer** 

Phoebe is for educational, research, and documentation purposes only. 

Sports betting involves financial risk. Phoebe does not provide guaranteed betting advice, does not guarantee profit, and should not be treated as a substitute for independent judgment. Users are responsible for complying with all applicable laws and regulations in their jurisdiction. 

3 

