# เริ่มต้นสำหรับผู้ใช้ที่ไม่ใช่นักพัฒนา

## คำตอบสั้นที่สุด

เริ่มด้วย **Codex Terra + High** ได้ แต่ใช้มันสร้าง Lite และรัน pilot ก่อน อย่าเริ่ม Full ทันที งานวิจัยที่น่าเชื่อถือเกิดจากการล็อก benchmark, baseline และการเก็บ metric ให้ถูกต้องก่อนเพิ่มระบบซับซ้อน

ตามคู่มือ Codex ปัจจุบัน Terra เหมาะกับงานเร็ว/ประหยัด เช่น scan, อ่านไฟล์จำนวนมาก และงาน support; งานออกแบบหรือแก้ปัญหาหลายขั้นที่ยากมากเหมาะกับรุ่นหลักที่ reasoning สูงกว่า ดังนั้น:

- **Terra High:** bootstrap repo, literature ingestion, Lite implementation, pilot และงาน routine
- **รุ่นหลัก High/Extra High:** architecture review, debugging ยาก, statistical analysis และ final manuscript
- ใน benchmark หลักต้องใช้ **model + reasoning เดียวกันทุก condition** เพื่อไม่ให้ model เป็นตัวแปรกวน

## สิ่งที่ต้องมี

- Git และ GitHub account
- Codex CLI หรือ Codex ใน desktop app
- Docker Desktop สำหรับ benchmark ที่ใช้ container
- Python 3.11+ และ Node.js 20+ (ให้ Codex ตรวจและติดตั้ง dependency ใน repo)
- พื้นที่ว่างอย่างน้อย 20–40 GB หากรัน Terminal-Bench
- API/ChatGPT budget ที่ตั้งเพดานรายวันได้

ถ้าเครื่องไม่พร้อม ให้เริ่มเฉพาะ unit tests และ BrainBench-Mini ในสัปดาห์แรกก่อน

## 60 นาทีแรก

1. สร้าง GitHub repo ส่วนตัวชื่อ `experience-brain` และ clone ลงเครื่อง
2. เปิด folder นั้นด้วย Codex
3. เลือก Terra และ High
4. เปิด Plan mode แล้ววาง `Prompt 0` จาก `CODEX_RUNBOOK.md`
5. ให้ Codexตรวจ environment แบบ read-only และสร้าง `ENVIRONMENT_REPORT.md`
6. วาง `Prompt 1` เพื่อ scaffold Lite โดยยังไม่ลง vector database หรือ knowledge graph
7. ให้ Codexรัน tests และ `/review`
8. commit เป็น `v0.1.0-lite-scaffold`

## กฎ 7 ข้อสำหรับคุณในฐานะ Principal Investigator

1. ไม่กดรับการเปลี่ยนแปลงจนกว่าจะเห็น `tests passed` และ diff summary
2. ไม่อนุญาตให้ agent เขียนคะแนน benchmark เอง ต้องมาจาก verifier
3. ทุก experiment ต้องมี `run_id`, model, reasoning, commit SHA, seed, task ID และ token counts
4. ห้ามใส่ข้อมูลผู้ป่วย/ใบสั่งยา/PII จริงในระบบทดลอง
5. ห้ามเปลี่ยน prompt หรือ budget ระหว่าง conditions หลังเริ่ม benchmark
6. ถ้า agent ทำผิดซ้ำ ให้เพิ่ม regression test ก่อนเพิ่มกฎใน `AGENTS.md`
7. เก็บ negative results เพราะมีค่าต่อ paper มากกว่าการเลือกเฉพาะรอบที่ดีที่สุด

## Milestone แรกที่ควรได้

ภายใน 1–2 สัปดาห์ Lite ต้องทำได้เพียง 5 อย่าง:

1. รับ trajectory/event
2. สร้าง episode แบบมี provenance
3. สกัด lesson/skill candidate
4. verify, merge, deprecate และเลือก skill ที่เกี่ยวข้อง
5. สร้าง context capsule ที่มี token budget ตายตัว

ถ้า 5 อย่างนี้ยังทดสอบไม่ได้ อย่าเพิ่ม image memory, graph database หรือ background agents

## คำสั่งรายวัน

```text
อ่าน AGENTS.md และ EXPERIMENT_PLAN.md ก่อน ทำเฉพาะ milestone ปัจจุบัน
สรุป goal, files ที่จะเปลี่ยน, tests และ done criteria ก่อนแก้ไฟล์
หลังแก้ให้รัน tests, ตรวจ diff, รายงานความเสี่ยง และหยุดถ้า benchmark protocol ต้องเปลี่ยน
```

## จุดตัดสินใจ Go / No-Go

- ไป Lite benchmark เมื่อ unit/integration tests ผ่านและ provenance ไม่ขาด
- ไป Full เมื่อ Lite ชนะ no-memory ใน `tokens_per_success` และไม่ทำ success rate แย่ลงเกิน 2 percentage points
- หยุดหรือ redesign ถ้า Wiki baseline ดีกว่า Lite อย่างสม่ำเสมอ หรือ background token สูงจน total cost แพงกว่า raw context

## Official Codex references

- <https://learn.chatgpt.com/guides/best-practices>
- <https://learn.chatgpt.com/docs/models>
- <https://learn.chatgpt.com/docs/config-file/config-basic>
