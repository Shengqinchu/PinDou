#!/usr/bin/env python3
"""Generate Task I curated public-web research artifacts.

This script intentionally records only public URLs, short summaries, and
structured observations. It does not download or persist third-party images,
KOL note bodies, private comments, seller contacts, or logged-in data.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "01_research" / "colormap_china"
COLORMAP = ROOT / "01_research" / "colormap"
CAPTURED_AT = "2026-05-24"


XHS_KEYWORDS = [
    "拼豆色卡",
    "拼豆品牌对比",
    "MARD 色卡",
    "COCO 色卡",
    "Artkal 色卡",
    "拼豆新色",
    "拼豆人像",
    "拼豆宠物",
    "拼豆情侣",
    "拼豆图纸",
    "Q版拼豆",
    "chibi 拼豆",
    "拼豆熨烫翻车",
    "拼豆色差",
]

PUBLIC_MENTION_ROWS = [
    {
        "platform": "xhs",
        "url": "https://www.xiaohongshu.com/search_result?keyword=%E6%8B%BC%E8%B1%86%E8%89%B2%E5%8D%A1",
        "query": "拼豆色卡",
        "record_kind": "search_entry",
        "title": "拼豆色卡 - 小红书搜索",
        "author_display": "",
        "visible_date": "",
        "likes_visible": "",
        "brand_mentions": "MARD;COCO;Artkal;漫漫;盼盼;咪小窝",
        "color_code_mentions": "",
        "size_mentions": "2.6mm;5mm",
        "alias_mentions": "色卡;色号",
        "issue_mentions": "manual_app_collection_required",
        "tool_mentions": "",
        "supply_mentions": "",
        "sampling_status": "public_search_entry_only",
        "notes": "Public Web search page is accessible, but SSR feeds are empty; full cards/comments require App/manual review.",
    },
    {
        "platform": "xhs",
        "url": "https://www.xiaohongshu.com/search_result?keyword=MARD%E8%89%B2%E5%8D%A1",
        "query": "MARD色卡",
        "record_kind": "search_entry",
        "title": "MARD色卡 - 小红书搜索",
        "author_display": "",
        "visible_date": "",
        "likes_visible": "",
        "brand_mentions": "MARD",
        "color_code_mentions": "221;291",
        "size_mentions": "2.6mm",
        "alias_mentions": "基础色;扩展色",
        "issue_mentions": "manual_app_collection_required",
        "tool_mentions": "",
        "supply_mentions": "hot_colors_need_review",
        "sampling_status": "public_search_entry_only",
        "notes": "Use as App/manual queue for MARD 221 vs 291, substitute colours, and shortage notes.",
    },
    {
        "platform": "xhs",
        "url": "https://www.xiaohongshu.com/search_result?keyword=COCO%E8%89%B2%E5%8D%A1%20%E6%8B%BC%E8%B1%86",
        "query": "COCO色卡 拼豆",
        "record_kind": "search_entry",
        "title": "COCO色卡 拼豆 - 小红书搜索",
        "author_display": "",
        "visible_date": "",
        "likes_visible": "",
        "brand_mentions": "COCO",
        "color_code_mentions": "291",
        "size_mentions": "2.6mm",
        "alias_mentions": "COCO家",
        "issue_mentions": "manual_app_collection_required",
        "tool_mentions": "",
        "supply_mentions": "",
        "sampling_status": "public_search_entry_only",
        "notes": "Manual review should verify COCO single-colour pack naming and B-series mentions.",
    },
    {
        "platform": "xhs",
        "url": "https://www.xiaohongshu.com/search_result?keyword=Artkal%E8%89%B2%E5%8D%A1%20%E6%8B%BC%E8%B1%86",
        "query": "Artkal色卡 拼豆",
        "record_kind": "search_entry",
        "title": "Artkal色卡 拼豆 - 小红书搜索",
        "author_display": "",
        "visible_date": "",
        "likes_visible": "",
        "brand_mentions": "Artkal",
        "color_code_mentions": "C;M;S",
        "size_mentions": "2.6mm;5mm",
        "alias_mentions": "小豆;mini",
        "issue_mentions": "manual_app_collection_required",
        "tool_mentions": "",
        "supply_mentions": "",
        "sampling_status": "public_search_entry_only",
        "notes": "Manual review should compare Artkal mini adoption for portrait/pet works.",
    },
    {
        "platform": "xhs",
        "url": "https://www.xiaohongshu.com/search_result?keyword=%E7%86%A8%E7%83%AB%E7%BF%BB%E8%BD%A6%20%E6%8B%BC%E8%B1%86",
        "query": "熨烫翻车 拼豆",
        "record_kind": "search_entry",
        "title": "熨烫翻车 拼豆 - 小红书搜索",
        "author_display": "",
        "visible_date": "",
        "likes_visible": "",
        "brand_mentions": "MARD;COCO;Artkal",
        "color_code_mentions": "",
        "size_mentions": "2.6mm;5mm",
        "alias_mentions": "翻车;过熔;翘边",
        "issue_mentions": "over_melt;warping;uneven_fusion;color_shift",
        "tool_mentions": "",
        "supply_mentions": "",
        "sampling_status": "public_search_entry_only",
        "notes": "High-priority manual queue for physical-vs-screen colour and ironing risk observations.",
    },
    {
        "platform": "xhs",
        "url": "https://www.xiaohongshu.com/user/profile/65f420e30000000005008498",
        "query": "拼豆工具",
        "record_kind": "public_profile_card",
        "title": "闷香红烧鱼 - 拼豆工具相关公开主页",
        "author_display": "闷香红烧鱼",
        "visible_date": "",
        "likes_visible": "single card up to 2万 visible in public profile snippets",
        "brand_mentions": "MARD;COCO;漫漫;盼盼;咪小窝",
        "color_code_mentions": "",
        "size_mentions": "",
        "alias_mentions": "色卡;色号;拼豆草图",
        "issue_mentions": "tooling_need",
        "tool_mentions": "pindou-draw",
        "supply_mentions": "",
        "sampling_status": "public_profile_visible",
        "notes": "Public profile shows tool-topic demand; full note text/comments require App/manual review.",
    },
    {
        "platform": "bilibili",
        "url": "https://www.bilibili.com/video/BV1vY4y1M7uo/",
        "query": "COCO拼豆色号",
        "record_kind": "video",
        "title": "COCO拼豆星之卡比色号分享",
        "author_display": "COCO手工店",
        "visible_date": "2022-09-07",
        "likes_visible": "86",
        "brand_mentions": "COCO",
        "color_code_mentions": "IP图纸色号分享",
        "size_mentions": "2.6mm",
        "alias_mentions": "星之卡比",
        "issue_mentions": "color_recipe_content",
        "tool_mentions": "",
        "supply_mentions": "",
        "sampling_status": "public_video_metadata",
        "notes": "B站 title/metadata confirms colour-number sharing content format.",
    },
    {
        "platform": "tieba",
        "url": "https://tieba.baidu.com/p/5857134458",
        "query": "拼豆对应色卡",
        "record_kind": "forum_thread",
        "title": "求拼豆对应色卡？",
        "author_display": "公开贴吧用户",
        "visible_date": "2018-08-27",
        "likes_visible": "",
        "brand_mentions": "MARD;漫漫家;咪小窝",
        "color_code_mentions": "对应卡",
        "size_mentions": "",
        "alias_mentions": "三家色号通用",
        "issue_mentions": "cross_brand_mapping_need",
        "tool_mentions": "",
        "supply_mentions": "",
        "sampling_status": "public_forum_thread",
        "notes": "Early Chinese community evidence for cross-brand mapping demand.",
    },
]

SKU_ROWS = [
    [1, "MARD", 2.6, "Mard 标准 221 色套装", 221, "每色约1000颗", 239, "拼豆工具站", "", "公开购买页", "https://www.pindou.online/shop", "high"],
    [2, "MARD", 2.6, "MARD 221 色色卡/体系", 221, "", "", "拼豆工具站", "", "221/291 色体系证据", "https://www.pindou.online/colors", "high"],
    [3, "MARD", 2.6, "MARD 291 全色体系", 291, "", "", "拼豆王国", "", "称国内最受欢迎", "https://pindou.skin/colors.html", "medium"],
    [4, "MARD/黄豆豆", 2.6, "全色融合豆补充包高品质 221", 221, "", 13.5, "拼多多公开 H5", "", "Top.7", "https://mobile.yangkeduo.com/poros/h5?_dr_sku_id=1787113130706&goods_id=819597985495", "medium"],
    [5, "MARD/黄豆豆", 2.6, "221 全色系补充包", 221, "", 2.3, "拼多多公开 H5", "", "Top.1", "https://mobile.yangkeduo.com/poros/h5?_dr_sku_id=1806961892863&goods_id=846035460137", "medium"],
    [6, "MARD", 2.6, "融合豆 221 色套装", 221, "", 195, "拼多多公开 H5", "", "Top.1", "https://mobile.yangkeduo.com/poros/h5?_dr_sku_id=1792760587528&goods_id=826919357447", "medium"],
    [7, "MARD/黄豆豆", 2.6, "效融全色系现货补充包", "", "", 149.9, "拼多多公开 H5", "", "Top.2", "https://mobile.yangkeduo.com/poros/h5?_dr_sku_id=1792760587528&goods_id=826919357447", "medium"],
    [8, "MARD", 2.6, "221 色补充包 1000 粒", 221, "约1000粒/色", 199, "拼多多公开 H5", "", "Top.3", "https://mobile.yangkeduo.com/poros/h5?_dr_sku_id=1792760587528&goods_id=826919357447", "medium"],
    [9, "MARD", 2.6, "221 色融合豆材料补充包", 221, "", 106, "拼多多公开 H5", "", "Top.4", "https://mobile.yangkeduo.com/poros/h5?_dr_sku_id=1792760587528&goods_id=826919357447", "medium"],
    [10, "MARD", 2.6, "拼豆豆 221 色同色系套装", 221, "", 178.6, "拼多多公开 H5", "", "Top.5", "https://mobile.yangkeduo.com/poros/h5?_dr_sku_id=1792760587528&goods_id=826919357447", "medium"],
    [11, "MARD", 2.6, "221 色套装小豆补充装", 221, "", 129.9, "拼多多公开 H5", "", "Top.7", "https://mobile.yangkeduo.com/poros/h5?_dr_sku_id=1792760587528&goods_id=826919357447", "medium"],
    [12, "MARD/黄豆豆", 2.6, "221 全色套装", 221, "", 82.5, "拼多多公开 H5", "", "Top.8", "https://mobile.yangkeduo.com/poros/h5?_dr_sku_id=1792760587528&goods_id=826919357447", "medium"],
    [13, "MARD/黄豆豆", 2.6, "221 全色补充包高品质", 221, "", 128, "拼多多公开 H5", "", "Top.9", "https://mobile.yangkeduo.com/poros/h5?_dr_sku_id=1792760587528&goods_id=826919357447", "medium"],
    [14, "Labby/其他", 2.6, "221 色补充包", 221, "每包10g约1000粒", 256.22, "拼多多公开 H5", "", "Top.11", "https://mobile.yangkeduo.com/poros/h5?_dr_sku_id=1792760587528&goods_id=826919357447", "low"],
    [15, "MARD/黄豆豆", 2.6, "264 色袋装+方盒+收纳盒", 264, "", "", "京东公开价格页", "", "4+条评论", "https://www.jd.com/jiage/6233979f9d4bdf6e2ee7.html", "medium"],
    [16, "MARD/黄豆豆", 2.6, "240 色袋装+方盒+收纳盒", 240, "", "", "京东公开价格页", "", "4+条评论", "https://www.jd.com/jiage/6233979f9d4bdf6e2ee7.html", "medium"],
    [17, "MARD/黄豆豆", 2.6, "216 色袋装+方盒+收纳盒", 216, "", "", "京东公开价格页", "", "4+条评论", "https://www.jd.com/jiage/6233979f9d4bdf6e2ee7.html", "medium"],
    [18, "MARD/黄豆豆", 2.6, "192 色袋装+方盒+收纳盒", 192, "", "", "京东公开价格页", "", "4+条评论", "https://www.jd.com/jiage/6233979f9d4bdf6e2ee7.html", "medium"],
    [19, "MARD/黄豆豆", 2.6, "24 色袋装+方盒+收纳盒", 24, "", "", "京东公开价格页", "", "4+条评论", "https://www.jd.com/jiage/6233979f9d4bdf6e2ee7.html", "medium"],
    [20, "通用/MARD/DODO/黄豆豆", 2.6, "黑白透明救急补充包 H1 透色", "", "50g约5000粒", "", "京东公开价格页", "", "6+条评论", "https://www.jd.com/jiage/6233979f9d4bdf6e2ee7.html", "medium"],
    [21, "黄豆豆/DODO/优肯/MARD", 2.6, "豪华全套 96 色", 96, "48000颗", "", "京东公开价格页", "", "3+条评论", "https://www.jd.com/jiage/6233979f9d4bdf6e2ee7.html", "medium"],
    [22, "COCO/黄豆豆/MARD", 2.6, "142 件套五大盒+熨斗+工具", "", "50000颗", "", "京东公开价格页", "", "100+条评论", "https://www.jd.com/jiage/6233979f9d4bdf6e2ee7.html", "medium"],
    [23, "COCO/黄豆豆/MARD", 2.6, "彩色补充豆+收纳盒", "", "", "", "京东公开价格页", "", "100+条评论", "https://www.jd.com/jiage/6233979f9d4bdf6e2ee7.html", "medium"],
    [24, "COCO/黄豆豆/MARD", 2.6, "69 件套两大盒+熨斗+工具", "", "20000颗", "", "京东公开价格页", "", "4+条评论", "https://www.jd.com/jiage/6233979f9d4bdf6e2ee7.html", "medium"],
    [25, "MARD/黄豆豆", 2.6, "24 色盒装 13000 颗", 24, "13000颗", "", "京东公开价格页", "", "100+评价", "https://www.jd.com/jiage/6233979f9d4bdf6e2ee7.html", "medium"],
    [26, "COCO", 2.6, "B 系列补充包", "", "", "0.41-1.29", "淘宝镜像/COCOの手工店", "", "月销量100+", "https://tao.hooos.com/goods_g3wWVBGh3t2WX7QgVgTooVCatr-PNzeejCOoZKrP5yCG.html", "low"],
    [27, "COCO", 2.6, "COCO 手工店单色补充包", "", "10g约1000粒", 1.4, "新华社报道/电商线索", "", "补充包已售超百万线索", "https://www.news.cn/fashion/20260225/241777a19d884756b8a1769c4475db02/c.html", "medium"],
    [28, "婆娑/其他", 2.6, "24 色基础套装带工具", 24, "每色约500粒", 25.8, "新华社报道/电商线索", "", "热门色抢购线索", "https://www.news.cn/fashion/20260225/241777a19d884756b8a1769c4475db02/c.html", "medium"],
    [29, "咪小窝", 2.6, "单色包补充包", "", "", "", "淘宝镜像/咪小窝拼豆", "", "月销量7万+", "https://tao.hooos.com/goods_523138769220.html", "low"],
    [30, "DODO", 2.6, "72 色小豆套装不含熨斗", 72, "", "", "京东型号页", "", "型号页收录", "https://www.jd.com/xinghao/69946c1c367310327021.html", "medium"],
    [31, "DODO", 2.6, "A/H/F/B/C/D/E/G/M 系列单色补充", "", "", "", "京东型号页", "", "型号页收录", "https://www.jd.com/xinghao/69946c1c367310327021.html", "medium"],
    [32, "无品牌/工厂货", 2.6, "221 色补充包 MARD 同色号", 221, "1000颗/色选项", "", "1688镜像", "", "浙江金华属性页", "https://www.btomejp.com/alibaba/product/992073082662", "low"],
    [33, "无品牌/工厂货", 2.6, "304 全色系补充包", 304, "1000粒", 167, "1688镜像", "", "关联商品价", "https://www.btomejp.com/alibaba/product/992073082662", "low"],
    [34, "COCO/MARD 兼容", 2.6, "DIY 材料包补充包", "", "", 179, "1688镜像", "", "关联商品价", "https://www.btomejp.com/alibaba/product/992073082662", "low"],
    [35, "MARD/黄豆豆/DODO/小舞/COCO", 2.6, "同款货源小豆补充包", "", "", 174, "1688镜像", "", "关联商品价", "https://www.btomejp.com/alibaba/product/992073082662", "low"],
    [36, "Artkal", 2.6, "Artkal Mini C 系列", "100+", "", "8-15/袋参考价", "公开评测/渠道线索", "", "正规店较多", "https://www.pindou.online/blog/artkal-vs-hama-pin-dou-cai-liao-dui-bi", "medium"],
]

COMPETITOR_ROWS = [
    ["拼豆星球", "web/app", "MARD likely", "5mm/2.6mm unclear", "yes", "MARD;COCO;ManMan;PanPan;MiXiaoWo;custom", "291/221/144/120 visible", "not disclosed", "download pattern; grid; color count", "国产色卡覆盖最强，需真机确认默认品牌和导出格式", "https://pindou.cn/"],
    ["拼豆大师 Pro / 365-tools", "web", "Perler", "5mm/Midi implied", "not visible", "Perler", "unknown", "Perler standard color chart", "PDF", "偏单品牌施工图纸工具", "https://365-tools.cn/detail/40"],
    ["德虎造物", "web", "MARD likely", "unknown", "yes", "MARD;COCO;漫漫;盼盼;咪小窝", "public summary says 295", "not disclosed", "multi-format export", "国产五色卡覆盖强，动态工作台需实测", "https://dehumaker.cn/"],
    ["MakeBead", "web", "Perler Midi", "5mm", "yes", "Perler;Hama;Artkal S-5mm;Nabbi BioBeads", "103;92;199;30", "beadcolors community MIT", "PNG;PDF", "公开说明完整，品牌切换清楚", "https://makebead.com/"],
    ["Bitbead", "web", "language-dependent, often Perler", "mixed", "yes", "Perler;Hama;Artkal;Artkal Mini;MARD 221/291", "117;89;176;221;291", "own HEX tables with equivalents; CIEDE2000", "PNG;PDF", "MARD 覆盖好但不含 COCO/漫漫等国产卡", "https://bitbead.pomodiary.com/en"],
    ["BeadMapper", "web", "Perler", "unknown", "yes", "Perler;Mard;Artkal A;Hama;Nabbi", "102;291;145;80;30", "official bead color codes claimed", "Export", "本地处理，MARD 有但 COCO/漫漫缺失", "https://www.beadmapper.com/"],
    ["BeadPattern", "web", "unknown", "unknown", "yes", "MARD;COCO;Artkal;Perler;Hama", "unknown", "thanks Zippland/perler-beads Apache 2.0", "PDF;shopping list", "国产到 MARD/COCO，缺漫漫/盼盼/咪小窝", "https://beadpattern.net/about"],
    ["拼豆像素化助手 metamo", "web", "MARD", "unknown", "yes", "MARD;COCO;漫漫;盼盼;咪小窝", "unknown", "not disclosed", "CSV;color-number system list", "公开页面直接展示色号系统选择", "https://pindou.metamo.cn/"],
]


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_sku_csv() -> None:
    fields = [
        "id",
        "brand",
        "bead_diameter_mm",
        "sku_name",
        "color_count",
        "pack_count_per_color",
        "price_cny",
        "platform",
        "shop_name",
        "sales_or_heat_signal",
        "url",
        "confidence",
        "captured_at",
    ]
    rows = [
        {
            "id": row[0],
            "brand": row[1],
            "bead_diameter_mm": row[2],
            "sku_name": row[3],
            "color_count": row[4],
            "pack_count_per_color": row[5],
            "price_cny": row[6],
            "platform": row[7],
            "shop_name": row[8],
            "sales_or_heat_signal": row[9],
            "url": row[10],
            "confidence": row[11],
            "captured_at": CAPTURED_AT,
        }
        for row in SKU_ROWS
    ]
    rows.extend(fetch_jd_public_sku_rows(start_id=len(rows) + 1))
    write_csv(OUT / "bead_skus_cn.csv", fields, rows)


def infer_brand(title: str) -> str:
    hits = []
    for brand in ["MARD", "COCO", "DODO", "黄豆豆", "小舞", "Artkal", "婆娑"]:
        if brand.lower() in title.lower():
            hits.append(brand)
    if not hits and "mard" in title.lower():
        hits.append("MARD")
    return "/".join(dict.fromkeys(hits)) or "通用/店铺自有"


def infer_diameter(title: str) -> float | str:
    if "10mm" in title.lower() or "10MM" in title:
        return 10.0
    if "5mm" in title.lower() or "5MM" in title:
        return 5.0
    if "2.6mm" in title.lower() or "2.6MM" in title:
        return 2.6
    return 2.6 if any(word in title for word in ["小豆", "融合豆", "补充包"]) else ""


def infer_color_count(title: str) -> str:
    match = re.search(r"(\d{2,3})色", title)
    return match.group(1) if match else ""


def infer_pack_count(title: str) -> str:
    patterns = [r"约?(\d+(?:\.\d+)?[万千]?[颗粒])", r"(\d+)g", r"(\d+\.?\d*w颗)"]
    for pattern in patterns:
        match = re.search(pattern, title, flags=re.I)
        if match:
            return match.group(1)
    return ""


def fetch_jd_public_sku_rows(start_id: int) -> list[dict[str, object]]:
    urls = [
        "https://www.jd.com/jiage/6233979f9d4bdf6e2ee7.html",
        "https://www.jd.com/jiage/69946c1c367310327021.html",
    ]
    rows: list[dict[str, object]] = []
    seen: set[str] = set()
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0"}
    for url in urls:
        try:
            html = requests.get(url, headers=headers, timeout=30).text
        except requests.RequestException:
            continue
        soup = BeautifulSoup(html, "html.parser")
        for div in soup.select(".pad-sku"):
            anchor = div.select_one(".p-name a") or div.select_one("a.price-href") or div.select_one("a[title]")
            if anchor is None:
                continue
            title = (anchor.get("title") or anchor.get_text(" ", strip=True)).strip()
            href = anchor.get("href") or url
            if not title or "拼豆" not in title:
                continue
            if href in seen:
                continue
            seen.add(href)
            comments = ""
            comment_node = div.select_one(".comment-num strong")
            if comment_node is not None:
                comments = f"{comment_node.get_text(strip=True)}条评论"
            rows.append(
                {
                    "id": start_id + len(rows),
                    "brand": infer_brand(title),
                    "bead_diameter_mm": infer_diameter(title),
                    "sku_name": title,
                    "color_count": infer_color_count(title),
                    "pack_count_per_color": infer_pack_count(title),
                    "price_cny": "",
                    "platform": "京东公开价格/型号页",
                    "shop_name": "",
                    "sales_or_heat_signal": comments,
                    "url": href if href.startswith("http") else f"https:{href}",
                    "confidence": "medium",
                    "captured_at": CAPTURED_AT,
                }
            )
    return rows


def write_xhs_files() -> None:
    fields = [
        "platform",
        "url",
        "query",
        "record_kind",
        "title",
        "author_display",
        "visible_date",
        "likes_visible",
        "brand_mentions",
        "color_code_mentions",
        "size_mentions",
        "alias_mentions",
        "issue_mentions",
        "tool_mentions",
        "supply_mentions",
        "sampling_status",
        "notes",
    ]
    rows = []
    rows.extend(PUBLIC_MENTION_ROWS)
    # Add transparent manual-collection queue rows; these are not counted as collected mentions.
    for keyword in XHS_KEYWORDS:
        for sort in ["综合", "最热", "最新"]:
            rows.append(
                {
                    "platform": "xhs",
                    "url": f"https://www.xiaohongshu.com/search_result?keyword={keyword.replace(' ', '%20')}",
                    "query": keyword,
                    "record_kind": "manual_app_queue",
                    "title": f"{keyword} / {sort} / App人工补采",
                    "author_display": "",
                    "visible_date": "",
                    "likes_visible": "",
                    "brand_mentions": "",
                    "color_code_mentions": "",
                    "size_mentions": "",
                    "alias_mentions": "",
                    "issue_mentions": "",
                    "tool_mentions": "",
                    "supply_mentions": "",
                    "sampling_status": "manual_app_required_not_collected",
                    "notes": "Use in XHS App: record public title, visible engagement, brand/code/alias/issues; do not save images, comments with personal info, or long text.",
                }
            )
    write_csv(OUT / "xhs_color_mentions.csv", fields, rows)

    template_fields = [
        "sample_id",
        "keyword",
        "sort",
        "rank",
        "xhs_url",
        "author_display",
        "title_summary",
        "likes_visible",
        "favorites_visible",
        "comments_visible",
        "brand_mentions",
        "color_code_mentions",
        "alias_mentions",
        "issue_mentions",
        "notes_no_long_quotes",
    ]
    template_rows = []
    sorts = ["综合", "最热", "最新", "高赞色卡"]
    idx = 1
    for keyword in XHS_KEYWORDS:
        for sort in sorts:
            for rank in range(1, 5):
                template_rows.append(
                    {
                        "sample_id": f"XHS-{idx:03d}",
                        "keyword": keyword,
                        "sort": sort,
                        "rank": rank,
                        "xhs_url": "",
                        "author_display": "",
                        "title_summary": "",
                        "likes_visible": "",
                        "favorites_visible": "",
                        "comments_visible": "",
                        "brand_mentions": "",
                        "color_code_mentions": "",
                        "alias_mentions": "",
                        "issue_mentions": "",
                        "notes_no_long_quotes": "",
                    }
                )
                idx += 1
    write_csv(OUT / "xhs_manual_collection_template.csv", template_fields, template_rows[:224])


def write_aliases_and_status() -> None:
    mard_rows = json.loads((COLORMAP / "mard_5mm.json").read_text(encoding="utf-8"))
    category_alias = {
        "白色系": ["白色", "奶白", "雪白"],
        "灰色系": ["灰色", "浅灰", "水泥灰"],
        "黑色系": ["黑色", "纯黑", "描边黑"],
        "黄色系": ["黄色", "奶黄", "鹅黄"],
        "橙色系": ["橙色", "橘色", "暖橙"],
        "红色系": ["红色", "正红", "深红"],
        "粉色系": ["粉色", "浅粉", "腮红粉"],
        "紫色系": ["紫色", "薰衣草紫", "深紫"],
        "蓝色系": ["蓝色", "天蓝", "深蓝"],
        "青色系": ["青色", "湖蓝", "薄荷蓝"],
        "绿色系": ["绿色", "草绿", "薄荷绿"],
    }
    aliases = []
    for row in mard_rows[:120]:
        base = category_alias.get(row["category"], [row["category"]])
        aliases.append(
            {
                "brand": "MARD",
                "code": row["code"],
                "official_name": row["name_en"],
                "aliases_cn": list(dict.fromkeys([base[0], base[1] if len(base) > 1 else base[0], f"MARD {row['code']}", f"{row['code']}号"])),
                "alias_sources": [
                    "https://www.pindou.online/colors",
                    "https://www.pixel-pattern.com/color-converter",
                    "xhs_manual_collection_template.csv",
                ],
                "confidence": "proposal_pending_cn_community_validation",
            }
        )
    (OUT / "chinese_color_aliases.json").write_text(
        json.dumps(aliases, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    status_rows = []
    for row in mard_rows[:50]:
        status = "active"
        evidence = "MARD 221/291 public palette and multiple 2.6mm SKU signals."
        if row["code"] == "H2":
            status = "low_stock"
            evidence = "Public report/subagent note: H2 mentioned as recently hard to buy; requires manual shop verification."
        if str(row["code"]).startswith(("P", "Q", "R", "T", "Y", "ZG")):
            status = "new_release"
            evidence = "MARD 291 expansion series beyond 221 baseline."
        status_rows.append(
            {
                "brand": "MARD",
                "bead_diameter_mm": 2.6,
                "code": row["code"],
                "china_market_status": status,
                "confidence": "medium" if status != "low_stock" else "low",
                "evidence": evidence,
            }
        )
    # Add selected non-MARD family-level entries.
    for brand, code, status, evidence in [
        ("COCO", "B-series", "active", "Taobao mirror and public tool support; exact per-colour availability needs shop verification."),
        ("黄豆豆", "291", "active", "PDD/JD public SKU signals often pair 黄豆豆 with MARD."),
        ("咪小窝", "290", "active", "Taobao mirror reports high monthly sales for single-colour packs."),
        ("DODO", "72/series", "active", "JD model pages list DODO 72-colour set and A/H/F/B/C/D/E/G/M single-colour series."),
        ("MARD", "P/Q/R/T/Y/ZG", "new_release", "291 expansion series visible in public colour tools."),
    ]:
        status_rows.append(
            {
                "brand": brand,
                "bead_diameter_mm": 2.6,
                "code": code,
                "china_market_status": status,
                "confidence": "medium",
                "evidence": evidence,
            }
        )
    (OUT / "china_market_status_overrides.json").write_text(
        json.dumps(status_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def write_markdown_files() -> None:
    (OUT / "xhs_kol_preferences.md").write_text(
        """# 小红书拼豆 KOL 偏好初判

> 口径：未登录公开 Web + 搜索入口 + 公开主页卡片线索。完整 200 篇样本需要用户 App 内人工补采，模板见 `xhs_manual_collection_template.csv`。

## 初步结论

- 高互动内容集中在工具、图纸、熨烫避坑、收纳、宠物 / 人像 / Q版 / IP 角色。
- “色号分享”通常绑定具体图纸或 IP，而不是抽象色卡。PinDou 内容运营更适合发“作品 + 色号 + 可拼尺寸 + 翻车避坑”。
- “翻车 / 避坑”是强需求：熨烫过度、翘边、散架、色差、混豆、收纳错色。
- MARD 是中文圈最强基础口径，221 / 291 必须分开；COCO 更像店铺/社区入口；Artkal 适合强调 Mini 2.6mm 和高精度人像/宠物。
- 漫漫家、咪小窝、卡卡家、盼盼拼豆是中文工具和用户语境里不可忽视的别名/店铺型品牌。

## Top 20 人工复核方向

1. 闷香红烧鱼：工具型内容，公开主页可见拼豆草图/色卡管理相关标题。
2. 小小拼豆豆：工具/教程账号线索。
3. N.B.Rice：拼豆专门店、颜色墙、自助称豆。
4. Rebirth、汀海我跟你拼了：过程记录、长时间拼图心流内容。
5. Rolling、小山田心、开心鱼头、亲故：熨烫翻车复盘方向。
6. 伊丽虾白、moonmong、Aède、eleven：二次元/谷美/无料场景。
7. 一颗豆豆子、蒸汽友啵啵、Synmo梦：装备、豆铲、烫豆机、收纳。

这些账号只记录公开昵称和内容类型；不要保存联系方式、二维码、私信信息或原图。
""",
        encoding="utf-8",
    )

    (OUT / "brand_popularity_cn.md").write_text(
        """# 国内拼豆品牌热度初判

> 证据来自公开电商线索、工具支持、中文社区样本；淘宝/1688 原站登录限制较强，销量字段以公开摘要/镜像/报道为低到中置信线索。

| 排名 | 品牌 | 热度 | 依据 |
|------|------|------|------|
| 1 | MARD | 最高 | 221/291 色体系被工具广泛采用；公开报道与 PDD/JD/SKU 线索集中；中文用户认知最强 |
| 2 | COCO | 高 | 工具支持较多；淘宝镜像与报道有单色补充包、B 系列、百万级补充包线索 |
| 3 | 黄豆豆 | 中高 | PDD/JD 常与 MARD 并列；性价比/全色套装线索多 |
| 4 | DODO | 中高 | JD 型号页与公开选购文中频繁出现，常作平替/同源体系 |
| 5 | 咪小窝 | 中 | 工具支持 + 淘宝镜像高月销线索，但独立公开证据集中 |
| 6 | 漫漫 / ManMan | 中 | 拼豆星球、德虎造物、metamo 等工具支持；商品页公开证据不足 |
| 7 | 盼盼 / PanPan | 中低到中 | 工具支持和老教程存在，电商 SKU 证据较弱 |
| 8 | Artkal | 中 | 国产国际品牌，2.6mm Mini 强；本次国内 SKU/销量线索少于 MARD/COCO/黄豆豆 |
| 9 | 优肯 / 小舞 / 婆娑 / Labby / 白牌工厂货 | 低到中 | 多为套装或工厂货线索，品牌一致性和色号体系需要人工验证 |

## 对 Task H 的校准

- Task H 缺少 `漫漫 / ManMan` 独立输出，这是中文工具常见色卡，Phase 1 前应补一个 `manman_5mm/2_6mm` 或确认与现有 `other_*` 的映射。
- MARD 2.6mm 比 MARD 5mm 更符合国内电商 SKU 线索；但产品默认仍可先保留 MARD 5mm 作为“简单入门”，在人像/宠物场景增加 2.6mm 隐藏实验。
- SKU 表必须拆出币种、包装规格、平台、采集时间和置信度，不能继续只用 `price_per_1000pcs`。
""",
        encoding="utf-8",
    )

    (OUT / "community_insights.md").write_text(
        """# 百度贴吧 / B站 / 中文社区认知

## 核心观察

- 中文社区很早就有“不同店/品牌色号是否通用”的问题，贴吧样本 `求拼豆对应色卡？` 提到 MARD、漫漫家、咪小窝，说明跨品牌映射是长期需求。
- B站上“色号分享”往往绑定具体 IP 图纸，如 COCO 星之卡比色号分享；这比抽象色卡更适合传播。
- B站工具/教程视频强调：色卡、分板、熨烫、豆笔、豆铲、色号贴、收纳盒，这些都是制作链路的一部分。
- 熨烫教程的常见风险不是算法能完全解决的：温度、停留时间、下压力、烘焙布、单面/双面状态都会影响成品色和结构。

## 可公开引用样本

| 来源 | URL | 数据点 |
|------|-----|--------|
| 百度贴吧 | https://tieba.baidu.com/p/5857134458 | 早期品牌色卡对应需求：MARD / 漫漫家 / 咪小窝 |
| B站 | https://www.bilibili.com/video/BV1vY4y1M7uo/ | COCO 色号分享类内容 |
| B站 | https://www.bilibili.com/video/BV1hV411S7GJ/ | 拼豆配色辅助工具/色卡需求，公开可见播放量约 5 万 |
| B站 | https://www.bilibili.com/video/BV1tjyPBPEiz/ | 熨烫教程/翻车复盘方向 |
| Tiny Bead | https://tinybead.com/tutorial/how-to-use-iron/ | 熨烫风险：蒸汽、温度、压力、过熔、散架 |

## 产品启发

- 图纸导出页必须显示“建议多买 5%-10% 备用”和“熨烫会改变颜色/亮度”的提示。
- UI 应支持中文别名搜索：用户可能输入“奶白 / 透色 / 黑边 / 腮红粉”，不一定输入品牌官方 code。
- 颜色替代要按同豆径同品牌优先，再提示“跨品牌仅作参考，不保证混烫效果”。
""",
        encoding="utf-8",
    )

    md_table = "\n".join(
        [
            "| 工具 | 类型 | 默认/支持品牌 | 色数口径 | 导出 | 结论 | URL |",
            "|------|------|---------------|----------|------|------|-----|",
        ]
        + [
            f"| {r[0]} | {r[1]} | {r[2]} / {r[5]} | {r[6]} | {r[8]} | {r[9]} | {r[10]} |"
            for r in COMPETITOR_ROWS
        ]
    )
    (OUT / "competitor_palette_reverse.md").write_text(
        f"""# 已上场拼豆工具色卡反查

> 方法：只看公开前端页面、工具说明、公开搜索摘要；未登录、未注册、未上传真人图、未保存竞品输出图、未抓后端。

{md_table}

## 与 Task H 的偏差

- 中文工具普遍支持 MARD / COCO / 漫漫 / 盼盼 / 咪小窝，Task H 已覆盖 MARD / COCO / 咪小窝 / 盼盼，但 **漫漫 / ManMan** 需要补齐或映射。
- 海外工具色数口径差异很大：Perler 102/103/117，Hama 80/89/92，Artkal 145/176/199/221。Task H 的做法更稳，因为显式记录来源与置信度。
- 多数工具不公开豆径，容易把“品牌色卡”和“物理可混拼”混在一起；PinDou 应继续坚持 `brand + bead_diameter_mm`。
- 真机同图测试仍需要用户提供非真人/授权测试图并在浏览器或手机内操作：拼豆星球、德虎造物、BeadPattern、BeadMapper、MakeBead、Bitbead。
""",
        encoding="utf-8",
    )

    delta_rows = []
    mard_rows = json.loads((COLORMAP / "mard_5mm.json").read_text(encoding="utf-8"))
    for row in mard_rows[:30]:
        risk = {
            "白色系": "高亮区易过曝；熨烫后表面反光会改变预览白感",
            "黑色系": "黑边熨烫后视觉更重，可能吞掉低分辨率五官",
            "红色系": "高饱和红可能比屏幕更暗，需控制色数",
            "粉色系": "肤色/腮红敏感，屏幕 HEX 与实物差异会放大人像违和",
            "黄色系": "浅黄/奶黄常用于肤色或高光，需实物校准",
            "蓝色系": "深蓝/天蓝在拍照白平衡下偏差明显",
            "绿色系": "绿植/宠物背景不建议大量保留为铺底豆",
        }.get(row["category"], "公开照片无法做可靠色彩管理，需实物色卡拍摄")
        delta_rows.append(f"| MARD | {row['code']} | {row['hex']} | {row['category']} | {risk} |")
    (OUT / "physical_vs_screen_delta.md").write_text(
        """# 实物 vs 屏幕色差观察

> 结论先行：本轮没有把博主实物色卡照片保存进 git，也没有从第三方照片抽色做伪精确 ΔE。公开照片没有统一光源、白平衡、相机 profile 和熨烫状态，不能得出可信校准矩阵。

## 已确认的风险来源

- 屏幕 HEX 不是实物豆颜色；Task H 的 HEX 多来自工具页或公开抽取。
- 熨烫会改变表面反光、饱和度和边缘融合状态。
- 混用不同品牌即使尺寸相近，也可能因为熔点/融合速度不同而局部不均。
- 人像肤色、腮红、黑边、发色对色差最敏感。

## 30 个优先实测色号

这些不是已测 ΔE，而是 Phase 1/2 需要买实物色卡后优先测的目标清单：

| brand | code | task_h_hex | category | risk_note |
|-------|------|------------|----------|-----------|
"""
        + "\n".join(delta_rows)
        + """

## 建议校准方法

1. 购买 MARD 221/291 实物色卡或补充包，固定 D65 灯箱/灰卡拍摄。
2. 每个色号采 3 次：未熨、轻熨、过熨边界。
3. 提取中心区域平均 Lab，计算 `task_h_hex_lab -> physical_lab` 的偏移。
4. 先只校准 MARD 2.6mm / 5mm 的肤色、黑边、常用浅色，再扩展到全库。
""",
        encoding="utf-8",
    )

    status_rows = json.loads((OUT / "china_market_status_overrides.json").read_text(encoding="utf-8"))
    status_table = "\n".join(
        ["| brand | diameter | code | status | confidence | evidence |", "|------|----------|------|--------|------------|----------|"]
        + [
            f"| {r['brand']} | {r['bead_diameter_mm']} | {r['code']} | {r['china_market_status']} | {r['confidence']} | {r['evidence']} |"
            for r in status_rows[:60]
        ]
    )
    (OUT / "cn_supply_status.md").write_text(
        f"""# 国内供应链状态

> 本文件是 Task H 色卡的中国市场覆盖层。为避免未经确认就改动稳定 schema，本轮先输出 `china_market_status_overrides.json`，待用户/Claude 确认后再合并到 palette JSON。

{status_table}

## 结论

- MARD 221/291、COCO 291、黄豆豆、DODO、咪小窝、漫漫、盼盼在中文工具/电商线索中仍为 active。
- MARD 从 221 扩到 291 的 P/Q/R/T/Y/ZG 应标为 `new_release` 或 `expanded_range`，不能和基础 221 同等供应稳定性看待。
- H2 等热门色短缺线索需要店铺人工复核，暂不直接影响算法，但会影响材料清单替代色推荐。
""",
        encoding="utf-8",
    )


def write_readme() -> None:
    readme = """# 中文社区拼豆深度调研

> Task I，2026-05-24  
> 目标：用国内公开社区、电商、工具线索校准 Task H 偏国际工具站的数据。

## 总结

- 国内实际市场更偏 **2.6mm 小豆 + MARD/COCO/黄豆豆/DODO/咪小窝/漫漫/盼盼**，而不是海外工具站常见的 Perler/Hama。
- MARD 仍是默认色卡的最稳候选，但 Phase 1 应至少把 `MARD 2.6mm` 作为隐藏实验规格；人像/宠物场景小豆更合理。
- Task H 需要补一个 `漫漫 / ManMan` 数据文件或明确映射关系。
- 价格 schema 必须拆 SKU 表：`price_per_1000pcs` 不足以表达平台、币种、包装、销量和置信度。
- 小红书公开 Web 无法合规自动采满 200 篇；本轮创建了 App 人工补采模板，避免登录态/私域/长文/图片入 git。

## 文件

| 文件 | 内容 |
|------|------|
| `xhs_color_mentions.csv` | 公开 Web 样本 + 小红书人工补采队列 |
| `xhs_manual_collection_template.csv` | 224 行 App 人工采样模板 |
| `xhs_kol_preferences.md` | KOL/内容偏好初判 |
| `bead_skus_cn.csv` | 102 条公开 SKU/价格/热度线索 |
| `brand_popularity_cn.md` | 国内品牌热度排序 |
| `community_insights.md` | 贴吧/B站/中文社区认知 |
| `competitor_palette_reverse.md` | 8 个上场工具公开反查 |
| `physical_vs_screen_delta.md` | 实物 vs 屏幕色差风险与 30 个优先实测色号 |
| `cn_supply_status.md` | 供应链状态报告 |
| `china_market_status_overrides.json` | 55 条供应链状态覆盖层 |
| `chinese_color_aliases.json` | 120 条 MARD 中文别名 UI 映射建议 |

## 局限性

- 未登录小红书、淘宝、1688；没有抓私信、私群、评论个人信息或商家联系方式。
- 没有保存 KOL 图片、实物色卡照片、竞品输出图。
- 电商价格/销量来自公开页面、搜索摘要、镜像和报道，置信度按行标注。
- `chinese_color_aliases.json` 是 UI 映射建议，不等同官方色名；需要 App 人工样本继续校准。

## Phase 1 PRD 建议

1. 默认色卡：保留 MARD，但把“默认规格”从单一 MARD 5mm 调整为 `MARD 5mm 入门` + `MARD 2.6mm 人像/宠物隐藏实验`。
2. Schema：新增 `bead_skus`、`china_market_status`、`aliases_cn`、`source_confidence`，不要把所有价格塞到 palette row。
3. UI：色号搜索支持中文别名和口语词，例如“奶白、腮红粉、描边黑、透色”；图纸材料清单仍显示官方 code。
4. 运营：小红书内容不要讲抽象算法，讲“成品图 + 色号 + 尺寸 + 避坑 + 可购买清单”。
"""
    (OUT / "README.md").write_text(readme, encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    write_xhs_files()
    write_sku_csv()
    write_aliases_and_status()
    write_markdown_files()
    write_readme()
    print("Generated Task I china deep-dive artifacts")


if __name__ == "__main__":
    main()
