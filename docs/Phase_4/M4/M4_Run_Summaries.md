# M4 运行汇总（P4-5/E2）

权威 run 与门测量的索引（详细判读见 `M4_Verification_Report.md`；原始产物在 `results/m4/<run_id>/`，不入库）。

| run_id | scope | E2 amp err max | E2 phase max | R2 | 通道差 | SPL（+20λ） | e2 | digest |
|---|---|---|---|---|---|---|---|---|
| `20260711T063735Z` | `P4-5_E2_D3_ONEWAY_10KHZ_NORMAL_EMISSION` | **+1.62%**（<10%） | 0.92°（<10°） | **2.63%**（<5%，同一绝对观察点/三点最大值） | −0.36% / −0.07°（<10%/<10°） | **86.67 dB ±0.46 dB[M3]** | `PASSED` | `d69bf24d881e` |
| `20260709T121241Z` | `P4-5_E2_D3_ONEWAY_10KHZ_NORMAL_EMISSION` | **+2.28%**（<10%） | 1.21°（<10°） | 0.18%（<5%） | −0.36%（<10%） | **86.60 dB ±0.46 dB[M3]** | `PASSED` | `cbcf7d738ede` |

**链路冻结常数（复现所需）**：`T̂_s=0.37269 K@−47.535°`（M3 canonical，digest `26be2fde3cc2`）→ `u_src=1.4683e-3 m/s` → `dp̂_phys=0.5997 Pa` → `G=0.1580@+152.4°`（立项 §12.3）→ 校准介质（`c0_m_s=339.9175` 旋钮）→ K0 kernel（`(−i/4)H₀^{(2)}`）。复现：`python -m scripts.phase4_m4_endtoend`；门测试 `verification/test_phase4_m4_endtoend.py`。

**M4 gate 措辞**：`PASSED_WITH_SCOPED_RISK`（报告 §7；(b) 清偿后 #2→DIAGNOSTIC_QUANTIFIED、#3→已定性，#1/#4/#5 为声明性；非 clear PASS、非 final production、不授权频扫）。

**run 谱系**：`20260711T063735Z`（digest `d69bf24d881e`）取代 `20260709T121241Z`：旧 R2 为每个控制面各自平移观察点且只比较首点，低估为 0.18%；新 run 固定同一绝对观察点、取三点最大值，并把通道相位门纳入 verdict，修正 R2=2.63% 后仍 PASSED。`20260709T121241Z` 继续作为 CV 审计首次落地的历史证据，不再是当前 E2 权威摘要。
