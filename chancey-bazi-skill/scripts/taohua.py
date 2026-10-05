# -*- coding: utf-8 -*-
"""桃花 / 配偶星扫描：按性取向确定「配偶星」类别，扫描大运 / 流年 / 流月。

规则（用户设定 2026-10-01）：
- 异性恋（一爱 / 四爱统一）：男看 财，女看 官杀。
- 同性恋（男同 / 女同）：看 比劫；双方在同一时间「比劫旺」→ 才是可能的配偶。
- 双性恋：需先定身份，不在本脚本自动判定范围。
"""

import argparse
import io
import os
import sys
from datetime import date

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pai_pan as pp  # noqa: E402

CATS = {
    "财": ("正财", "偏财"),
    "官杀": ("正官", "偏官"),
    "比劫": ("比肩", "劫财"),
    "印": ("正印", "偏印"),
    "食伤": ("食神", "伤官"),
}
ZHI_SANHE = {
    "申": "水", "子": "水", "辰": "水",
    "亥": "木", "卯": "木", "未": "木",
    "寅": "火", "午": "火", "戌": "火",
    "巳": "金", "酉": "金", "丑": "金",
}


def cat_of(name):
    for k, v in CATS.items():
        if name in v:
            return k
    return name


def want_category(orientation, role):
    """返回 (类别名, 说明)。"""
    o = orientation.strip()
    r = role.strip() if role else ""
    if o in ("异性", "一爱", "四爱", "异性恋"):
        if r == "男":
            return "财", "异性恋·男 → 配偶星看 财（正财=正妻/正缘，偏财=偏缘）"
        if r == "女":
            return "官杀", "异性恋·女 → 配偶星看 官杀（正官=正夫、偏官=偏夫）"
        raise SystemExit("异性恋需指定 --role 男 或 女（一爱与四爱同规则）")
    if o in ("同性", "男同", "女同", "同性恋", "gay", "les"):
        return "比劫", "同性恋 → 配偶星看 比劫（双方同期比劫旺 → 可能配偶）"
    raise SystemExit("请用 --orientation 异性 / 同性；双性恋需先确定身份后手动指定")


def taohua_zhi(zhi):
    return {"水": "酉", "木": "子", "火": "卯", "金": "午"}[ZHI_SANHE[zhi]]


def gz_marks(day_i, gz, cats):
    """返回 (干十神, 本气十神, 干命中, 本气命中, 藏干命中列表)。cats 为十神名集合。"""
    g, z = gz[0], gz[1]
    gs = pp.shishen_of(day_i, pp.GAN.index(g))
    cang = pp.CANGGAN[z]
    zs = pp.shishen_of(day_i, pp.GAN.index(cang[0][0]))
    hit_g = gs in cats
    hit_z = zs in cats
    hidden = [c for c, _w in cang[1:] if pp.shishen_of(day_i, pp.GAN.index(c)) in cats]
    return gs, zs, hit_g, hit_z, hidden


def scan_line(label, gz, day_i, cats):
    gs, zs, hg, hz, hidden = gz_marks(day_i, gz, cats)
    hit = hg or hz or hidden
    mark = " ★" if hit else "  "
    detail = ""
    if hit:
        parts = []
        if hg:
            parts.append(f"干{gs}")
        if hz:
            parts.append(f"支{zs}")
        if hidden:
            parts.append("藏" + "/".join(hidden))
        detail = "  <- " + "、".join(parts)
    return f"{label} {gz}  干={gs} 支={zs}{mark}{detail}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--solar", required=True)
    ap.add_argument("--realtime", action="store_true", help="输入的 --hour 为真太阳时（默认视作北京时间）")
    ap.add_argument("--hour", default=None)
    ap.add_argument("--shichen", default=None)
    ap.add_argument("--sex", required=True)
    ap.add_argument("--place", default=None)
    ap.add_argument("--orientation", required=True, help="异性 / 同性")
    ap.add_argument("--role", default=None, help="异性恋：男/女（一爱与四爱同规则）")
    ap.add_argument("--start", type=int, default=2020)
    ap.add_argument("--end", type=int, default=2045)
    ap.add_argument("--months-year", type=int, default=0, help="额外打印该年 12 流月")
    a = ap.parse_args()

    cat, why = want_category(a.orientation, a.role)
    cats = set(CATS[cat])

    hh, mm = (None, None)
    shichen = a.shichen
    if a.hour:
        hh, mm = pp.parse_hour(a.hour)
    solar = pp.parse_iso_date(a.solar, "--solar")
    res = pp.compute(solar_date=solar, hour=hh, minute=mm,
                     shichen=shichen, sex=a.sex, place=a.place)
    p = res["pillars"]
    day = p["day"][0]
    day_i = pp.GAN.index(day)

    print(f"=== 桃花 / 配偶星扫描 ===")
    print(f"日主：{day}{pp.GAN_WUXING[day_i]}    四柱：" + " ".join(p[k][0] + p[k][1] for k in ["year", "month", "day", "hour"]))
    print(f"判定：{why}")
    print()

    # 原局配偶星显现
    print(f"== 原局「{cat}」显现情况 ==")
    for k, nm in [("year", "年"), ("month", "月"), ("day", "日"), ("hour", "时")]:
        g, z = p[k][0], p[k][1]
        gs = pp.shishen_of(day_i, pp.GAN.index(g))
        cang = pp.CANGGAN[z]
        zs = pp.shishen_of(day_i, pp.GAN.index(cang[0][0]))
        flags = []
        if gs in cats:
            flags.append(f"干{gs}")
        if zs in cats:
            flags.append(f"本气{zs}")
        for c, _w in cang[1:]:
            if pp.shishen_of(day_i, pp.GAN.index(c)) in cats:
                flags.append(f"藏{c}")
        print(f"  {nm}柱 {g}{z}：{('、'.join(flags)) if flags else '—'}")
    print()

    # 桃花位
    ty = taohua_zhi(p["year"][1])
    td = taohua_zhi(p["day"][1])
    zhis = {p["year"][1], p["month"][1], p["day"][1], p["hour"][1]}
    print(f"== 桃花位 ==")
    print(f"  年支{p['year'][1]}({ZHI_SANHE[p['year'][1]]}) → 桃花位 {ty}；日支{p['day'][1]}({ZHI_SANHE[p['day'][1]]}) → 桃花位 {td}")
    present = [z for z in (ty, td) if z in zhis]
    print(f"  原局地支 {''.join(p[k][1] for k in ['year','month','day','hour'])} → " +
          (f"已见桃花位 {'/'.join(present)}" if present else "原局无桃花位，属潜伏型"))
    print()

    print(f"== 大运（★＝走{cat}）==")
    for seq, ages, gz in res["dayun_rows"]:
        if "小运" in gz:
            print(f"  {ages:<14} {gz}（起运前）")
            continue
        print("  " + scan_line(f"{seq} {ages:<12}", gz, day_i, cats))
    print()

    print(f"== 流年 {a.start}-{a.end}（★＝走{cat}）==")
    for y in range(a.start, a.end + 1):
        print("  " + scan_line(str(y), pp.liunian_gz(y), day_i, cats))
    print()

    if a.months_year:
        y = a.months_year
        print(f"== {y} 流月（★＝走{cat}）==")
        for m in range(1, 13):
            print("  " + scan_line(f"{pp.MONTH_CN[m-1]:<3}", pp.liuyue_gz(y, m), day_i, cats))


if __name__ == "__main__":
    main()
