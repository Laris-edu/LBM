# 文档架构：分层混合（Layered-Hybrid）

本项目所有文档遵循「分层混合」架构。本文是该架构的**唯一权威说明**（核心逻辑与决策规则）；
`CLAUDE.md` 与 `lbm-doc-sync` skill 是它的操作摘要，指向本文、不复制本文。

> 一句话：**按海拔分层、按范围混合，用「一个事实只有一个家」防漂移。**

## 0. 它解决什么问题

项目变大后，文档常滑向两个失败极端：

- **一份巨文档**装下全部 → 臃肿、远离代码、单点漂移、没人读得完；
- **到处碎 README** 互相复制 → 重复、矛盾、跨目录全局图丢失。

分层混合是中间路径：让每个事实落在唯一、最合适的「家」，既不堆成山，也不散成沙。

## 1. 铁律：一个事实只有一个家

唯一真相源（single source of truth）。同一事实**绝不**写两遍——重复＝必然漂移（两份各自被改，最终矛盾）。
其余所有规则都为这条服务：凡「看起来能放两处」的，放更具体的那个，另一处**退化成指针（链接）**。

## 2. 轴一 · 分层（竖切：按海拔 / 抽象层级）

文档按抽象高度分层。**越上层越压缩、越稳定、越先读**；要细节就逐层下钻，钻到够用为止——上层永远是下层的压缩索引。

| 层 | 角色（只装什么） | 本项目载体 | 变更频率 |
|---|---|---|---|
| 入口层 | 全项目结论 / 口径 / 链接 | `docs/PROJECT_CONTEXT.md` | 最低；最先读 |
| 阶段流水层 | 当前阶段详细日志、数值、风险、更新日志 | `docs/Phase_N/PhaseN_STATUS.md` | 高 |
| 证据层 | 推导、反例、专项分析 | `docs/Phase_N/<主题>/*.md` | 中 |
| 产物 / 归档层 | run 摘要、digest、长期留档 | `results/`（不入库）→ `docs/Phase_2/M2/M2_runs/` | 高 |

铁规：**入口层绝不放 run 数值或推导**——否则「先读一份」退化成「读一本书」。

## 3. 轴二 · 混合（横切：按事实的作用范围）

同一层内，再按「事实管多大范围」在两种组织策略间选一：

- **就近（distributed）**：只关乎某目录的事实 → 放该目录 `README.md`。优点：打开目录即见、改代码时顺手更新、就近不易忘。
- **集中（centralized）**：跨目录的关系 / 约定 / 总览 → 放一份集中文档。优点：全局图不散、约定有唯一出处。

「混合」＝两者**并存**，不是二选一。

| 策略 | 装什么 | 本项目载体 |
|---|---|---|
| 就近 | 「这个目录里有什么 / 怎么跑」的逐文件说明 | `core/README.md`、`configs/README.md`、`verification/README.md`、`phase3_interfaces/README.md`、`scripts/README.md` |
| 集中 | 跨目录结构图、专题文档索引、运行产物 / 归档约定、实现边界 | `docs/Phase_N/PhaseN_Output_Files_Guide.md` |

## 4. 决策规则：一个事实该去哪个家？

```text
这个事实是……
├─ 全项目级结论 / 当前状态？       → 入口层  PROJECT_CONTEXT（压缩）
├─ 本阶段的 run / 数值 / 日志？      → 流水层  PhaseN_STATUS
├─ 推导 / 反例 / 专项分析？          → 证据层  专项报告
├─ “这个目录里有什么 / 怎么跑”？     → 就近    该目录 README
├─ 跨目录关系 / 约定 / 总览？        → 集中    Output_Files_Guide
└─ run 产物 / 需长期留档？           → 产物层  results/ → M2_runs/（不提交 results/）

若它“看起来能放两处” → 放更具体 / 就近的那个，另一处退化成指针。
```

## 5. 为什么是「混合」，而非两个纯粹极端

| 方案 | 问题 |
|---|---|
| 纯集中（一份大文档） | 臃肿、远离代码、单点漂移 |
| 纯分散（到处 README，无总览） | 跨目录关系散掉、约定无出处、无法快速建全局图 |
| **分层混合** | 局部事实就近（易发现、随改随新）＋ 跨目录事实集中（总览不丢）＋ 入口层始终薄（先读一份即可定位一切） |

## 6. 反模式（出现即违反铁律）

- 入口文档里出现 run 号、百分比、长推导 → 应下沉到 STATUS / 证据层。
- 给目录建了 README，又在 Output_Files_Guide 保留同一份逐文件表 → 后者应退化成指针。
- `CLAUDE.md` / skill 复制 PROJECT_CONTEXT 的护栏全文 → 应只链接。
- 同一 run 的结论在多处各写一遍 → 留一处，其余链接。

## 7. 落地映射（本项目，随阶段复用同一套）

每进入一个新阶段，**架构不变、只套一遍**：

| 层 | Phase_2 | Phase_3（进行中） |
|---|---|---|
| 入口（全项目唯一） | `docs/PROJECT_CONTEXT.md`（指针指向当前阶段） | 同一份，指针切到 Phase_3 |
| 阶段流水 | `docs/Phase_2/Phase2_STATUS.md` | `docs/Phase_3/Phase3_STATUS.md` |
| 阶段合同 | `docs/Phase_2/phase2_instruction_v1.1.md` | `docs/Phase_3/phase3_instruction_v1.0.md` |
| 集中总览 | `docs/Phase_2/Phase2_Output_Files_Guide.md` | `docs/Phase_3/Phase3_Output_Files_Guide.md` ＋ `docs/Phase_3/README.md` |
| 证据 | `docs/Phase_2/{closure,acoustic,robustness}/*.md` | （随 P3-x 产出） |
| 里程碑归档 | `docs/Phase_2/M2/`（含 `M2_runs/`） | （M3 启动后） |
| 就近 README | `core/`、`configs/`、`verification/`、`phase3_interfaces/`、`scripts/` | 同上（`configs/` 已加 Phase_3 入口节） |

## 8. 与执行机制的关系

本文是「为什么 / 核心逻辑」；落地强制由两件东西承担（它们指向本文，不复制）：

- **`CLAUDE.md`**（每会话常驻）：写「何时必须同步文档」的义务与触发条件。
- **`lbm-doc-sync` skill**：写「具体怎么落位」的 6 步流程清单。

文档同步的触发条件权威清单见 `docs/PROJECT_CONTEXT.md` §7「维护规则」。
