# Architecture: Lite → Full ใน repo เดียว

## Thesis ของระบบ

สิ่งที่ทำให้ agent “มี experience” ไม่ใช่จำนวนไฟล์ แต่คือวงจรที่ตรวจสอบได้:

```text
event → episode → attribution → lesson/skill candidate → verification
      → consolidation → retrieval/intervention → outcome → update
```

ระบบ Wiki ของอาจารย์เก่งด้านจัดระเบียบ artifact, provenance, version และ human-readable knowledge ส่วน Autoresearch เก่งด้าน iterative experiment search ภายใต้ objective ที่วัดได้ Experience Brain เสนอชั้นที่ต่างออกไป: แปลง trajectory และผลลัพธ์เป็น procedural memory ที่มี lifecycle และวัดการ transfer ไปงานใหม่

## Canonical storage

```text
experience-brain/
├── AGENTS.md
├── brain.yaml
├── inbox/                     # raw user/agent inputs
├── sources/                   # immutable originals + converted Markdown
├── events/events.jsonl        # append-only event log
├── memory/
│   ├── episodes/              # what happened
│   ├── concepts/              # stable semantic facts
│   ├── skills/                # how to do recurring procedures
│   └── visual/                # image descriptors + pointers
├── policies/                  # write/retrieve/consolidate rules
├── capsules/                  # generated token-bounded context
├── evaluations/               # benchmark manifests + raw metrics
├── reports/                   # generated HTML for humans
└── tools/                     # deterministic validators and renderers
```

Markdown/YAML/JSONL คือ source of truth; SQLite/FTS/vector/KG เป็น **rebuildable indexes**; HTML เป็น view ที่ generate ใหม่ได้

## Lite profile

### Components

| Component | งาน | Implementation ที่ลีน |
|---|---|---|
| Event logger | เก็บ action, observation, result, cost | JSONL append-only |
| Episode builder | สรุปหนึ่ง attempt โดยไม่ทิ้ง pointer ไป raw trace | Markdown + YAML front matter |
| Attributor | ระบุ decision/step ที่นำไปสู่ success/failure | structured LLM output + verifier evidence |
| Skill compiler | แปลงหลาย episode เป็น procedure | Markdown skill schema |
| Skill registry | activate/merge/deprecate/version | folder + index JSON |
| Retriever | เลือก skill/lesson | lexical + metadata scoring; ไม่ต้อง vector DB |
| Capsule builder | จัด context ตาม token budget | deterministic priority packing |
| Reporter | แสดงให้คนอ่าน | static HTML generated from canonical files |

### Skill schema ขั้นต่ำ

```yaml
id: skill_cli_test_then_patch_v1
status: candidate       # candidate|verified|deprecated
activation:
  task_types: [bug_fix]
  signals: [existing_test_suite]
preconditions:
  - repository is writable
procedure:
  - reproduce failure
  - add or identify failing test
  - make smallest patch
  - run focused then full tests
termination:
  - targeted and regression tests pass
failure_modes:
  - test does not reproduce issue
evidence:
  episode_ids: [ep_001, ep_014]
  verifier_results: [pass, pass]
confidence: 0.78
```

### Token-bounded capsule

ลำดับ packing ที่แนะนำ:

1. task contract และ safety constraints
2. relevant verified skills
3. open subgoals/state
4. failure warnings ที่ match task
5. pointers ไป evidence; raw trace ใส่เฉพาะเมื่อ budget เหลือ

ใช้ 3 budget: 1k, 2k และ 4k tokens เพื่อสร้าง cost-quality curve

## Full profile

Full ใช้ schema และ core loop เดียวกับ Lite แล้วเปิด plugin เพิ่ม:

| Full module | เพิ่มอะไร | คำถาม ablation |
|---|---|---|
| Hybrid retrieval | lexical + embedding + reranker | vector ช่วยมากกว่า metadata หรือไม่ |
| Typed temporal KG | entity/relation/time/conflict | graph ช่วย multi-hop/temporal มากเท่าไร |
| Proactive intervention | memory agent เลือกเตือนหรือเงียบ | always-on retrieval สู้ selective reminder ได้ไหม |
| Scheduled consolidation | replay, merge, prune, confidence update | consolidation คุ้ม background tokens หรือไม่ |
| Multimodal memory | image OCR/caption/region pointer | visual track ช่วยเฉพาะ task ที่ต้องใช้ภาพหรือไม่ |
| Cross-project transfer | global skill pool + scope rules | abstraction ลด negative transfer หรือไม่ |
| Adaptive budget | เลือก capsule budget ตาม uncertainty | ประหยัด token โดยไม่เสีย success หรือไม่ |

## Lite กับ Full คล้ายกันแค่ไหน

ความสามารถหลักเหมือนกัน: capture, consolidate, retrieve, update, provenance และ token budget สิ่งที่ต่างคือ **กลไกและ coverage** ดังนั้นควรทดสอบบน benchmark เดียวกัน แต่ Full มี stress tracks เพิ่มเพื่อพิสูจน์ว่าความซับซ้อนที่เพิ่มมีเหตุผล

## Functional brain analogy

ใช้ mapping ต่อไปนี้เพื่อการสื่อสารเท่านั้น:

| Analogy | System function | Canonical folder |
|---|---|---|
| sensory gateway | รับข้อมูลและ validate | `inbox/` |
| episodic/hippocampal analogue | เก็บเหตุการณ์ตามเวลา | `memory/episodes/` |
| semantic analogue | facts/concepts ที่ consolidate | `memory/concepts/` |
| procedural/basal-ganglia analogue | skill/action policy | `memory/skills/` |
| visual/occipital analogue | image descriptors + original pointers | `memory/visual/` |
| executive/frontal analogue | goals, retrieval, inhibition, budget | `policies/` + capsule builder |
| sleep-like consolidation | replay/merge/prune | scheduled consolidation job |

ไม่ควรตั้งชื่อ folder ว่า `frontal-lobe` สำหรับ text memory เพราะ frontal lobe ไม่ใช่ที่เก็บ text memory โดยตรง ถ้าชอบธีมสมอง ให้ทำ aliases ใน HTML แต่คงชื่อ canonical ที่อธิบาย function ได้

## ความต่างจาก Prompt 01/02 ของอาจารย์

| มิติ | Wiki Prompt 01/02 | Experience Brain |
|---|---|---|
| เป้าหมายหลัก | จัด artifact/experiment/wiki | เรียนรู้ procedure จาก trajectory |
| หน่วยความจำ | source/version/page/lesson | event/episode/skill/state |
| trigger | user สั่ง process/synthesize | event และ verifier outcome |
| lifecycle | ingest/completeness/lesson promotion | candidate/verify/merge/deprecate/transfer |
| retrieval | agent อ่าน index/pages | budgeted retrieval policy + optional proactive reminder |
| evaluation | completeness และ experiment metrics | same benchmark across memory conditions |
| token accounting | ไม่ใช่แกนหลัก | first-class total cost incl. consolidation |
| interface | Obsidian-style Markdown | canonical Markdown + generated HTML |

Wiki ของอาจารย์สามารถเป็น baseline และยังนำ pattern ที่ดีมาใช้ได้ เช่น immutable raw sources, provenance, weak relation, completeness lint และ human approval

