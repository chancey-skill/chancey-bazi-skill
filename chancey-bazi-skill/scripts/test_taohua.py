# -*- coding: utf-8 -*-
"""桃花 / 配偶星扫描（taohua.py）回归测试。

规则（2026-10-01）：异性恋（一爱＝四爱）男看财 / 女看官杀；同性恋看比劫。
"""

import contextlib
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import taohua as th  # noqa: E402


class WantCategoryTests(unittest.TestCase):
    def test_hetero_male_female(self):
        self.assertEqual(th.want_category("异性", "男")[0], "财")
        self.assertEqual(th.want_category("异性", "女")[0], "官杀")

    def test_siai_same_as_yiai(self):
        self.assertEqual(th.want_category("四爱", "男")[0], "财")
        self.assertEqual(th.want_category("四爱", "女")[0], "官杀")

    def test_homosexual_bijie(self):
        self.assertEqual(th.want_category("同性", None)[0], "比劫")
        self.assertEqual(th.want_category("男同", "1")[0], "比劫")
        self.assertEqual(th.want_category("女同", "T")[0], "比劫")

    def test_hetero_needs_role(self):
        with self.assertRaises(SystemExit):
            th.want_category("异性", None)


class TaohuaZhiTests(unittest.TestCase):
    def test_groups(self):
        self.assertEqual(th.taohua_zhi("亥"), "子")
        self.assertEqual(th.taohua_zhi("卯"), "子")
        self.assertEqual(th.taohua_zhi("未"), "子")
        self.assertEqual(th.taohua_zhi("申"), "酉")
        self.assertEqual(th.taohua_zhi("酉"), "午")
        self.assertEqual(th.taohua_zhi("戌"), "卯")


class RunSmokeTests(unittest.TestCase):
    def _run(self, argv):
        buf = io.StringIO()
        old = th.sys.argv
        with contextlib.redirect_stdout(buf):
            try:
                th.sys.argv = ["taohua.py"] + argv
                th.main()
            finally:
                th.sys.argv = old
        return buf.getvalue()

    def test_hetero_run(self):
        out = self._run(["--solar", "2007-09-14", "--hour", "20:56", "--sex", "男",
                         "--orientation", "异性", "--role", "男", "--start", "2025", "--end", "2026"])
        self.assertIn("配偶星看 财", out)
        self.assertIn("2026", out)

    def test_homo_run(self):
        out = self._run(["--solar", "2007-09-14", "--hour", "20:56", "--sex", "男",
                         "--orientation", "同性", "--start", "2025", "--end", "2026"])
        self.assertIn("看 比劫", out)


if __name__ == "__main__":
    unittest.main()
