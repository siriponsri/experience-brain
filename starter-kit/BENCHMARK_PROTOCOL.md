# Benchmark Protocol

## Benchmark ที่เลือก

### Primary: SkillEvolBench

เลือกเพราะ benchmark ออกแบบมาเพื่อวัดการเปลี่ยนจาก episodic experience ไป procedural skill โดยตรง มี acquisition และ frozen deployment tasks ทำให้แยก local adaptation ออกจาก durable transfer ได้

ใช้ทั้ง Lite และ Full บน task split เดียวกัน นี่คือ benchmark หลักสำหรับ claim ของ paper

### Secondary: Terminal-Bench 2.0

ใช้ตรวจ external validity ของงาน CLI จริง โดยเริ่ม pilot 6–12 tasks แล้วขยายตาม budget จุดสำคัญคือ verifier-based outcome ไม่ใช้ LLM judge เป็น primary score

### Full stress tracks

- **MemoryArena หรือ MemGym:** memory ที่เกิดระหว่าง action และนำไปใช้ข้าม session
- **LongCLI-Bench:** งาน programming ระยะยาว 20 tasks พร้อม step-level diagnosis
- **EpiBench:** เฉพาะเมื่อเปิด multimodal/research workflow track

## Conditions

| ID | Condition | Persistent information allowed |
|---|---|---|
| C0 | No memory | task prompt + current session only |
| C1 | Wiki baseline | Prompt 01/02-style raw/wiki/index/lessons |
| C2 | Lite | events, episodes, verified Markdown skills, lexical retrieval, bounded capsule |
| C3 | Full | C2 + hybrid retrieval, consolidation, intervention, KG/multimodal ตาม ablation |

เพิ่ม C4 `raw trajectory reuse` ใน ablation เพราะ SkillEvolBench รายงานว่า raw traces อาจดีกว่า distilled skills ในบาง setting

## Fairness controls

- model identifier และ reasoning effort เหมือนกันทุก condition
- task order randomized เป็น blocks
- time/token/tool limits เท่ากัน
- same system prompt ยกเว้น memory interface ที่จำเป็น
- acquisition data และ deployment data แยกเด็ดขาด
- memory store แยก directory/container ต่อ condition และ run
- temperature/seed/version บันทึกทุกครั้ง แม้ provider ไม่รับประกัน determinism
- freeze Codex, benchmark harness, dependency lock และ container digest

## Metrics

### Primary

```text
deployment_success_rate = passed_deployment_tasks / attempted_deployment_tasks
```

### Co-primary efficiency

```text
total_tokens = action_agent_input + action_agent_output
             + memory_write + consolidation + retrieval_rerank
             + judge_tokens_if_any

tokens_per_success = total_tokens / successful_deployment_tasks
```

### Secondary

- acquisition success
- cross-task / cross-role / cross-domain transfer
- repeated error rate by failure signature
- skill activation precision and recall
- harmful activation / negative transfer rate
- latency p50/p95
- memory size and growth slope
- capsule tokens and evidence density
- provenance accuracy จาก human sample
- background-to-foreground token ratio

## Recommended outcome schema

```json
{
  "run_id": "2026-08-01_c2_task17_r2",
  "condition": "lite",
  "task_id": "...",
  "split": "deployment",
  "model": "exact-model-id",
  "reasoning": "high",
  "commit_sha": "...",
  "harness_version": "...",
  "success": true,
  "verifier_score": 1.0,
  "foreground_input_tokens": 0,
  "foreground_output_tokens": 0,
  "background_tokens": 0,
  "wall_seconds": 0,
  "skills_retrieved": [],
  "skills_applied": [],
  "failure_signature": null
}
```

## Statistical analysis

- ใช้ paired comparison ตาม task เพราะทุก condition ทำ task ชุดเดียวกัน
- success แบบ binary: report paired difference, bootstrap 95% CI และ McNemar test เป็น sensitivity analysis
- token/latency แบบ skewed: median, IQR, paired bootstrap และ log-scale visualization
- multiple secondary metrics: แยก confirmatory กับ exploratory; ใช้ correction หรือรายงาน unadjusted อย่างชัดเจน
- รายงาน effect size และ CI ไม่พึ่ง p-value อย่างเดียว
- run-level และ task-level variability ต้องแยกกัน

## Pilot task selection

เลือกแบบ stratified ก่อนเห็นผล condition:

- 1/3 task สั้น
- 1/3 task กลาง
- 1/3 task ยาว
- ครอบคลุม failure recovery, tool use, multi-file state และ repeated procedure

เก็บ task IDs และ hash ใน `evaluations/manifests/pilot-v1.json` และ final manifest แยกกัน

## BrainBench-Mini สำหรับ development เท่านั้น

สร้าง local tests 12–20 tasks เช่น recall exact state, conflict update, skill merge, forgetting, distractor injection, procedure composition และ token budget ใช้ตรวจ regression ได้ แต่ **ห้ามใช้เป็นหลักฐานหลัก** เพราะผู้พัฒนาระบบสร้างทั้ง benchmark และ solution

## Leakage checks

- hash source/trajectory ที่เข้า memory
- search deployment task strings ใน acquisition memory
- disable internet ถ้า benchmark กำหนด
- แยก converted literature corpus ออกจาก benchmark memory
- reset repo/container/memory store ก่อนแต่ละ condition
- audit retrieved items 10–20% แบบ blind

## Interpretation rule

Full จะเรียกว่า “ดีกว่า” Lite ก็ต่อเมื่อ:

1. primary success ดีขึ้นหรือ non-inferior ตาม margin
2. มีประโยชน์ในอย่างน้อยหนึ่ง prespecified stress/transfer metric
3. incremental total tokens/latency ถูกเปิดเผย
4. ablation ชี้ว่า gain มาจาก module ไม่ใช่ prompt drift

## Primary benchmark sources

- SkillEvolBench: <https://arxiv.org/abs/2605.24117>
- Terminal-Bench 2.0: <https://arxiv.org/abs/2601.11868>
- MemoryArena: <https://arxiv.org/abs/2602.16313>
- MemGym: <https://arxiv.org/abs/2605.20833>
- LongCLI-Bench: <https://arxiv.org/abs/2602.14337>
- EpiBench: <https://arxiv.org/abs/2604.05557>
