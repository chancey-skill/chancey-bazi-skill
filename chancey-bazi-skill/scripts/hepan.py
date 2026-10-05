#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""合盘脚本：双人八字契合度（机械计算部分）。

规则见 references/compatibility-rules.md。本脚本只做「机械」部分：

- 两盘四柱（十神、藏干）
- 五行分布（主气 / 全藏干两种口径）
- 身强弱粗估（仅供参考，以格局分析为准）
- 四柱逐柱对应关系（天干五合/冲/克；地支六合/三合/三会/六冲/六害/刑/破）
- 大运 / 流年 十神标记（财/官杀/印/比劫/食伤）
- 桃花引动时间线（流年命中桃花位）
- 财—官杀 窗口交集（角色适配的「有戏」年份）

用神/忌神不由本脚本判定，需由分析阶段人工代入。

用法：
  python3 scripts/hepan.py \
    --a-solar 2007-09-14 --a-hour 20:56 --a-sex 男 --a-role 男 \
    --b-solar 2006-10-30 --b-hour 01:50 --b-sex 男 --b-role 女 \
    --start-year 2022 --end-year 2040
"""

import argparse
import io
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pai_pan as pp  # noqa: E402

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")
except Exception:
    pass

GAN = pp.GAN
ZHI = pp.ZHI
GAN_WUXING = pp.GAN_WUXING          # index-aligned str
CANGGAN = pp.CANGGAN                # zhi -> [(gan, wuxing), ...] 本气在前
TAOHUA = pp.TAOHUA                  # 三合五行 -> 桃花支

SHENG = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}   # 我生
KE = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}      # 我克

# ---- 关系表（无序配对） ----
WUHE_GAN = [("甲", "己"), ("乙", "庚"), ("丙", "辛"), ("丁", "壬"), ("戊", "癸")]
GAN_CHONG = [("甲", "庚"), ("乙", "辛"), ("丙", "壬"), ("丁", "癸")]

LIUHE = [("子", "丑"), ("寅", "亥"), ("卯", "戌"), ("辰", "酉"), ("巳", "申"), ("午", "未")]
LIUCHONG = [("子", "午"), ("丑", "未"), ("寅", "申"), ("卯", "酉"), ("辰", "戌"), ("巳", "亥")]
LIUHAI = [("子", "未"), ("丑", "午"), ("寅", "巳"), ("卯", "辰"), ("申", "亥"), ("酉", "戌")]
PO = [("子", "酉"), ("卯", "午"), ("辰", "丑"), ("寅", "亥"), ("巳", "申"), ("未", "戌")]
SANHE = [("申", "子", "辰"), ("亥", "卯", "未"), ("寅", "午", "戌"), ("巳", "酉", "丑")]
SANHUI = [("寅", "卯", "辰"), ("巳", "午", "未"), ("申", "酉", "戌"), ("亥", "子", "丑")]
XING3 = [("寅", "巳", "申"), ("丑", "未", "戌")]   # 组内两两为刑
ZIMAO = ("子", "卯")
ZIXING = ("辰", "午", "酉", "亥")


def _pair(a, b, table):
    return (a, b) in table or (b, a) in table


def gan_wx(gan):
    return GAN_WUXING[GAN.index(gan)]


def zhi_benqi(zhi):
    return CANGGAN[zhi][0][0]


def shishen(day_gan, other_gan):
    return pp.shishen_of(GAN.index(day_gan), GAN.index(other_gan))


CAT = {
    "比肩": "比劫", "劫财": "比劫",
    "食神": "食伤", "伤官": "食伤",
    "正财": "财", "偏财": "财",
    "正官": "官杀", "偏官": "官杀",
    "正印": "印", "偏印": "印",
}


def ten_god_cat(name):
    return CAT.get(name, name)


def gan_relation(g1, g2):
    if g1 == g2:
        return "同干"
    if _pair(g1, g2, WUHE_GAN):
        return "天干五合"
    if _pair(g1, g2, GAN_CHONG):
        return "天干相冲"
    if KE[gan_wx(g1)] == gan_wx(g2) or KE[gan_wx(g2)] == gan_wx(g1):
        return "天干相克"
    if gan_wx(g1) == gan_wx(g2):
        return "同类五行"
    if SHENG[gan_wx(g1)] == gan_wx(g2):
        return "天干相生(前生后)"
    if SHENG[gan_wx(g2)] == gan_wx(g1):
        return "天干相生(后生前)"
    return "—"


def zhi_relation(z1, z2):
    rels = []
    if z1 == z2:
        rels.append("同支(伏吟)")
        if z1 in ZIXING:
            rels.append("自刑")
        return rels
    if _pair(z1, z2, LIUHE):
        rels.append("地支六合")
    for grp in SANHE:
        if z1 in grp and z2 in grp:
            rels.append("半合(三合缺一)")
            break
    for grp in SANHUI:
        if z1 in grp and z2 in grp:
            rels.append("半会(三会缺一)")
            break
    if _pair(z1, z2, LIUCHONG):
        rels.append("地支六冲")
    if _pair(z1, z2, LIUHAI):
        rels.append("地支六害")
    if _pair(z1, z2, PO):
        rels.append("地支相破")
    for grp in XING3:
        if z1 in grp and z2 in grp:
            rels.append("地支相刑")
            break
    if _pair(z1, z2, [ZIMAO]):
        rels.append("地支相刑(无礼)")
    return rels or ["—"]


def taohua_zhi(zhi):
    for grp, wx in ((("申", "子", "辰"), "水"), (("亥", "卯", "未"), "木"),
                    (("寅", "午", "戌"), "火"), (("巳", "酉", "丑"), "金")):
        if zhi in grp:
            return TAOHUA[wx]
    return None


def five_counts(pillars, hour_unknown):
    """返回 (主气计数, 全藏干计数)。主气＝天干 + 地支本气。"""
    main = {w: 0 for w in "木火土金水"}
    full = {w: 0 for w in "木火土金水"}
    keys = ["year", "month", "day", "hour"]
    for k in keys:
        g, z = pillars[k][0], pillars[k][1]
        if g == "未知" or z == "未知":
            continue
        main[gan_wx(g)] += 1
        full[gan_wx(g)] += 1
        for i, (cg, _wx) in enumerate(CANGGAN[z]):
            full[gan_wx(cg)] += 1
            if i == 0:
                main[gan_wx(cg)] += 1
    return main, full


def strength_estimate(day_gan, pillars, hour_unknown):
    """粗略身强弱：帮身(同五行=比劫 + 生日主=印) 占比。仅供参考。"""
    dwx = gan_wx(day_gan)
    weights = {"year": 1.0, "month": 1.5, "day": 1.2, "hour": 1.0}

    def helps(wx):
        return wx == dwx or SHENG[wx] == dwx

    sup = 0.0
    tot = 0.0
    for k, w in weights.items():
        g, z = pillars[k][0], pillars[k][1]
        if g == "未知" or z == "未知":
            continue
        tot += w
        if helps(gan_wx(g)):
            sup += w
        for i, (cg, _wx) in enumerate(CANGGAN[z]):
            ww = w if i == 0 else w * 0.5
            tot += ww
            if helps(gan_wx(cg)):
                sup += ww
    ratio = sup / tot if tot else 0.0
    if ratio >= 0.62:
        band = "身旺"
    elif ratio >= 0.5:
        band = "偏强"
    elif ratio >= 0.38:
        band = "偏弱"
    else:
        band = "身弱"
    return ratio, band


class Person(object):
    def __init__(self, name, result, role, orientation="异性"):
        self.name = name
        self.result = result
        self.role = role  # 扮演「男」/「女」（仅异性恋用）
        self.orientation = orientation  # 「异性」/「同性」
        p = result["pillars"]
        self.pillars = p
        self.day_gan = p["day"][0]
        self.day_zhi = p["day"][1]
        self.hour_unknown = result["hour_unknown"]
        self.year_zhi = p["year"][1]
        self.main, self.full = five_counts(p, self.hour_unknown)
        self.ratio, self.band = strength_estimate(self.day_gan, p, self.hour_unknown)
        self.tp_y = taohua_zhi(self.year_zhi)
        self.tp_d = taohua_zhi(self.day_zhi)

    def gz_shishen(self, gz):
        g, z = gz[0], gz[1]
        gs = shishen(self.day_gan, g)
        zs = shishen(self.day_gan, zhi_benqi(z))
        return gs, zs

    def cats_of(self, gz):
        gs, zs = self.gz_shishen(gz)
        return {ten_god_cat(gs), ten_god_cat(zs)}, gs, zs

    def want_cat(self):
        # 异性恋：男看财、女看官杀；同性恋：看比劫。
        if self.orientation == "同性":
            return "比劫"
        return "财" if self.role == "男" else "官杀"


def build_person(name, ns, prefix):
    # 解析日期
    solar_date = None
    lunar_display = None
    if getattr(ns, prefix + "solar"):
        solar_date = pp.parse_iso_date(getattr(ns, prefix + "solar"), "--" + prefix + "solar")
    if getattr(ns, prefix + "lunar"):
        ld = pp.parse_iso_date(getattr(ns, prefix + "lunar"), "--" + prefix + "lunar")
        leap = getattr(ns, prefix + "leap")
        converted = pp.lunar_to_solar(ld.year, ld.month, ld.day, leap=leap)
        lunar_display = pp.format_lunar(ld.year, ld.month, ld.day, leap)
        if solar_date is None:
            solar_date = converted
    if solar_date is None:
        raise SystemExit("请至少提供 --%ssolar 或 --%slunar" % (prefix, prefix))

    hour = minute = None
    if getattr(ns, prefix + "hour"):
        hour, minute = pp.parse_hour(getattr(ns, prefix + "hour"))

    result = pp.compute(
        solar_date=solar_date,
        hour=hour,
        minute=minute,
        shichen=getattr(ns, prefix + "shichen"),
        sex=getattr(ns, prefix + "sex"),
        place=getattr(ns, prefix + "place"),
        deceased_year=getattr(ns, prefix + "deceased_year"),
        lunar_display=lunar_display if (getattr(ns, prefix + "lunar") and getattr(ns, prefix + "solar")) else None,
    )
    if getattr(ns, prefix + "lunar") and not getattr(ns, prefix + "solar"):
        result["lunar_text"] = lunar_display
    role = getattr(ns, prefix + "role") or getattr(ns, prefix + "sex")
    orientation = getattr(ns, prefix + "orientation") or "异性"
    return Person(name, result, role, orientation)


def role_desc(p):
    """人类可读的角色 / 配偶星说明。"""
    if p.orientation == "同性":
        return "同性恋｜配偶星看比劫"
    return "异性恋·%s方｜配偶星看%s" % (p.role, p.want_cat())


def fmt_pillars_row(p):
    g = [p["year"][0], p["month"][0], p["day"][0], p["hour"][0]]
    z = [p["year"][1], p["month"][1], p["day"][1], p["hour"][1]]
    s = [p["year"][2], p["month"][2], p["day"][2], p["hour"][2]]
    return g, z, s


def section_person(p):
    out = []
    r = p.result
    out.append("### %s（%s｜%s）" % (p.name, r["sex"], role_desc(p)))
    out.append("- 阳历：%s ｜ 农历：%s" % (r["solar_text"], r["lunar_text"]))
    out.append("- 时辰：%s ｜ 出生地：%s" % (r["shichen_text"], r["place"] or "—"))
    g, z, s = fmt_pillars_row(p.pillars)
    out.append("")
    out.append("| | 年柱 | 月柱 | 日柱 | 时柱 |")
    out.append("|---|---|---|---|---|")
    out.append("| 天干 | %s | %s | %s | %s |" % tuple(g))
    out.append("| 地支 | %s | %s | %s | %s |" % tuple(z))
    out.append("| 十神 | %s | %s | %s | %s |" % tuple(s))
    out.append("")
    out.append("- 日主：%s（%s）" % (p.day_gan, gan_wx(p.day_gan)))
    main = "  ".join("%s%d" % (w, p.main[w]) for w in "木火土金水")
    full = "  ".join("%s%d" % (w, p.full[w]) for w in "木火土金水")
    out.append("- 五行（主气：天干+地支本气）：%s" % main)
    out.append("- 五行（全藏干）：%s" % full)
    out.append("- 身强弱粗估：%s（帮身占比 %.2f，仅供参考，以格局分析为准）" % (p.band, p.ratio))
    out.append("- 桃花位：年支取 %s，日支取 %s" % (p.tp_y or "—", p.tp_d or "—"))
    if r["warnings"]:
        seen = []
        for w in r["warnings"]:
            if w not in seen:
                seen.append(w)
        out.append("- 警告：%s" % "；".join(seen))
    out.append("")
    return out


def section_pillar_pairs(a, b):
    out = []
    out.append("## 四柱逐柱对应")
    out.append("")
    out.append("| 柱 | A | B | 天干关系 | 地支关系 | 提示 |")
    out.append("|---|---|---|---|---|---|")
    names = ["year", "month", "day", "hour"]
    cn = {"year": "年柱", "month": "月柱", "day": "日柱", "hour": "时柱"}
    hint = {
        "year": "双方家长的看法（刑/冲/克/害→家长阻挠）",
        "month": "对当下的影响",
        "day": "婚后的情况（合且为用神→幸福；破→离婚风险；刑→相处不适）",
        "hour": "子女",
    }
    for k in names:
        ag, az = a.pillars[k][0], a.pillars[k][1]
        bg, bz = b.pillars[k][0], b.pillars[k][1]
        if "未知" in (ag, az, bg, bz):
            out.append("| %s | %s%s | %s%s | — | — | %s |" % (cn[k], ag, az, bg, bz, hint[k]))
            continue
        gr = gan_relation(ag, bg)
        zr = "、".join(zhi_relation(az, bz))
        out.append("| %s | %s%s | %s%s | %s | %s | %s |" % (cn[k], ag, az, bg, bz, gr, zr, hint[k]))
    out.append("")
    # 日柱特别提示
    dg = gan_relation(a.pillars["day"][0], b.pillars["day"][0])
    dzr = zhi_relation(a.pillars["day"][1], b.pillars["day"][1])
    flags = []
    if "地支六合" in dzr or "半合(三合缺一)" in dzr or "半会(三会缺一)" in dzr or dg == "天干五合":
        flags.append("夫妻宫/日干见合")
    if "地支相破" in dzr:
        flags.append("日柱相破→需留意婚姻稳定")
    if "地支相刑" in dzr or "地支相刑(无礼)" in dzr:
        flags.append("日柱相刑→相处易不适")
    if "地支六冲" in dzr:
        flags.append("日柱相冲→聚少离多/易起波折")
    if "地支六害" in dzr:
        flags.append("日柱相害→易生嫌隙")
    out.append("> 日柱结论：%s" % ("；".join(flags) if flags else "日柱无明显合/破/刑/冲/害，按十神与用忌关系另断。"))
    out.append("")
    return out


def dayun_ten_god_table(p):
    out = []
    out.append("| 大运序 | 年龄 | 干支 | 干十神 | 支十神 | 类别 | 角色标记 |")
    out.append("|---|---|---|---|---|---|---|")
    want = p.want_cat()
    for seq, ages, gz in p.result["dayun_rows"]:
        if "（小运）" in gz or gz in ("未知",):
            out.append("| %s | %s | %s | — | — | — | — |" % (seq, ages, gz))
            continue
        cats, gs, zs = p.cats_of(gz)
        mark = "★走%s运" % want if want in cats else ""
        out.append("| %s | %s | %s | %s | %s | %s | %s |" % (
            seq, ages, gz, gs, zs, "/".join(sorted(cats)), mark))
    return out


def liunian_rows(a, b, start_year, end_year):
    out = []
    out.append("| 年份 | 干支 | A 干/支十神 | A 类别 | B 干/支十神 | B 类别 | 角色契合 | 桃花 |")
    out.append("|---|---|---|---|---|---|---|---|")
    awant, bwant = a.want_cat(), b.want_cat()
    hits = []
    for y in range(start_year, end_year + 1):
        gz = pp.liunian_gz(y)
        acats, ags, azs = a.cats_of(gz)
        bcats, bgs, bzs = b.cats_of(gz)
        match = (awant in acats) and (bwant in bcats)
        taos = []
        if gz[1] in (a.tp_y, a.tp_d) and a.tp_y:
            taos.append("A桃")
        if gz[1] in (b.tp_y, b.tp_d) and b.tp_y:
            taos.append("B桃")
        if match:
            hits.append((y, gz))
        out.append("| %d | %s | %s/%s | %s | %s/%s | %s | %s | %s |" % (
            y, gz, ags, azs, "/".join(sorted(acats)),
            bgs, bzs, "/".join(sorted(bcats)),
            "★有戏" if match else "",
            "/".join(taos)))
    return out, hits


def liuyue_taohua(a, b, year):
    out = []
    out.append("### %d 年流月桃花引动" % year)
    out.append("")
    for m in range(1, 13):
        gz = pp.liuyue_gz(year, m)
        taos = []
        if a.tp_y and gz[1] == a.tp_y:
            taos.append("A桃")
        if b.tp_y and gz[1] == b.tp_y:
            taos.append("B桃")
        if taos:
            out.append("- %s %s：%s" % (pp.MONTH_CN[m - 1], gz, "、".join(taos)))
    if len(out) == 2:
        out.append("- （无流月命中桃花位）")
    out.append("")
    return out


def build_parser():
    p = argparse.ArgumentParser(description="双人合盘（机械计算部分，无第三方依赖）")
    for pre, label in (("a-", "A（测算者）"), ("b-", "B（对象）")):
        dest = pre.replace("-", "_")
        g = p.add_argument_group(label)
        g.add_argument("--" + pre + "solar", help="阳历 YYYY-MM-DD")
        g.add_argument("--" + pre + "lunar", help="农历 YYYY-MM-DD")
        g.add_argument("--" + pre + "leap", action="store_true", help="农历闰月")
        g.add_argument("--" + pre + "hour", help="出生钟点 HH:MM")
        g.add_argument("--" + pre + "shichen", choices=pp.ZHI_LIST, help="时辰地支")
        g.add_argument("--" + pre + "sex", required=True, choices=("男", "女"), help="生理性别")
        g.add_argument("--" + pre + "role", choices=("男", "女"), help="异性恋角色（默认＝性別）：男=走财运，女=走官杀运")
        g.add_argument("--" + pre + "orientation", choices=("异性", "同性"), help="性取向（默认异性）；同性时配偶星看比劫，role 参数不影响取用")
        g.add_argument("--" + pre + "place", help="出生地")
        g.add_argument("--" + pre + "deceased-year", type=int, dest=dest + "deceased_year", help="已故年份")
    p.add_argument("--start-year", type=int, default=None, help="流年窗口起始年（默认当前年-5）")
    p.add_argument("--end-year", type=int, default=None, help="流年窗口结束年（默认当前年+15）")
    return p


def run(argv=None):
    ns = build_parser().parse_args(argv)
    a = build_person("A（测算者）", ns, "a_")
    b = build_person("B（对象）", ns, "b_")

    from datetime import datetime
    now_year = datetime.now().year
    start = ns.start_year if ns.start_year else now_year - 5
    end = ns.end_year if ns.end_year else now_year + 15

    out = []
    out.append("# 合盘报告（机械部分）")
    out.append("")
    out.append("> 用神/忌神需在分析阶段判定后代入；本报告只给机械关系与身强弱粗估。")
    out.append("")
    out.append("## 双方盘面")
    out.append("")
    out.extend(section_person(a))
    out.extend(section_person(b))

    out.append("## 五行互补（待代入用忌）")
    out.append("")
    out.append("| 盘 | 日主 | 五行主气 | 身强弱粗估 |")
    out.append("|---|---|---|---|")
    for p in (a, b):
        main = "  ".join("%s%d" % (w, p.main[w]) for w in "木火土金水")
        out.append("| %s | %s(%s) | %s | %s(%.2f) |" % (p.name, p.day_gan, gan_wx(p.day_gan), main, p.band, p.ratio))
    out.append("")
    out.append("> 填入用忌后按 rules 判定：")
    out.append("> 1) B 是否含 A 忌神 X 的「财(X所克) + 食伤(X所生)」→ 化解 A 多余；")
    out.append("> 2) A 是否含 B 忌神的「财 + 食伤」→ 化解 B 多余；")
    out.append("> 3) 双方是否互含对方用神 → 天作之合；")
    out.append("> 4) A 是否含 B 忌神多 → A 克 B。")
    out.append("")

    out.extend(section_pillar_pairs(a, b))

    out.append("## 大运对照（配偶星标记：异性男看财 / 女看官杀；同性看比劫）")
    out.append("")
    out.append("**A（%s｜目标%s运）**" % (role_desc(a), a.want_cat()))
    out.append("")
    out.extend(dayun_ten_god_table(a))
    out.append("")
    out.append("**B（%s｜目标%s运）**" % (role_desc(b), b.want_cat()))
    out.append("")
    out.extend(dayun_ten_god_table(b))
    out.append("")

    out.append("## 流年窗口对照（%d–%d）" % (start, end))
    out.append("")
    rows, hits = liunian_rows(a, b, start, end)
    out.extend(rows)
    out.append("")
    if a.orientation == "同性" or b.orientation == "同性":
        out.append("> 规则（同性）：配偶星看**比劫**；两方**同年**比劫均旺 → 「有戏」（可能配偶）。")
    elif a.role == b.role:
        out.append("> 注：双方角色相同（均为「%s方」），经典「男走财 × 女走官杀」配对不成立；此处按「各自踩中自身目标运」近似标注。" % a.role)
    else:
        out.append("> 规则（异性）：男走财运、女走官杀运；两方**同年**分别踩中 → 「有戏」。（四爱与一爱同规则）")
    if hits:
        out.append("**角色契合（同段 A走%s ＆ B走%s）年份：%s**" % (
            a.want_cat(), b.want_cat(), "、".join("%d %s" % (y, gz) for y, gz in hits)))
    else:
        out.append("**窗口内无「A走%s ＆ B走%s」同年重合。**" % (a.want_cat(), b.want_cat()))
    out.append("")

    out.append("## 桃花引动时间线")
    out.append("")
    out.append("- A 桃花位：年支取 %s / 日支取 %s" % (a.tp_y or "—", a.tp_d or "—"))
    out.append("- B 桃花位：年支取 %s / 日支取 %s" % (b.tp_y or "—", b.tp_d or "—"))
    out.append("")
    ay = [str(y) for y in range(start, end + 1) if pp.liunian_gz(y)[1] in (a.tp_y, a.tp_d) and a.tp_y]
    by = [str(y) for y in range(start, end + 1) if pp.liunian_gz(y)[1] in (b.tp_y, b.tp_d) and b.tp_y]
    both = sorted(set(ay) & set(by), key=int)
    out.append("- A 桃花流年：%s" % ("、".join(ay) if ay else "—"))
    out.append("- B 桃花流年：%s" % ("、".join(by) if by else "—"))
    out.append("- **重合年份：%s**" % ("、".join(both) if both else "无"))
    out.append("")
    out.extend(liuyue_taohua(a, b, now_year))

    out.append("## 结语提示")
    out.append("")
    out.append("1. 先在「五行互补」里代入双方用忌，判天作之合 / 单向 / 相克。")
    out.append("2. 再看「角色契合年份」与「桃花引动重合年份」：多且连续 → 高概率在一起且长久；")
    out.append("   若后续某段对不上 → 感情可能没有后续。")
    out.append("3. 最后看四柱逐柱对应（家长 / 当下 / 婚后 / 子女）。")
    out.append("4. 力量层级：大运 ＞ 流年 ＞ 流月；例外（合/会/冲、开库、动用忌）以关系主导。")
    out.append("")

    sys.stdout.write("\n".join(out))
    sys.stdout.write("\n")
    return 0


def main():
    sys.exit(run())


if __name__ == "__main__":
    main()
