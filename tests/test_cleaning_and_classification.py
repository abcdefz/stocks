import math
import unittest

from graham_screen.classification import financial_subtype, is_financial_subtype
from graham_screen.io import clean_stock_code
from graham_screen.metrics import clean_number


class CleaningAndClassificationTest(unittest.TestCase):
    def test_clean_stock_code_preserves_leading_zeroes(self):
        self.assertEqual(clean_stock_code('="002801"'), "002801")
        self.assertEqual(clean_stock_code("000001"), "000001")
        self.assertEqual(clean_stock_code(" 600000 "), "600000")

    def test_clean_number_handles_lixinger_exports(self):
        self.assertEqual(clean_number('="1,234.50"'), 1234.5)
        self.assertEqual(clean_number("16.71%"), 16.71)
        self.assertTrue(math.isnan(clean_number("--")))
        self.assertTrue(math.isnan(clean_number("")))

    def test_clean_number_normalizes_decimal_percent(self):
        self.assertEqual(clean_number("0.1671", percent=True), 16.71)
        self.assertEqual(clean_number("16.71", percent=True), 16.71)

    def test_financial_subtype_uses_all_industry_levels(self):
        self.assertEqual(financial_subtype({"一级行业": "金融", "二级行业": "银行"}), "银行")
        self.assertEqual(financial_subtype({"一级行业": "非银金融", "二级行业": "保险"}), "保险")
        self.assertEqual(financial_subtype({"一级行业": "非银金融", "二级行业": "证券"}), "证券")
        self.assertEqual(financial_subtype({"一级行业": "金融科技", "二级行业": "支付"}), "其他金融")
        self.assertEqual(financial_subtype({"一级行业": "电力设备", "二级行业": "电机"}), "非金融")

    def test_is_financial_subtype(self):
        self.assertTrue(is_financial_subtype("银行"))
        self.assertFalse(is_financial_subtype("非金融"))


if __name__ == "__main__":
    unittest.main()
