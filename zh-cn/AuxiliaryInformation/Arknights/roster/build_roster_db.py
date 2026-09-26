#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把 roster/operators.json 构建成 SQLite 数据库，供 agent 按需检索。

设计要点
--------
* 干员名录**不写进 prompt**（460 人塞进系统提示词既臃肿又浪费），
  而是落成数据库，agent 需要时用 roster_query.py 查询。
* 建 FTS5 全文索引，支持档案正文模糊检索。
* 关系网（势力/组织/团队/隐藏势力/国家/出身地）单独成表，便于「谁属于谁」。
* mentions（档案提及）单独成表，支持「谁提到过谁」。

用法：
    python build_roster_db.py
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "operators.json"
DB = HERE / "operators.db"


def _text(value) -> str:
    """把任意字段压成可入库的字符串。"""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (list, tuple)):
        return "、".join(str(x).strip() for x in value if str(x).strip())
    if isinstance(value, dict):
        return "\n".join(f"{k}: {_text(v)}" for k, v in value.items() if _text(v))
    return str(value)


def build() -> None:
    if not SRC.is_file():
        sys.exit(f"缺少数据源：{SRC}")

    data = json.loads(SRC.read_text(encoding="utf-8"))
    operators = data.get("operators") or []
    relations = data.get("relations") or {}

    if DB.exists():
        DB.unlink()

    con = sqlite3.connect(DB)
    cur = con.cursor()

    cur.executescript(
        """
        CREATE TABLE operators (
            name        TEXT PRIMARY KEY,
            char_id     TEXT,
            no          INTEGER,
            rarity      INTEGER,
            class       TEXT,
            branch      TEXT,
            trait       TEXT,
            position    TEXT,
            tags        TEXT,
            intel_code  TEXT,
            name_cn     TEXT,
            name_en     TEXT,
            name_jp     TEXT,
            nation      TEXT,   -- 国家
            faction     TEXT,   -- 势力（明面）
            hidden      TEXT,   -- 隐藏势力
            org         TEXT,   -- 组织
            team        TEXT,   -- 团队
            gender      TEXT,
            birth       TEXT,   -- 出身地
            race        TEXT,
            birthday    TEXT,
            height      TEXT,
            combat_exp  TEXT,
            infected    TEXT,
            profile     TEXT,   -- 履历（resume）
            acquire     TEXT,
            credits     TEXT
        );

        CREATE TABLE archives (
            operator TEXT,
            section  TEXT,
            content  TEXT
        );

        CREATE TABLE mentions (
            operator  TEXT,
            mentioned TEXT
        );

        CREATE TABLE relations (
            category TEXT,   -- 势力 / 组织 / 团队 / 隐藏势力 / 国家 / 出身地
            grp      TEXT,   -- 分组名
            member   TEXT
        );

        CREATE INDEX idx_archives_op ON archives(operator);
        CREATE INDEX idx_mentions_op ON mentions(operator);
        CREATE INDEX idx_mentions_to ON mentions(mentioned);
        CREATE INDEX idx_relations_member ON relations(member);
        CREATE INDEX idx_relations_grp ON relations(category, grp);
        """
    )

    for op in operators:
        name = _text(op.get("name"))
        if not name:
            continue

        names = op.get("names") or {}
        aff = op.get("affiliation") or {}
        prof = op.get("profile") or {}
        acq = op.get("acquire") or {}
        cred = op.get("credits") or {}

        cur.execute(
            """INSERT OR REPLACE INTO operators VALUES
               (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                name,
                _text(op.get("char_id")),
                op.get("no") or 0,
                op.get("rarity") or 0,
                _text(op.get("class")),
                _text(op.get("branch")),
                _text(op.get("trait")),
                _text(op.get("position")),
                _text(op.get("tags")),
                _text(op.get("intel_code")),
                _text(names.get("中文")),
                _text(names.get("外文")),
                _text(names.get("日文")),
                _text(aff.get("国家")),
                _text(aff.get("势力")),
                _text(aff.get("隐藏势力")),
                _text(aff.get("组织")),
                _text(aff.get("团队")),
                _text(prof.get("性别")),
                _text(prof.get("出身地")),
                _text(prof.get("种族")),
                _text(prof.get("生日")),
                _text(prof.get("身高")),
                _text(prof.get("战斗经验")),
                _text(prof.get("是否感染者")),
                _text(op.get("resume")),
                _text(acq),
                _text(cred),
            ),
        )

        archives = op.get("archives") or {}
        if isinstance(archives, dict):
            for section, content in archives.items():
                body = _text(content)
                if body:
                    cur.execute(
                        "INSERT INTO archives VALUES (?,?,?)", (name, _text(section), body)
                    )

        for m in op.get("mentions") or []:
            if _text(m):
                cur.execute("INSERT INTO mentions VALUES (?,?)", (name, _text(m)))

    for category, groups in relations.items():
        if not isinstance(groups, dict):
            continue
        for grp, members in groups.items():
            for member in members or []:
                cur.execute(
                    "INSERT INTO relations VALUES (?,?,?)",
                    (_text(category), _text(grp), _text(member)),
                )

    # 全文索引：档案正文 + 履历
    cur.executescript(
        """
        CREATE VIRTUAL TABLE archives_fts USING fts5(
            operator, section, content, tokenize='unicode61'
        );
        INSERT INTO archives_fts (operator, section, content)
            SELECT operator, section, content FROM archives;

        CREATE VIRTUAL TABLE operators_fts USING fts5(
            name, profile, tokenize='unicode61'
        );
        INSERT INTO operators_fts (name, profile)
            SELECT name, profile FROM operators;
        """
    )

    con.commit()

    counts = {
        "干员": cur.execute("SELECT COUNT(*) FROM operators").fetchone()[0],
        "档案段": cur.execute("SELECT COUNT(*) FROM archives").fetchone()[0],
        "提及关系": cur.execute("SELECT COUNT(*) FROM mentions").fetchone()[0],
        "关系条目": cur.execute("SELECT COUNT(*) FROM relations").fetchone()[0],
    }
    con.close()

    print(f"已生成: {DB}")
    for k, v in counts.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    build()
