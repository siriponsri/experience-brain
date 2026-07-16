# Literature Review Index

## Review objective

หาคำตอบว่าเคยมีระบบใดทำครบทั้ง 4 อย่างหรือยัง:

1. เปลี่ยน execution trajectory เป็น procedural knowledge
2. ใช้ข้าม session/task และมี lifecycle update/forget/deprecate
3. ส่ง memory กลับเข้า action agent ภายใต้ token budget หรือ selective intervention
4. ประเมินด้วย task outcome + total token cost เทียบกับ no-memory/raw-context/wiki baseline

หากมีงานทำครบ ให้ปรับ novelty ไปที่ controlled comparison, lightweight-to-full continuum, Wiki baseline, total-cost accounting หรือ healthcare-domain transfer

## Corpus

- `references/literature_catalog.csv` — portable source of truth
- `references/literature_catalog.xlsx` — workbook สำหรับ filter/screen/tag
- Core 30 — อ่าน full text ก่อน
- benchmark/method candidates — abstract screen แล้วคัดตามเกณฑ์

## Taxonomy

### A. Cognitive and memory foundations

external memory, episodic/semantic/procedural distinction, working memory, consolidation, forgetting, interference และ dual-process control

### B. Agent memory architectures

memory stream, hierarchical memory, OS-style memory, temporal/graph memory, local-first memory, multimodal memory และ learned memory manager

### C. Experience → skill

reflection, trajectory attribution, skill extraction, skill lifecycle, verification, cross-task/model transfer และ negative transfer

### D. Retrieval and token efficiency

RAG, compression, selective context, long-context failure, capsule budget, reranking และ proactive intervention

### E. Benchmarks

long-term conversation, incremental memory, agentic multi-session tasks, procedural skills, terminal/coding, long-horizon diagnosis และ research workflows

### F. Autonomous research and self-improvement

experiment loops, evaluator-guided search, scientific agents, prompt/program optimization และ reproducible research automation

## Screening criteria

### Include

- primary research paper/official technical report
- อธิบาย memory/experience/skill mechanism หรือ benchmark ที่เกี่ยวข้องโดยตรง
- มี architecture หรือ evaluation ที่ extract ได้
- ภาษาอังกฤษ; full text หรือ detailed preprint เข้าถึงได้
- 2014–2026 สำหรับ neural/LLM memory; งาน cognitive คลาสสิกเพิ่มได้โดย snowballing

### Exclude

- blog/product page ที่ไม่มี technical evidence
- งาน long context ที่ไม่มีนัยต่อ memory/retrieval เลย
- paper ซ้ำหลาย version ให้เก็บ canonical version เดียว
- benchmark ที่ไม่มี task/data/harness description เพียงพอ
- claim จาก secondary survey โดยไม่ตามไป primary source

## Search strings

```text
("LLM agent" OR "language agent") AND (memory OR experience) AND
(procedural OR skill OR trajectory OR consolidation)

(agent memory) AND (benchmark OR evaluation) AND
(multi-session OR long-horizon OR transfer)

(coding agent OR terminal agent) AND
(persistent memory OR skill library OR self-evolving)

(context compression OR selective retrieval OR proactive memory) AND
(token cost OR efficiency)
```

Databases: arXiv, ACL Anthology, ACM DL, IEEE Xplore, Semantic Scholar, Google Scholar และ references/citations ของ survey หลัก บันทึกวันที่ค้นและ query จริงทุกครั้ง

## Data extraction form

ต่อ paper ให้กรอก:

- citation, year, venue, URL, code/data
- memory unit และ storage
- write trigger / update / forget / conflict
- retrieval query/ranking/intervention
- provenance/verification
- benchmark/tasks/models/budget
- metrics รวม token/latency หรือไม่
- baselines/ablations
- findings และ effect size
- limitations/threats
- relation to Lite/Full module
- claim ที่ paper ของเราสามารถอ้างได้

## Core 30 reading order

### รอบ 1 — Frame (6)

CoALA, Generative Agents, MemGPT, Reflexion, ExpeL, Voyager

### รอบ 2 — Modern memory systems (8)

HippoRAG, A-MEM, Zep, Mem0, MemoryOS, MIRIX, SimpleMem, CraniMem

### รอบ 3 — Procedural experience (8)

Memp, Skill-Pro, SkillEvolBench, CODESKILL, MUSE-Autoskill, Trajectory-Informed Memory, Retrieval-Augmented LLM Agents, Memory Transfer Learning

### รอบ 4 — Evaluation and long horizon (6)

MemoryAgentBench, MemoryArena, MemGym, Terminal-Bench 2.0, LongCLI-Bench, HORIZON

### รอบ 5 — Research loops (2)

The AI Scientist-v2, AlphaEvolve

## Review matrix ที่ต้องสร้างก่อนเขียน Related Work

| Paper | Unit | Write | Consolidate | Retrieve/intervene | Verify | Transfer | Total tokens | Open code |
|---|---|---|---|---|---|---|---|---|
| ... | ... | ... | ... | ... | ... | ... | ... | ... |

## Weekly workflow

- อ่าน Core 5 ฉบับ/สัปดาห์
- extract เป็น structured row ทันที ไม่เขียนสรุปยาวก่อน
- ทุก 10 ฉบับ เขียน synthesis memo 1 หน้า: consensus, conflict, gap
- snowball references เฉพาะที่เติมช่องว่าง taxonomy
- freeze review search ก่อน final analysis และทำ update search อีกครั้งก่อน submission

## PRISMA-style record

เก็บจำนวน identified, deduplicated, title/abstract screened, full-text assessed, included และ exclusion reasons แม้งานนี้ไม่ใช่ medical systematic review เต็มรูปแบบ วิธีนี้เหมาะกับพื้นฐานเภสัชกรและช่วยให้กระบวนการโปร่งใส

## Warning

รายการใน catalog เป็น starting corpus ไม่ใช่ evidence synthesis สำเร็จแล้ว Paper ปี 2025–2026 จำนวนมากเป็น preprint ควรตรวจ version/venue/code availability อีกครั้ง ณ วันที่เขียน manuscript

