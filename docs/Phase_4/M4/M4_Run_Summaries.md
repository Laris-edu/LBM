# M4 运行汇总（P4-5/E2）

权威 run 与门测量的索引（详细判读见 `M4_Verification_Report.md`；原始产物在 `results/m4/<run_id>/`，不入库）。

| run_id | scope | E2 amp err max | E2 phase max | R2 | 通道差 | SPL（+20λ） | e2 | digest |
|---|---|---|---|---|---|---|---|---|
| `20260709T121241Z` | `P4-5_E2_D3_ONEWAY_10KHZ_NORMAL_EMISSION` | **+2.28%**（<10%） | 1.21°（<10°） | 0.18%（<5%） | −0.36%（<10%） | **86.60 dB ±0.46 dB[M3]** | `PASSED` | `cbcf7d738ede` |

**链路冻结常数（复现所需）**：`T̂_s=0.37269 K@−47.535°`（M3 canonical，digest `26be2fde3cc2`）→ `u_src=1.4683e-3 m/s` → `dp̂_phys=0.5997 Pa` → `G=0.1580@+152.4°`（立项 §12.3）→ 校准介质（`c0_m_s=339.9175` 旋钮）→ K0 kernel（`(−i/4)H₀^{(2)}`）。复现：`python -m scripts.phase4_m4_endtoend`；门测试 `verification/test_phase4_m4_endtoend.py`。

**M4 gate 措辞**：`PASSED_WITH_SCOPED_RISK`（报告 §7；(b) 清偿后 #2→DIAGNOSTIC_QUANTIFIED、#3→已定性，#1/#4/#5 为声明性；非 clear PASS、非 final production、不授权频扫）。

**run 谱系**：`20260709T121241Z`（digest `cbcf7d738ede`，含 CV 通量审计 I_start=4.496e-4 W/m²/闭合 ~1%）取代 `20260709T083552Z`（digest `8ecc2486d14a`，E2 门数值逐位相同、仅缺 cv_audit 块——确定性链复现的自证）。
