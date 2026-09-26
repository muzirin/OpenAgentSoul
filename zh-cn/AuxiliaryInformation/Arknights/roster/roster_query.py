#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
罗德岛干员名录查询工具。

干员数据不进 prompt，agent 需要时用本工具按需查询数据库。

用法示例
--------
    python roster_query.py --name 凯尔希              # 查单人完整档案
    python roster_query.py --name 凯尔希 --archives   # 含全部档案正文
    python roster_query.py --faction 罗德岛           # 列出某势力成员
    python roster_query.py --faction 巴别塔 --category 隐藏势力
    python roster_query.py --search 特蕾西娅          # 全文检索档案
    python roster_query.py --mentions 可露希尔        # 谁提到过她
    python roster_query.py --class 医疗 --rarity 6    # 按职业/星级筛选
    python roster_query.py --json --name 凯尔希       # 输出 JSON

环境变量
--------
ROSTER_DB  覆盖数据库路径（默认与本脚本同目录的 operators.db）
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DB = Path(os.environ.get("ROSTER_DB") or (HERE / "operators.db"))


def connect() -> sqlite3.Connection:
    if not DB.is_file():
        sys.exit(f"缺少数据库 {DB}，请先运行 build_roster_db.py")
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


def row_to_dict(row: sqlite3.Row) -> dict:
    return {k: row[k] for k in row.keys()}


# ---------------------------------------------------------------- 查询


def get_operator(con, name: str, with_archives: bool) -> dict | None:
    row = con.execute("SELECT * FROM operators WHERE name = ?", (name,)).fetchone()
    if row is None:
        # 模糊兜底：按中文名/外文名/日文名/别名匹配
        row = con.execute(
            """SELECT * FROM operators
               WHERE name LIKE ? OR name_cn LIKE ? OR name_en LIKE ? OR name_jp LIKE ?
               LIMIT 1""",
            (f"%{name}%", f"%{name}%", f"%{name}%", f"%{name}%"),
        ).fetchone()
    if row is None:
        return None

    data = row_to_dict(row)

    if with_archives:
        data["archives"] = [
            dict(r)
            for r in con.execute(
                "SELECT section, content FROM archives WHERE operator = ?", (data["name"],)
            )
        ]

    data["mentions"] = [
        r["mentioned"]
        for r in con.execute(
            "SELECT mentioned FROM mentions WHERE operator = ?", (data["name"],)
        )
    ]
    data["mentioned_by"] = [
        r["operator"]
        for r in con.execute(
            "SELECT operator FROM mentions WHERE mentioned = ?", (data["name"],)
        )
    ]
    data["relations"] = [
        f"{r['category']}/{r['grp']}"
        for r in con.execute(
            "SELECT category, grp FROM relations WHERE member = ?", (data["name"],)
        )
    ]
    return data


def list_faction(con, group: str, category: str | None) -> list[dict]:
    sql = """SELECT DISTINCT o.name, o.rarity, o.class_, o.branch, r.category, r.grp
             FROM relations r JOIN (
                 SELECT name, rarity, class AS class_, branch FROM operators
             ) o ON o.name = r.member
             WHERE r.grp = ?"""
    params: list = [group]
    if category:
        sql += " AND r.category = ?"
        params.append(category)
    sql += " ORDER BY o.rarity DESC, o.name"

    # 上面用了子查询别名，简化成直接查 operators
    sql = """SELECT DISTINCT o.name, o.rarity, o.class, o.branch, r.category, r.grp
             FROM relations r JOIN operators o ON o.name = r.member
             WHERE r.grp = ?"""
    params = [group]
    if category:
        sql += " AND r.category = ?"
        params.append(category)
    sql += " ORDER BY o.rarity DESC, o.name"

    return [row_to_dict(r) for r in con.execute(sql, params)]


def search_archives(con, keyword: str, limit: int) -> list[dict]:
    out: list[dict] = []
    try:
        rows = con.execute(
            """SELECT operator, section, content FROM archives_fts
               WHERE archives_fts MATCH ? LIMIT ?""",
            (f'"{keyword}"', limit),
        ).fetchall()
    except sqlite3.OperationalError:
        rows = []

    if not rows:
        # FTS 对中文分词不可靠时退回 LIKE
        rows = con.execute(
            """SELECT operator, section, content FROM archives
               WHERE content LIKE ? LIMIT ?""",
            (f"%{keyword}%", limit),
        ).fetchall()

    for r in rows:
        text = r["content"] or ""
        idx = text.find(keyword)
        snippet = text[max(0, idx - 40): idx + 80] if idx >= 0 else text[:120]
        out.append(
            {"operator": r["operator"], "section": r["section"], "snippet": snippet.strip()}
        )
    return out


def filter_operators(con, cls: str | None, rarity: int | None,
                     faction: str | None, limit: int) -> list[dict]:
    sql = "SELECT name, rarity, class, branch, faction, hidden FROM operators WHERE 1=1"
    params: list = []
    if cls:
        sql += " AND class = ?"
        params.append(cls)
    if rarity:
        sql += " AND rarity = ?"
        params.append(rarity)
    if faction:
        sql += " AND (faction LIKE ? OR hidden LIKE ?)"
        params.extend([f"%{faction}%", f"%{faction}%"])
    sql += " ORDER BY rarity DESC, no LIMIT ?"
    params.append(limit)
    return [row_to_dict(r) for r in con.execute(sql, params)]


# ---------------------------------------------------------------- 输出


def render_operator(d: dict, with_archives: bool) -> str:
    lines = [
        f"【{d['name']}】{d.get('name_en','')} / {d.get('name_jp','')}",
        f"  编号 {d.get('intel_code','')} · {d.get('rarity',0)}★ · {d.get('class','')}"
        f"（{d.get('branch','')}）· {d.get('position','')}",
        f"  势力 {d.get('faction','') or '—'}"
        + (f" · 隐藏势力 {d['hidden']}" if d.get("hidden") else ""),
        f"  国家 {d.get('nation','') or '—'} · 出身地 {d.get('birth','') or '—'}"
        f" · 种族 {d.get('race','') or '—'}",
        f"  战斗经验 {d.get('combat_exp','') or '—'} · 感染 {d.get('infected','') or '—'}",
        f"  特性 {d.get('trait','') or '—'} · 标签 {d.get('tags','') or '—'}",
    ]
    if d.get("profile"):
        lines.append(f"  履历 {d['profile']}")
    if d.get("relations"):
        lines.append("  关系网 " + "、".join(d["relations"]))
    if d.get("mentions"):
        lines.append("  提及过 " + "、".join(d["mentions"]))
    if d.get("mentioned_by"):
        lines.append("  被提及 " + "、".join(d["mentioned_by"]))
    if with_archives and d.get("archives"):
        lines.append("  ── 档案 ──")
        for a in d["archives"]:
            lines.append(f"  ▸ {a['section']}")
            for para in (a["content"] or "").split("\n"):
                lines.append(f"    {para}")
    return "\n".join(lines)


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    ap = argparse.ArgumentParser(prog="roster_query", description="罗德岛干员名录查询")
    ap.add_argument("--name", help="干员名（支持模糊）")
    ap.add_argument("--archives", action="store_true", help="附带档案正文")
    ap.add_argument("--faction", help="按势力/组织/团队名列出成员")
    ap.add_argument("--category", help="限定关系类别：势力/组织/团队/隐藏势力/国家/出身地")
    ap.add_argument("--search", help="在档案正文中全文检索")
    ap.add_argument("--mentions", help="谁提到过该干员")
    ap.add_argument("--class", dest="cls", help="按职业筛选（如 医疗）")
    ap.add_argument("--rarity", type=int, help="按星级筛选（1-6）")
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    args = ap.parse_args(argv)

    con = connect()

    if args.name:
        d = get_operator(con, args.name, args.archives)
        if d is None:
            print(f"未找到干员：{args.name}")
            return 1
        print(json.dumps(d, ensure_ascii=False, indent=2) if args.json
              else render_operator(d, args.archives))
        return 0

    if args.faction:
        rows = list_faction(con, args.faction, args.category)
        if not rows:
            print(f"未找到分组：{args.faction}")
            return 1
        print(json.dumps(rows, ensure_ascii=False, indent=2) if args.json else
              f"{args.faction}（{len(rows)}）:\n" +
              "\n".join(f"  {r['name']}  {r['rarity']}★ {r['class']}" for r in rows))
        return 0

    if args.mentions:
        rows = [dict(r) for r in con.execute(
            """SELECT m.operator, a.section, a.content FROM mentions m
               LEFT JOIN archives a ON a.operator = m.operator
               WHERE m.mentioned = ?""", (args.mentions,))]
        who = sorted({r["operator"] for r in rows})
        print(json.dumps(rows, ensure_ascii=False, indent=2) if args.json else
              f"提到「{args.mentions}」的干员（{len(who)}）：" + "、".join(who))
        return 0

    if args.search:
        rows = search_archives(con, args.search, args.limit)
        if not rows:
            print(f"未检索到：{args.search}")
            return 1
        print(json.dumps(rows, ensure_ascii=False, indent=2) if args.json else
              f"检索「{args.search}」（{len(rows)} 条）:\n" +
              "\n".join(f"  [{r['operator']}·{r['section']}] {r['snippet']}" for r in rows))
        return 0

    rows = filter_operators(con, args.cls, args.rarity, args.faction, args.limit)
    if not rows:
        print("无匹配结果")
        return 1
    print(json.dumps(rows, ensure_ascii=False, indent=2) if args.json else
          f"筛选结果（{len(rows)}）:\n" +
          "\n".join(f"  {r['name']}  {r['rarity']}★ {r['class']}/{r['branch']}"
                    f"  {r['faction'] or '—'}" for r in rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
