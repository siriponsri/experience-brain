# OWNER_GUIDE_TH.md — คู่มือเจ้าของ Experience Brain

## 1. ระบบนี้คืออะไร

Experience Brain คือระบบที่ช่วยให้ AI Agent เก็บ “ประสบการณ์จากการลงมือทำจริง” ข้าม session ได้

ระบบไม่ได้เก็บเพียงประวัติการคุย แต่เก็บว่า:

- งานมีเป้าหมายอะไร
- Agent ทำอะไร
- ใช้เครื่องมือใด
- พบ error อะไร
- ตัดสินใจอย่างไร
- ผลสำเร็จหรือล้มเหลว
- owner ให้ feedback อะไร
- มีบทเรียนใดที่ควรนำกลับมาใช้

ข้อมูลต้นฉบับเก็บใน JSONL และทุกบทเรียนต้องย้อนกลับไปดูเหตุการณ์จริงได้

## 2. วิธีใช้งานหลัก

คุณจะใช้งานผ่าน **Codex CLI เป็นหลัก**

Runtime ที่เลือกไว้:

- โมเดลหลัก: GPT-5.5
- reasoning effort ปกติ: medium
- เพิ่มเป็น high เฉพาะงาน debugging หรือ architecture ที่ medium ทำไม่สำเร็จ

ระบบต้องบันทึกว่าแต่ละ session ใช้ Agent, model และ reasoning effort อะไรจริง

## 3. คำสั่งหลักที่ควรจำ

### `process session`

ใช้เมื่อ:

- ต้องการประมวลผล session ล่าสุด
- session จบไม่สมบูรณ์
- นำ trace เก่าเข้าระบบ
- ต้องการสกัด Experience ใหม่อีกครั้ง

ตัวอย่าง:

```text
process session
```

### `query experience: <คำถาม>`

ใช้ถามประสบการณ์เดิมที่เกี่ยวข้อง

ตัวอย่าง:

```text
query experience: ก่อนหน้านี้เราเคยแก้ test failure ลักษณะนี้อย่างไร
```

คำตอบควรบอกว่า Experience มาจาก project, session และเหตุการณ์ใด

### `review latest`

ใช้ตรวจ candidate Experience และรายงานของ session ล่าสุด

ตัวอย่าง:

```text
review latest
```

คุณควรเห็นรายการที่:

- ใช้ได้ทันที
- รอ owner ยืนยัน
- ควรแก้ไข
- ควรยกเลิกหรือแทนที่ของเดิม

## 4. คำสั่งรอง

```text
status
lint experience
dashboard
compare EXP-01 with EXP-02
```

- `status` — ดูสถานะระบบ รุ่นซอฟต์แวร์ experiment และ session ล่าสุด
- `lint experience` — ตรวจข้อมูลไม่ครบ ขัดแย้ง หรืออ้างอิงเหตุการณ์ไม่ได้
- `dashboard` — เปิด Web Dashboard ในเครื่อง
- `compare ...` — เปรียบเทียบแนวทางทดลองสองรุ่น

## 5. Workflow ปกติ

```text
1. เปิด Codex CLI ใน repo
2. สั่ง /plan พร้อมเป้าหมาย
3. Codex อ่าน AGENTS.md และ PROJECT_PLAN.md
4. Codex วางแผนและ implement ต่อ
5. ระบบเก็บ Events ระหว่างทำงาน
6. เมื่อ session จบ ระบบ consolidate อัตโนมัติ
7. สั่ง review latest
8. ตรวจหรือแก้ Candidate Experience
9. session ถัดไป Agent เรียก Experience ที่เกี่ยวข้องกลับมาใช้
```

`process session` เป็นคำสั่งสำรองเมื่อ automatic processing ไม่เกิดขึ้นหรืออยากประมวลผลใหม่

## 6. เมื่อใด Agent จะถามคุณ

Agent ควรถามเฉพาะเรื่องใหญ่หรือย้อนกลับได้ยาก เช่น:

- เปลี่ยน vision หรือ scope หลัก
- เปลี่ยน JSONL จากการเป็น source of truth
- เปลี่ยน architecture หลัก
- ลบหรือ migrate ข้อมูลจำนวนมาก
- เปลี่ยน license
- เปลี่ยนทิศทาง paper หรือ research claim

เรื่องเล็ก เช่น เลือก library, แก้ bug, จัดไฟล์ย่อย หรือเพิ่ม test ให้ Agent ตัดสินใจเองได้

## 7. ลำดับความน่าเชื่อถือ

เมื่อข้อมูลขัดกัน ระบบต้องใช้ลำดับนี้:

1. owner
2. project rule ที่ยัง active
3. feedback จากผลลัพธ์จริง
4. Experience ที่มีหลักฐานว่าสำเร็จซ้ำ

Experience จาก project อื่นใช้ได้ แต่ต้องติดป้าย **External Project Experience** และห้าม override กฎของ project ปัจจุบัน

## 8. ข้อมูลสามไฟล์หลัก

### `data/events.jsonl`

เก็บเหตุการณ์จริงทั้งหมด เช่น:

- user message
- agent message
- tool call
- tool result
- file change
- decision
- feedback
- error
- outcome
- session start/end

### `data/experiences.jsonl`

เก็บบทเรียนหรือขั้นตอนที่สกัดจาก Events เช่น:

- สถานการณ์
- เป้าหมาย
- วิธีที่ใช้
- ผลลัพธ์
- บทเรียน
- หลักฐาน event IDs
- จำนวนครั้งที่สำเร็จหรือล้มเหลว
- สถานะการยืนยัน

### `data/knowledge.jsonl`

เก็บข้อมูลที่อ่านหรือย่อยจากไฟล์ภายนอก เช่น เอกสารใน `inbox/`

- ชื่อไฟล์ต้นทาง
- hash ของเนื้อหา
- ชนิดไฟล์และตำแหน่งในไฟล์
- summary หรือ key facts
- provenance ของ Agent/model/runtime ที่ย่อยข้อมูล
- สถานะการยืนยันหรือยกเลิก

Knowledge ไม่ใช่ Experience อัตโนมัติ เอกสารภายนอกบอกว่า X คือ Knowledge
แต่ Agent ต้องลงมือทำและเห็นผลลัพธ์จริงก่อนจึงจะสร้าง Experience ได้

ห้ามแก้ประวัติเดิมแบบลบเงียบ ๆ การแก้ไขต้องสร้าง record ใหม่ที่ระบุว่าแทนที่หรือยกเลิก record ใด

## 9. การตรวจ Candidate Experience

ระบบจะสร้าง Candidate อัตโนมัติหลังจบ session

- หลักฐานชัดและความมั่นใจสูง: เปิดใช้ได้
- สำคัญแต่ยังไม่แน่ใจ: เข้า review queue
- owner ยืนยันหรือแก้ไขได้
- ห้ามสร้าง lesson ที่ไม่มี raw episode รองรับ

สถานะบทเรียนอาจเป็น:

```text
proposed → confirmed → refined → retired
```

## 10. Software Version, Experiment และ Run

สามอย่างนี้ไม่ใช่สิ่งเดียวกัน

### Software version

ตัวอย่าง:

```text
v0.2.0
```

บอกว่าตัวโปรแกรมรุ่นนี้ทำอะไรได้

### Experiment index

ตัวอย่าง:

```text
EXP-02
```

บอกว่ากำลังทดลองแนวคิดหรือ configuration แบบใด

### Run ID

ตัวอย่าง:

```text
RUN-003
```

บอกว่าเป็นการรันซ้ำครั้งใดของ experiment นั้น

ข้อมูลหนึ่งชุดอาจเขียนว่า:

```text
Software: v0.2.0
Experiment: EXP-02
Run: RUN-003
```

## 11. Dashboard

Dashboard เป็น local single-owner app ไม่ต้องมี login ใน POC แรก

ควรใช้เพื่อ:

- ดู session และ timeline
- ดู Events และ Experiences
- ค้นหาและกรอง
- ตรวจ raw JSONL
- ยืนยันหรือแก้ Experience
- supersede, invalidate หรือ retire ข้อมูลเก่า
- ดูว่า Experience ใดถูกนำกลับไปใช้
- ดู software version, experiment และ run
- export Markdown review report

## 12. ความปลอดภัยของข้อมูล

ระบบต้องกรองก่อนบันทึก:

- API keys, passwords และ secrets
- `.env` และ credential
- ข้อมูลส่วนบุคคล
- ข้อมูลผู้ป่วย
- benchmark solutions หรือข้อมูลเสี่ยง leakage
- hidden chain-of-thought

ข้อมูลที่ถูกกรองให้แทนด้วย `[REDACTED]` และบันทึกเหตุผลไว้

## 13. การ Reframe Repo

เมื่อเริ่ม restructure จริง ให้ Agent ทำตามลำดับ:

1. tag ของเดิมเป็น `pre-reframe-v0.1.0`
2. ตรวจว่า tag ใช้งานได้
3. เก็บ Git history
4. ตัด benchmark/wiki structure เดิมออกจาก `main`
5. ไม่สร้าง legacy folder ใหญ่
6. สร้าง `docs/LEGACY.md` ชี้กลับไปยัง tag
7. สร้างโครงสร้างใหม่แบบลีน
8. รัน test ก่อนและหลังการเปลี่ยนแปลง

ยังไม่ควรทำขั้นตอนนี้จนกว่าคุณจะสั่งเริ่ม implementation โดยตรง

## 14. รายงานที่ควรได้รับหลัง Agent ทำงาน

Agent ต้องสรุปเพียง 4 ส่วน:

1. ทำอะไรเสร็จแล้ว
2. ทดสอบอะไรและผลเป็นอย่างไร
3. มีปัญหาหรือความเสี่ยงอะไร
4. ควรสั่งอะไรต่อ

## 15. ลำดับงานหลัง 7-Day POC

1. สร้างระบบให้ครบวงจร
2. เลือก benchmark dataset ที่มีอยู่แล้ว
3. เปรียบเทียบ Agent ไม่มี Experience กับ Agent มี Experience
4. ทำ ablation และวิเคราะห์ผล
5. เขียน paper และเผยแพร่บน arXiv
6. หลังจากนั้นจึงทดลองกับ LabLoop และ ThaiPhaLex
## 16. Knowledge Inbox

ระบบมีความจำสองแบบที่ต้องแยกกัน:

- Knowledge = สิ่งที่ Agent อ่านจากไฟล์หรือแหล่งข้อมูล
- Experience = สิ่งที่ Agent ลงมือทำจริงและเห็นผลลัพธ์จริง
- Rules = กฎที่ owner หรือ project กำหนด
- Working Context = เรื่องที่สำคัญในงานปัจจุบัน

ไฟล์จาก paper, เอกสาร, spreadsheet หรือ source code จะกลายเป็น Knowledge
ไม่ใช่ Experience โดยอัตโนมัติ

workflow แบบ low-code:

```text
วางไฟล์ใน inbox/
-> สั่ง process inbox
-> เปิด Dashboard
-> ดูแท็บ Inbox และ Knowledge
-> session ถัดไป Agent ค้นคืน Knowledge ได้
```

หรือใช้ Dashboard:

```text
experience dashboard
-> Inbox
-> Upload Files
-> Process Inbox
-> ตรวจ Knowledge
```

ไฟล์ที่รองรับในรอบนี้: `.md`, `.txt`, `.json`, `.jsonl`, `.yaml`, `.yml`,
`.csv`, source-code text files, text-based `.pdf`, `.docx`, และ `.xlsx`

ถ้าไฟล์ซ้ำ ระบบจะตรวจด้วย content hash และไม่สร้าง Knowledge ซ้ำแบบเงียบ ๆ
ถ้าไฟล์ยังไม่รองรับ อ่านไม่ได้ สแกนเป็นรูปภาพ เข้ารหัส หรือเป็น audio/video
ระบบจะแสดงสถานะเช่น `unsupported`, `needs_extractor`, หรือ `error`
