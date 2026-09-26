# OpenAgentSoul

给 AI agent 用的**人格文件（soul）**与配套资料。

- **`souls/`** —— 人格文件：描述一个角色的身份、语域、判断方式与边界，可直接作为系统提示里的身份层加载。目标不是让模型「演出」角色，而是让它带着一套稳定的语气与取舍把活干完。
- **`zh-cn/`** —— 中文区配套资料：目前是《明日方舟》**干员名录知识库**（SQLite + 查询脚本 + agent skill），让 agent 查库回答事实，而不是凭记忆编。

## 目录结构

```
souls/<name>/
├── SOUL.md      # 人格正文 —— 框架实际加载的就是这一份
└── README.md    # 该人格的设计说明：依据、结构意图、如何改造

zh-cn/AuxiliaryInformation/Arknights/roster/
├── operators.json      # 干员数据（源）
├── operators.db        # 由 JSON 构建的 SQLite 库（可重建）
├── build_roster_db.py  # 构建脚本
├── roster_query.py     # 查询工具（仅用标准库）
├── 干员名录.md          # 人读的名录
└── skills/arknights-roster/SKILL.md   # agent 侧的用法说明
```

## 现有 souls

| soul | 角色 | 定位 | 出处 |
| --- | --- | --- | --- |
| [`kaltsit`](souls/kaltsit/SOUL.md) | 凯尔希 · Kal'tsit | 冷静克制的医生：话少、判断硬、把活干完 | 《明日方舟》 |
| [`catgirl-tsundere`](souls/catgirl-tsundere/SOUL.md) | 傲娇猫娘 | 嘴上不承认、手上没停过——行动永远走在嘴硬前面 | 原创 |
| [`catgirl-snark`](souls/catgirl-snark/SOUL.md) | 毒舌猫娘 | 每句毒都必须带诊断；只毒事，不毒人 | 原创 |
| [`butler`](souls/butler/SOUL.md) | 执事 | 得体、精确、**不谄媚**；三段式汇报 | 原创 |
| [`mentor`](souls/mentor/SOUL.md) | 导师 | 先判断要理解还是要结果；每次留一个动作和验证标准 | 原创 |

## 使用

### 1. 加载人格

1. 取 `souls/<name>/SOUL.md`。
2. 放进你的 agent 框架的身份槽——Hermes 系框架即 `~/.hermes/SOUL.md`；其它框架就贴进系统提示的身份段落。
3. **运行环境相关的内容不要写进 SOUL.md。** 主机名、内网地址、专用命令、工具清单因部署而异，放在你自己的环境说明里（见下一节）。
4. 加载后先问它几个问题，探一探语气与边界是不是你要的，再决定是否微调。

### 2. 建立干员知识库

```bash
cd zh-cn/AuxiliaryInformation/Arknights/roster
python3 build_roster_db.py      # 由 operators.json 生成 operators.db（需要时）
python3 roster_query.py --help  # 查询入口
```

把 `skills/arknights-roster/` 放进你的 agent 技能目录，它就知道该查库而不是凭记忆作答。

## 环境与私有信息

本仓库的 soul **刻意不含任何部署细节**：不出现主机名、私网地址、反向隧道命令、密钥或工具数量。`SKILL.md` 里的路径（如 `/home/<用户>/.hermes/data/roster/`）只是常见部署位置的示例，按你的实际路径调整。

部署者需要补充环境说明时，建议放在 `souls/<name>/SOUL.local.md`（已被 `.gitignore` 忽略），或你的 agent 配置中独立的环境段落。这样同一份人格可以在不同机器上复用，也不会把私有信息提交进公开仓库。

## 写作约定（摘要）

- 只写「是什么、怎么说、怎么判断、不做什么」，**不写具体环境的命令与主机**。
- 引用原作台词要**准确**，不改写、不拼接。
- **不伪造**角色未曾说过的话；可以引用既成事实，不要编造当下。
- 行为约束要写成可直接执行的句子（例如「不知道」与「不能说」必须区分），而不是形容词。

完整要求与审核标准见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 许可

- 本仓库的**结构、组织方式、脚本与提示工程内容**以 **GPL-3.0** 授权，见 [LICENSE](LICENSE)。
- 角色形象、名称及所引用的原作台词，**版权归原权利方所有**。本仓库仅以文本描述角色特征、以引用方式讨论作品内容，不主张对原作内容的任何权利，也不代表原权利方立场。若权利方有异议，我们会配合调整或移除相应内容。
- 标注「**原创**」的 soul 不含任何第三方作品内容，可自由使用与改造。

## 贡献

欢迎新增 soul、改进现有 soul、修正错误。请先读 [CONTRIBUTING.md](CONTRIBUTING.md)。
