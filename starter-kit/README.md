# Experience Brain — Research Starter Kit

ชุดเริ่มต้นสำหรับสร้างและประเมิน **ระบบความจำจากประสบการณ์ของ AI agent** แบบ Lite → Full โดยใช้ repo เดียวและ benchmark เดียวกัน เพื่อแยกให้ได้ว่าความจำช่วยจริงหรือเพียงเพิ่ม context และ token

## ข้อสรุปการออกแบบ

- เริ่มด้วย **Lite** แต่ใช้ schema กลางที่อัปเกรดเป็น Full ได้ ไม่แยกสอง repo
- ใช้ **SkillEvolBench** เป็น benchmark หลัก เพราะวัดการเปลี่ยน episodic experience เป็น procedural skill โดยตรง
- ใช้ **Terminal-Bench 2.0** เป็น external-validity benchmark สำหรับงาน CLI จริง
- เปรียบเทียบ 4 เงื่อนไข: no memory, ระบบ Wiki/Prompt 01–02, Lite, Full
- วัดทั้งคุณภาพและต้นทุน: success, transfer, repeated errors, input/output/background tokens, latency และ tokens per success
- Markdown/YAML/JSONL เป็น canonical data; HTML เป็น generated interface สำหรับคน ไม่ใช้ HTML เป็น memory store
- `markdownify-mcp` เป็น ingestion adapter สำหรับแปลงไฟล์ ไม่ใช่สมองหรือฐานความจำ
- คำว่า hippocampus/frontal/occipital ใช้เป็น **functional analogy** เท่านั้น ไม่อ้างว่าเป็นแบบจำลองชีววิทยาของสมองจริง

## อ่านตามลำดับนี้

1. `START_HERE.md` — เริ่มรอบแรกด้วย Codex Terra High
2. `RESEARCH_QUESTION_AND_HYPOTHESES.md` — คำถามวิจัยและสมมติฐาน
3. `ARCHITECTURE_LITE_TO_FULL.md` — ระบบ Lite และ Full
4. `BASELINE_COMPARISON.md` — Wiki, Autoresearch, Lite และ Full
5. `BENCHMARK_PROTOCOL.md` — benchmark, baselines และ metrics
6. `EXPERIMENT_PLAN.md` — แผน 12 สัปดาห์และเกณฑ์ผ่านแต่ละ gate
7. `CODEX_RUNBOOK.md` — prompt ที่ copy ไปใช้ได้ทีละ phase
8. `LITERATURE_REVIEW_INDEX.md` และ `references/literature_catalog.*`
9. `PAPER_ROADMAP.md` และ `paper/MANUSCRIPT_TEMPLATE.md`
10. `MARKDOWNIFY_MCP_INTEGRATION.md` — ติดตั้งและเชื่อม ingestion อย่างปลอดภัย
11. `DATA_ETHICS_AND_REPRODUCIBILITY.md` — privacy, leakage และ reproducibility

## Research claim ที่ควรตั้ง

> A bounded, provenance-preserving consolidation pipeline that converts agent trajectories into verified procedural skills can improve cross-session task performance and reduce tokens per successful task compared with raw-context reuse and an LLM-maintained research wiki.

อย่าตั้ง claim ว่า “เลียนแบบสมองมนุษย์” จนกว่าจะมีผู้เชี่ยวชาญ neuroscience ร่วมออกแบบและมีการทดสอบเชิงชีววิทยา งานฉบับแรกควรเรียกแนวคิดนี้ว่า **neurocognitively inspired functional architecture**

## Definition of done ของงานวิจัยฉบับแรก

- benchmark protocol ถูก freeze ก่อนดูผล Full
- รันครบ 4 เงื่อนไขด้วย task split, model และ budget เดียวกัน
- มีอย่างน้อย 3 independent runs ต่อ condition ในชุดหลัก
- รายงาน token ทั้ง foreground และ background consolidation
- มี ablation อย่างน้อย 4 ตัว
- ปล่อย code, config, task manifest, raw metrics และ analysis script
- manuscript มี limitations, negative results และ threat-to-validity

## สถานะของคลังเอกสาร

`references/literature_catalog.csv` และ `.xlsx` เป็น **screening corpus 114 papers + 2 system references** ตรวจรวบรวมถึงวันที่ 2026-07-16 ไม่ได้หมายความว่าอ่าน full text แล้วทั้งหมด คอลัมน์ `screening_stage` ใช้ติดตามว่า paper ใดเป็น Core 30, priority, abstract-screen หรือ system review
