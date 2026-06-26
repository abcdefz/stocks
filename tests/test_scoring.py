import unittest

import pandas as pd

from graham_screen.scoring import build_bank_candidate_pool, rules_for_market, score_ordinary_companies


class ScoringTest(unittest.TestCase):
    def test_a_strict_pass_requires_all_rules(self):
        frame = pd.DataFrame(
            [
                {
                    "交易所": "sz",
                    "代码": "000001",
                    "公司": "样本公司",
                    "PE-TTM": 10,
                    "PB": 1,
                    "PE×PB": 10,
                    "PE十年分位": 10,
                    "PB十年分位": 10,
                    "股息率": 4,
                    "ROE5均": 9,
                    "扣非ROE5均": 7,
                    "归母净利润5年全正": True,
                    "扣非归母净利润5年全正": True,
                    "资产负债率": 50,
                    "有息负债率": 20,
                    "流动比率": 1.3,
                    "速动比率": 0.9,
                    "经营现金流/净利润5年": 1.0,
                    "自由现金流5年合计": 1,
                }
            ]
        )

        scored = score_ordinary_companies(frame)

        self.assertTrue(scored.loc[0, "A档"])
        self.assertFalse(scored.loc[0, "B档"])
        self.assertEqual(scored.loc[0, "评分"], 1.0)
        self.assertEqual(scored.loc[0, "缺失项"], "")

    def test_b_observation_uses_score_and_missing_denominator(self):
        frame = pd.DataFrame(
            [
                {
                    "交易所": "sz",
                    "代码": "000002",
                    "公司": "观察公司",
                    "PE-TTM": 10,
                    "PB": 1,
                    "PE×PB": 10,
                    "PE十年分位": 10,
                    "PB十年分位": 10,
                    "股息率": 4,
                    "ROE5均": 9,
                    "扣非ROE5均": 7,
                    "归母净利润5年全正": True,
                    "扣非归母净利润5年全正": True,
                    "资产负债率": 50,
                    "有息负债率": 20,
                    "流动比率": 1.3,
                    "速动比率": 0.9,
                    "经营现金流/净利润5年": 0.5,
                    "自由现金流5年合计": None,
                }
            ]
        )

        scored = score_ordinary_companies(frame)

        self.assertFalse(scored.loc[0, "A档"])
        self.assertTrue(scored.loc[0, "B档"])
        self.assertGreaterEqual(scored.loc[0, "评分"], 0.85)
        self.assertIn("自由现金流5年合计", scored.loc[0, "缺失项"])
        self.assertIn("经营现金流/净利润5年", scored.loc[0, "未通过规则"])

    def test_hk_rules_use_only_lixinger_available_fields(self):
        frame = pd.DataFrame(
            [
                {
                    "交易所": "hk",
                    "代码": "00819",
                    "公司": "港股样本",
                    "PE-TTM": 5,
                    "PB": 0.6,
                    "PE×PB": 3,
                    "PE十年分位": 10,
                    "PB十年分位": 10,
                    "股息率": 5,
                    "ROE5均": 10,
                    "归母净利润5年全正": True,
                    "资产负债率": 50,
                    "流动比率": 1.3,
                    "经营现金流/净利润5年": 1.0,
                }
            ]
        )

        scored = score_ordinary_companies(frame, rules=rules_for_market("hk"))

        self.assertTrue(scored.loc[0, "A档"])
        self.assertEqual(scored.loc[0, "缺失项"], "")
        self.assertEqual(scored.loc[0, "可判断规则数"], 11)

    def test_c_low_priority_observation_uses_valuation_gate_and_score_range(self):
        frame = pd.DataFrame(
            [
                {
                    "交易所": "sz",
                    "代码": "000003",
                    "公司": "低优先级观察公司",
                    "PE-TTM": 10,
                    "PB": 1,
                    "PE×PB": 10,
                    "PE十年分位": 10,
                    "PB十年分位": 10,
                    "股息率": 4,
                    "ROE5均": 9,
                    "扣非ROE5均": 7,
                    "归母净利润5年全正": True,
                    "扣非归母净利润5年全正": True,
                    "资产负债率": 70,
                    "有息负债率": 40,
                    "流动比率": 1.0,
                    "速动比率": 0.7,
                    "经营现金流/净利润5年": 1.0,
                    "自由现金流5年合计": 1,
                }
            ]
        )

        scored = score_ordinary_companies(frame)

        self.assertFalse(scored.loc[0, "A档"])
        self.assertFalse(scored.loc[0, "B档"])
        self.assertTrue(scored.loc[0, "C档"])
        self.assertEqual(scored.loc[0, "评分"], 0.75)
        self.assertIn("资产负债率", scored.loc[0, "未通过规则"])

    def test_bank_candidate_pool_filters_and_tags_banks(self):
        frame = pd.DataFrame(
            [
                {
                    "交易所": "sh",
                    "代码": "600000",
                    "公司": "样本银行",
                    "金融分类": "银行",
                    "PB": 0.7,
                    "PB十年分位": 20,
                    "股息率": 5,
                    "ROE5均": 9,
                    "扣非ROE5均": 7,
                    "归母净利润5年全正": True,
                    "扣非归母净利润5年全正": True,
                    "A股市值": 1000,
                },
                {
                    "交易所": "sh",
                    "代码": "600001",
                    "公司": "高PB银行",
                    "金融分类": "银行",
                    "PB": 1.2,
                    "PB十年分位": 20,
                    "股息率": 5,
                    "ROE5均": 9,
                    "扣非ROE5均": 7,
                    "归母净利润5年全正": True,
                    "扣非归母净利润5年全正": True,
                    "A股市值": 900,
                },
            ]
        )

        pool = build_bank_candidate_pool(frame)

        self.assertEqual(pool["代码"].tolist(), ["600000"])
        self.assertEqual(pool.loc[0, "观察标签"], "低PB高股息观察")


if __name__ == "__main__":
    unittest.main()
