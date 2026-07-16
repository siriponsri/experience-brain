# Research Questions, Hypotheses และ Contribution

## Working title

**From Context to Experience: A Token-Bounded Procedural Memory Architecture for Cross-Session CLI Agents**

## Problem statement

LLM agents มักเก็บอดีตเป็น conversation history, summary, wiki หรือ retrieved chunks แต่การ “เคยทำ” ไม่เท่ากับการ “เรียนรู้วิธีทำ” งานนี้ศึกษาว่า pipeline ที่แปลง execution trajectory เป็น episodic records และ verified procedural skills จะทำให้ session ใหม่ทำงานดีขึ้นและใช้ token ต่อความสำเร็จน้อยลงได้หรือไม่

## Research questions

- **RQ1 — Effectiveness:** Experience Brain เพิ่ม deployment task success เหนือ no-memory และ Wiki baseline หรือไม่
- **RQ2 — Efficiency:** ระบบลด `tokens_per_success` เมื่อรวม background consolidation แล้วหรือไม่
- **RQ3 — Transfer:** skill ที่สกัดจาก acquisition tasks ใช้กับ task ใหม่, domain ใหม่ หรือ model ใหม่ได้แค่ไหน
- **RQ4 — Error recurrence:** ระบบลดการทำ failure pattern ซ้ำโดยไม่เพิ่ม negative transfer หรือไม่
- **RQ5 — Complexity:** Full modules ให้ประโยชน์เพิ่มเหนือ Lite มากพอคุ้ม token, latency และ engineering complexity หรือไม่
- **RQ6 — Intervention:** การเลือกเวลาที่ควรเตือนดีกว่า always-on memory injection หรือไม่

## Preregistered hypotheses

- **H1:** Lite มี deployment success สูงกว่า no-memory
- **H2:** Lite มี tokens_per_success ต่ำกว่า Wiki และ raw-trajectory reuse
- **H3:** verified skills transfer ดีกว่า unverified lessons และ raw trace ใน frozen deployment
- **H4:** Full hybrid retrieval + selective intervention ชนะ Lite ใน long-horizon tasks แต่ไม่จำเป็นต้องชนะในงานสั้น
- **H5:** provenance gate ลด harmful/incorrect memory activation
- **H6:** Full ที่ไม่มี pruning จะเกิด memory clutter และประสิทธิภาพตกเมื่อจำนวน episodes เพิ่ม

ทุก hypothesis ต้องมี null, primary metric, comparison, split และ analysis method ใน preregistration

## Intended contribution

1. architecture กลางที่ใช้ schema เดียวจาก Lite ไป Full
2. operational definition ของ experience เป็น verified reusable procedure ไม่ใช่เพียง stored context
3. benchmark protocol ที่เปรียบเทียบ no-memory, research wiki, Lite และ Full บน task/model/budget เดียวกัน
4. total token accounting ที่รวม extraction, consolidation, retrieval และ failed attempts
5. open screening corpus และ literature taxonomy สำหรับ agent memory/procedural skill/long-horizon research agents

## สิ่งที่ไม่ควร claim

- ไม่ claim ว่าเป็น digital human brain
- ไม่ claim continual learning ในระดับ model parameters หากไม่ได้ fine-tune
- ไม่ใช้คำว่า “understands” เป็น metric; ใช้ observable task performance
- ไม่สรุปว่า Full ดีกว่า Lite หากชนะเพราะใช้ token หรือ model มากกว่า
- ไม่สรุป general intelligence จาก benchmark เดียว

## Operational definitions

- **Event:** action/observation/tool/result หนึ่งรายการพร้อมเวลาและ cost
- **Episode:** bounded attempt ที่มี goal, trajectory pointers, outcome และ attribution
- **Lesson:** descriptive insight ที่ยังไม่รับรองว่า execute ได้
- **Skill:** procedure ที่มี activation, preconditions, steps, termination, evidence และ lifecycle
- **Experience:** episode ที่ถูกใช้เพื่อเปลี่ยนการตัดสินใจครั้งต่อไปและสามารถวัดผลของการเปลี่ยนนั้นได้
- **Memory integrity:** ความถูกต้อง, provenance, conflict handling, scope และ lifecycle ของ memory

## Paper framing

งานมี novelty มากที่สุดเมื่อวางที่จุดตัดของ:

- procedural memory from trajectories
- budgeted/selective memory intervention
- cross-session CLI agents
- cost-aware empirical comparison against a human-oriented research wiki

หาก literature review พบงานที่ทำทั้งสี่จุดแล้ว ให้ลด claim เป็น replication + controlled comparison + open reproducibility contribution

