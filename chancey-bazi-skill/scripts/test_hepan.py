# -*- coding: utf-8 -*-
"""合盘脚本（hepan.py）回归测试。"""

import os
import sys
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hepan as h  # noqa: E402
import pai_pan as pp  # noqa: E402


class RelationTests(unittest.TestCase):
    def test_gan_wuhe(self):
        self.assertEqual(h.gan_relation("丁", "壬"), "天干五合")
        self.assertEqual(h.gan_relation("丙", "辛"), "天干五合")

    def test_gan_chong(self):
        self.assertEqual(h.gan_relation("甲", "庚"), "天干相冲")
        self.assertEqual(h.gan_relation("丁", "癸"), "天干相冲")

    def test_gan_sheng(self):
        self.assertEqual(h.gan_relation("辛", "壬"), "天干相生(前生后)")
        self.assertEqual(h.gan_relation("壬", "辛"), "天干相生(后生前)")

    def test_zhi_liuhe_chong_hai(self):
        self.assertIn("地支六合", h.zhi_relation("子", "丑"))
        self.assertIn("地支六冲", h.zhi_relation("卯", "酉"))
        self.assertIn("地支六害", h.zhi_relation("酉", "戌"))

    def test_zhi_sanhe_sanhui(self):
        self.assertIn("半合(三合缺一)", h.zhi_relation("申", "子"))
        self.assertIn("半会(三会缺一)", h.zhi_relation("酉", "戌"))

    def test_zhi_xing_po(self):
        self.assertIn("地支相刑(无礼)", h.zhi_relation("子", "卯"))
        self.assertIn("地支相刑", h.zhi_relation("寅", "巳"))
        self.assertIn("地支相破", h.zhi_relation("子", "酉"))

    def test_zhi_zixing(self):
        self.assertIn("自刑", h.zhi_relation("辰", "辰"))

    def test_taohua(self):
        self.assertEqual(h.taohua_zhi("亥"), "子")   # 亥卯未见子
        self.assertEqual(h.taohua_zhi("卯"), "子")
        self.assertEqual(h.taohua_zhi("申"), "酉")   # 申子辰见酉
        self.assertEqual(h.taohua_zhi("酉"), "午")   # 巳酉丑见午
        self.assertEqual(h.taohua_zhi("戌"), "卯")   # 寅午戌见卯


class PersonTests(unittest.TestCase):
    def _mk(self, solar, hour, sex, role):
        return h.Person(
            "X",
            pp.compute(solar_date=solar, hour=hour[0], minute=hour[1], sex=sex),
            role,
        )

    def test_known_2007(self):
        p = self._mk(date(2007, 9, 14), (20, 56), "男", "男")
        self.assertEqual(p.pillars["year"][:2], ("丁", "亥"))
        self.assertEqual(p.pillars["month"][:2], ("己", "酉"))
        self.assertEqual(p.pillars["day"][:2], ("辛", "亥"))
        self.assertEqual(p.pillars["hour"][:2], ("戊", "戌"))
        self.assertEqual(p.day_gan, "辛")
        self.assertEqual(p.tp_y, "子")
        self.assertEqual(p.want_cat(), "财")

    def test_known_2006(self):
        p = self._mk(date(2006, 10, 30), (1, 50), "男", "女")
        self.assertEqual(p.pillars["day"][:2], ("壬", "辰"))
        self.assertEqual(p.tp_y, "卯")
        self.assertEqual(p.tp_d, "酉")
        self.assertEqual(p.want_cat(), "官杀")

    def test_role_default_follows_sex(self):
        p = h.Person("X", pp.compute(solar_date=date(2000, 1, 1), hour=12, minute=0, sex="女"), "女")
        self.assertEqual(p.want_cat(), "官杀")


class EndToEndTests(unittest.TestCase):
    def test_run_smoke(self):
        # 不应抛异常；返回码 0
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = h.run([
                "--a-solar", "2007-09-14", "--a-hour", "20:56", "--a-sex", "男", "--a-role", "男",
                "--b-solar", "2006-10-30", "--b-hour", "01:50", "--b-sex", "男", "--b-role", "女",
                "--start-year", "2024", "--end-year", "2026",
            ])
        self.assertEqual(rc, 0)
        self.assertIn("合盘报告", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
