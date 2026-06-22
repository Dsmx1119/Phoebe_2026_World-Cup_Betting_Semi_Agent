import unittest

from sportmira.llm.prompts import (
    BETTING_AGENT_SYSTEM_PROMPT,
    REPORT_SYSTEM_PROMPT,
    build_context_injection_prompt,
)


class PromptTests(unittest.TestCase):
    def test_quant_prompt_contains_hard_ev_and_kelly_rules(self):
        self.assertIn("EV = (模型预测概率 × 博彩公司十进制赔率) - 1", BETTING_AGENT_SYSTEM_PROMPT)
        self.assertIn("EV ≤ 0", BETTING_AGENT_SYSTEM_PROMPT)
        self.assertIn("Quarter-Kelly", BETTING_AGENT_SYSTEM_PROMPT)
        self.assertIn("绝对禁止满仓或梭哈", BETTING_AGENT_SYSTEM_PROMPT)
        self.assertIn("📊 【数据核心对比】", BETTING_AGENT_SYSTEM_PROMPT)

    def test_report_prompt_inherits_quant_rules(self):
        self.assertIn(BETTING_AGENT_SYSTEM_PROMPT, REPORT_SYSTEM_PROMPT)
        self.assertIn("Evidence Log", REPORT_SYSTEM_PROMPT)

    def test_context_injection_prompt_wraps_json_and_question(self):
        prompt = build_context_injection_prompt("怎么投？", '{"home": "France"}')
        self.assertIn("# Injected Match Context JSON", prompt)
        self.assertIn('"home": "France"', prompt)
        self.assertIn("怎么投？", prompt)


if __name__ == "__main__":
    unittest.main()
