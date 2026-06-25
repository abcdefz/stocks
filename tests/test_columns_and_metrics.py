import unittest

import pandas as pd

from graham_screen.columns import canonicalize_csv1, canonicalize_csv2
from graham_screen.metrics import derive_metrics


class ColumnsAndMetricsTest(unittest.TestCase):
    def test_canonicalize_csv1_prefers_enhanced_pe_pb_fields(self):
        raw = pd.DataFrame(
            {
                "交易所": ["sz"],
                "代码": ['="002801"'],
                "公司": ["微光股份"],
                "一级行业": ["电力设备"],
                "二级行业": ["电机"],
                "三级行业": ["电机"],
                "上市日期  ": ["2016-06-22"],
                "A股市值 最新时间 (亿元)": ["50"],
                "PE-TTM 最新时间 ": ["12"],
                "PE-TTM(扣非) 最新时间 ": ["10"],
                "PB 最新时间 ": ["1.4"],
                "PB(不含商誉) 最新时间 ": ["1.2"],
                "PE-TTM统计值(10年)·分位点% 最新时间 ": ["19"],
                "PE-TTM(扣非)统计值(10年)·分位点% 最新时间 ": ["17"],
                "PB统计值(10年)·分位点% 最新时间 ": ["18"],
                "PB(不含商誉)统计值(10年)·分位点% 最新时间 ": ["16"],
                "股息率 最新时间 ": ["3.5"],
                "理杏仁Url": ["https://example.test/002801"],
            }
        )

        canonical = canonicalize_csv1(raw)

        self.assertEqual(canonical.loc[0, "代码"], "002801")
        self.assertEqual(canonical.loc[0, "PE-TTM"], 10)
        self.assertEqual(canonical.loc[0, "PE-TTM_普通"], 12)
        self.assertEqual(canonical.loc[0, "PB"], 1.2)
        self.assertEqual(canonical.loc[0, "PB_普通"], 1.4)
        self.assertEqual(canonical.loc[0, "PE十年分位"], 17)
        self.assertEqual(canonical.loc[0, "PB十年分位"], 16)

    def test_canonicalize_csv2_maps_five_year_history(self):
        raw = pd.DataFrame(
            {
                "交易所": ["sz"],
                "代码": ['="002801"'],
                "净资产收益率(ROE) 累积 【动态日期】:【最新Q4（2025-Q4）】->【2025-12-31】 ": ["10"],
                "净资产收益率(ROE) 累积 【动态日期】:【最新Q4（2025-Q4）偏移1年】->【2024-12-31】 ": ["9"],
                "净资产收益率(ROE) 累积 【动态日期】:【最新Q4（2025-Q4）偏移2年】->【2023-12-31】 ": ["8"],
                "净资产收益率(ROE) 累积 【动态日期】:【最新Q4（2025-Q4）偏移3年】->【2022-12-31】 ": ["7"],
                "净资产收益率(ROE) 累积 【动态日期】:【最新Q4（2025-Q4）偏移4年】->【2021-12-31】 ": ["6"],
                "归属于母公司普通股股东的扣非ROE 累积 【动态日期】:【最新Q4（2025-Q4）】->【2025-12-31】 ": ["9"],
                "归属于母公司普通股股东的扣非ROE 累积 【动态日期】:【最新Q4（2025-Q4）偏移1年】->【2024-12-31】 ": ["8"],
                "归属于母公司普通股股东的扣除非经常性损益的净利润 累积 【动态日期】:【最新Q4（2025-Q4）】->【2025-12-31】 (亿元)": ["5"],
                "归属于母公司普通股股东的扣除非经常性损益的净利润 累积 【动态日期】:【最新Q4（2025-Q4）偏移4年】->【2021-12-31】 (亿元)": ["4"],
                "股息率统计值(5年)·平均值 最新时间 ": ["4.2"],
            }
        )

        canonical = canonicalize_csv2(raw)

        self.assertEqual(canonical.loc[0, "ROE_0"], 10)
        self.assertEqual(canonical.loc[0, "ROE_4"], 6)
        self.assertEqual(canonical.loc[0, "扣非ROE_0"], 9)
        self.assertEqual(canonical.loc[0, "扣非归母净利润_4"], 4)
        self.assertEqual(canonical.loc[0, "股息率5年平均"], 4.2)

    def test_canonicalize_csv_maps_hk_market_cap_and_parent_profit_history(self):
        csv1 = pd.DataFrame(
            {
                "交易所": ["hk"],
                "代码": ['="00819"'],
                "公司": ["天能动力"],
                "H股市值 最新时间 (亿港币)": ["53.7"],
                "PE-TTM 最新时间 ": ["3.3"],
                "PB 最新时间 ": ["0.3"],
            }
        )
        csv2 = pd.DataFrame(
            {
                "交易所": ["hk"],
                "代码": ['="00819"'],
                "归属于母公司股东及其他权益持有者的净利润 累积 【动态日期】:【最新Q4（2025-Q4）】->【2025-12-31】 (亿港币)": ["10"],
                "归属于母公司股东及其他权益持有者的净利润 累积 【动态日期】:【最新Q4（2025-Q4）偏移1年】->【2024-12-31】 (亿港币)": ["9"],
                "归属于母公司股东及其他权益持有者的净利润 累积 【动态日期】:【最新Q4（2025-Q4）偏移2年】->【2023-12-31】 (亿港币)": ["8"],
                "归属于母公司股东及其他权益持有者的净利润 累积 【动态日期】:【最新Q4（2025-Q4）偏移3年】->【2022-12-31】 (亿港币)": ["7"],
                "归属于母公司股东及其他权益持有者的净利润 累积 【动态日期】:【最新Q4（2025-Q4）偏移4年】->【2021-12-31】 (亿港币)": ["6"],
            }
        )

        canonical1 = canonicalize_csv1(csv1)
        canonical2 = canonicalize_csv2(csv2)

        self.assertEqual(canonical1.loc[0, "A股市值"], 53.7)
        self.assertEqual(canonical2.loc[0, "归母净利润_0"], 10)
        self.assertEqual(canonical2.loc[0, "归母净利润_4"], 6)

    def test_derive_metrics_calculates_history_fields(self):
        frame = pd.DataFrame(
            {
                "PE-TTM": [10],
                "PB": [1.5],
                "上市日期": ["2020-06-01"],
                "ROE_0": [10],
                "ROE_1": [9],
                "ROE_2": [8],
                "ROE_3": [7],
                "ROE_4": [6],
                "扣非ROE_0": [9],
                "扣非ROE_1": [8],
                "扣非ROE_2": [7],
                "扣非ROE_3": [6],
                "扣非ROE_4": [5],
                "归母净利润_0": [5],
                "归母净利润_1": [4],
                "归母净利润_2": [3],
                "归母净利润_3": [2],
                "归母净利润_4": [1],
                "扣非归母净利润_0": [5],
                "扣非归母净利润_1": [4],
                "扣非归母净利润_2": [3],
                "扣非归母净利润_3": [2],
                "扣非归母净利润_4": [1],
                "自由现金流_0": [1],
                "自由现金流_1": [1],
                "自由现金流_2": [1],
                "自由现金流_3": [1],
                "自由现金流_4": [1],
                "经营现金流入_0": [10],
                "经营现金流入_1": [10],
                "经营现金流入_2": [10],
                "经营现金流入_3": [10],
                "经营现金流入_4": [10],
                "经营现金流出_0": [5],
                "经营现金流出_1": [5],
                "经营现金流出_2": [5],
                "经营现金流出_3": [5],
                "经营现金流出_4": [5],
                "销售商品提供劳务收到的现金": [120],
                "营业收入": [100],
            }
        )

        result = derive_metrics(frame)

        self.assertEqual(result.loc[0, "PE×PB"], 15)
        self.assertEqual(result.loc[0, "ROE5均"], 8)
        self.assertEqual(result.loc[0, "ROE5最小"], 6)
        self.assertTrue(result.loc[0, "归母净利润5年全正"])
        self.assertTrue(result.loc[0, "扣非归母净利润5年全正"])
        self.assertAlmostEqual(result.loc[0, "扣非归母净利润5年CAGR"], 49.534878, places=5)
        self.assertEqual(result.loc[0, "自由现金流5年合计"], 5)
        self.assertAlmostEqual(result.loc[0, "经营现金流/净利润5年"], 25 / 15)
        self.assertEqual(result.loc[0, "收现比"], 1.2)


if __name__ == "__main__":
    unittest.main()
