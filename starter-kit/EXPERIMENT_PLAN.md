# แผนทดลอง Lite → Full ระยะ 12 สัปดาห์

## Phase 0 — Preregister และ freeze (สัปดาห์ 1)

Deliverables:

- research questions และ hypotheses เวอร์ชัน 1.0
- benchmark task manifest ที่มี hash
- 4 conditions และ token budgets
- exclusion criteria, stopping rule, analysis plan
- environment manifest: model, reasoning, Codex version, harness version, OS, Docker, commit SHA

Gate: ห้ามเริ่ม Full จนกว่า protocol ถูก commit/tag เป็น `protocol-v1`

## Phase 1 — Lite core (สัปดาห์ 2–3)

สร้าง event log, episode builder, skill schema, registry, lexical retriever, capsule builder และ HTML report

Tests ขั้นต่ำ:

- append-only event log ไม่แก้ย้อนหลัง
- episode ทุกตัว trace กลับ event ได้
- skill ทุกตัวมี activation/precondition/procedure/termination/evidence
- duplicate skill ถูก merge อย่าง deterministic หรือส่ง review
- deprecated skill ไม่ถูก retrieve
- capsule ไม่เกิน budget ±2%
- untrusted source text ไม่กลายเป็น instruction โดยอัตโนมัติ

Gate: tests ผ่าน 100% และ manual review 20 episodes ไม่พบ provenance ขาด

## Phase 2 — Pilot benchmark (สัปดาห์ 4)

Conditions:

- C0: no persistent memory
- C1: Wiki baseline จาก Prompt 01/02
- C2: Lite

ใช้ SkillEvolBench pilot subset และ Terminal-Bench 2.0 จำนวน 6–12 tasks ห้ามใช้ pilot tasks ใน final test

สิ่งที่ pilot ตอบ:

- logger เก็บ token/latency ครบไหม
- verifier deterministic หรือไม่
- task ยาก/ง่ายเกินไปไหม
- run ใช้ budget เท่าไร
- memory leakage ข้าม condition หรือ task หรือไม่

Gate: data completeness ≥ 98%; ไม่มี cross-condition memory leakage

## Phase 3 — Lite main study (สัปดาห์ 5–6)

รัน C0, C1, C2 บน frozen acquisition/deployment splits อย่างน้อย 3 runs ต่อ condition ใช้ randomized block order เพื่อกระจายผลจาก service/model drift

Primary endpoint:

```text
deployment_success_rate on SkillEvolBench
```

Co-primary efficiency endpoint:

```text
tokens_per_success = total_foreground_and_background_tokens / successful_tasks
```

Secondary endpoints: repeated error rate, skill reuse precision, cross-task transfer, latency, capsule size และ provenance accuracy

Go-to-Full:

- Lite ชนะ C0 ใน tokens_per_success อย่างมี effect ที่ใช้งานได้จริง
- success ไม่ด้อยกว่า C0 เกิน non-inferiority margin 2 pp
- หรือ Lite ลด repeated errors ≥ 15% พร้อม confidence interval ที่รายงานชัด

หากไม่ผ่าน ให้ publish/เขียนเป็น diagnostic study ได้ ไม่ควรซ่อนผล

## Phase 4 — Full modules ทีละตัว (สัปดาห์ 7–9)

เพิ่ม module ตามลำดับ:

1. hybrid retrieval
2. consolidation/pruning
3. proactive intervention
4. temporal KG
5. multimodal track (ทำเมื่อ benchmark ต้องใช้จริง)

ทุก module ต้องมี ablation และ rollback flag เช่น `profile=full --no-kg`

Gate ของแต่ละ module: ชนะ Lite อย่างน้อยหนึ่ง metric โดยไม่ทำ primary endpoint แย่ลงเกิน margin และรายงาน incremental token/latency cost

## Phase 5 — Full main study (สัปดาห์ 10)

รัน C0–C3 ทั้งหมดบน frozen final tasks:

- C0 no memory
- C1 Wiki
- C2 Lite
- C3 Full

เพิ่ม Full stress track: MemoryArena หรือ MemGym และ LongCLI-Bench หากทรัพยากรพอ

## Phase 6 — Analysis และ paper (สัปดาห์ 11–12)

- validate raw logs กับ task manifest
- compute bootstrap 95% CI และ paired effect sizes
- ทำ error taxonomy แบบ blind condition labels ถ้าเป็นไปได้
- สร้าง figures/tables จาก script เท่านั้น
- เขียน Results ก่อน Discussion
- เติม limitations, negative transfer, contamination, model drift และ cost accounting
- ทำ reproducibility audit โดยรัน fresh clone อย่างน้อยหนึ่งครั้ง

## Minimum publishable ablations

1. raw trajectory vs distilled skill
2. unbounded context vs 1k/2k/4k capsule
3. no consolidation vs merge/prune consolidation
4. always retrieve vs selective retrieval/intervention
5. Lite lexical vs Full hybrid retrieval
6. with vs without provenance/evidence gate

## Budget ladder

| Stage | Tasks | Repeats | ใช้เพื่อ |
|---|---:|---:|---|
| smoke | 2–3 | 1 | ตรวจ harness |
| pilot | 6–12 | 1–2 | ประมาณ variance/cost |
| main-lite | frozen subset | 3 | ตัดสิน Go-to-Full |
| main-full | full feasible set | 3+ | final claims |

อย่ากำหนด sample size จากความสะดวกอย่างเดียว หลัง pilot ให้ใช้ observed paired variance ทำ power/sensitivity analysis และรายงาน minimum detectable effect

## Stop rules

- หยุด run หากเกิน token/time budget ที่ preregistered
- verifier failure ให้นับเป็น infrastructure failure ไม่ใช่ task failure และ rerun ตามกฎเดียวกันทุก condition
- model/service outage ให้หยุดทั้ง block ไม่เลือก rerun เฉพาะ condition ที่คะแนนต่ำ
- task contamination หรือ leaked solution ให้ exclude ตามเกณฑ์ที่เขียนไว้ก่อนเห็น condition labels

