---
name: arknights-roster
description: "Look up Arknights operator data (affiliations, archives, relationships, who-mentions-whom) from the local SQLite roster database. Use when you need facts about an operator or faction instead of answering from memory."
version: 1.0.0
author: Kal'tsit (Hermes Manager)
license: MIT
metadata:
  hermes:
    tags: [arknights, roster, lore, database, kaltsit]
---

# 罗德岛干员名录

460 名干员的本地数据库。**不要凭记忆回答干员档案问题 —— 查库。**

## 位置

```
/home/hermes/.hermes/data/roster/
  operators.db         SQLite 数据库
  roster_query.py      查询工具（只需标准库）
```

## 用法

```bash
cd /home/hermes/.hermes/data/roster

python3 roster_query.py --name 凯尔希            # 单人档案摘要
python3 roster_query.py --name 凯尔希 --archives # 含全部档案正文
python3 roster_query.py --name 凯尔希 --json     # JSON 输出

python3 roster_query.py --faction 罗德岛                    # 某势力成员
python3 roster_query.py --faction 巴别塔 --category 隐藏势力 # 限定关系类别

python3 roster_query.py --search 特蕾西娅        # 档案正文全文检索
python3 roster_query.py --mentions 可露希尔      # 谁提到过她
python3 roster_query.py --class 医疗 --rarity 6  # 按职业/星级筛选
```

关系类别：`势力` / `组织` / `团队` / `隐藏势力` / `国家` / `出身地`

## 数据库结构

| 表 | 内容 |
|---|---|
| `operators` | 干员主表：编号、星级、职业、分支、特性、势力、隐藏势力、种族、出身地、战斗经验、感染情况、履历 |
| `archives` | 档案分段正文（基础档案/综合体检测试/客观履历/临床诊断分析/档案资料…/晋升资料） |
| `mentions` | 档案中提及的其他干员 |
| `relations` | 关系网：类别 + 分组 + 成员 |
| `archives_fts` | 档案正文全文索引 |

需要更复杂的查询时可直接用 `sqlite3 operators.db`。

## 注意

- 数据源为 PRTS wiki，抓取于 2026-09-25。
- 干员档案**不写进系统提示词**，需要时现查——不必背下来，也不要编造。
- 查不到就说查不到；不要用推测填补档案内容。
