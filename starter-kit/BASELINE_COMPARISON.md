# Baseline Comparison: Wiki vs Autoresearch vs Lite vs Full

## หน้าที่ของแต่ละระบบ

| System | Core loop | Memory unit | Optimizes | จุดแข็ง | จุดที่ยังไม่ตอบคำถามวิจัยนี้ |
|---|---|---|---|---|---|
| Prompt 01/02 Wiki | inbox→classify→wiki→synthesize | source/version/page/lesson | organization + provenance | audit ง่ายและคนอ่านดี | ไม่ได้บังคับ skill lifecycle หรือ frozen transfer evaluation |
| Autoresearch | inspect code→modify→run→score→keep/revert | experiment result + code state | measurable objective | search loop ง่ายและ feedback ชัด | ไม่ใช่ general cross-session memory และไม่เน้น token-bounded retrieval |
| Experience Brain Lite | event→episode→skill→capsule→outcome | verified procedural skill | success + transfer + token efficiency | ลีนและทดสอบ causal contribution ได้ | retrieval/coverage จำกัดเมื่อ memory ใหญ่หรือ multimodal |
| Experience Brain Full | Lite + hybrid retrieval/consolidation/intervention/KG | typed multi-memory | long-horizon adaptive performance | รองรับ scale, temporal, multimodal, selective reminder | ซับซ้อน แพง และเสี่ยง memory poisoning/clutter |

## ทำไมต้องใช้ Wiki เป็น baseline

Wiki เป็น strong baseline ไม่ใช่ strawman เพราะมี immutable raw, provenance, version detection, completeness lint, lesson lifecycle และ synthesis จากหลายแหล่ง สิ่งที่ต้องทำคือ freeze prompt/schema และคิด token ที่ใช้ดูแล wiki เข้า cost ด้วย

## ทำไม Autoresearch ไม่ใช่คู่แข่งตรง

Autoresearch คือ experiment optimizer ที่มี evaluator loop ส่วน Experience Brain คือ memory layer ที่ควรเสียบเข้า agent/optimizer ใดก็ได้ การทดลองที่น่าสนใจในอนาคตคือให้ autoresearch เป็น action/experiment loop แล้วเปรียบเทียบ:

- autoresearch เดิม
- autoresearch + raw history
- autoresearch + Lite
- autoresearch + Full

ใช้ objective และ experiment budget เดียวกัน วัด best score over budget, duplicate experiments, time-to-improvement และ total tokens

## Shared capability vs implementation

Lite และ Full ควรใช้ interface เดียว:

```text
record(event)
close_episode(outcome)
consolidate(scope)
retrieve(task, budget)
observe_effect(memory_ids, outcome)
```

ดังนั้น benchmark harness ไม่ต้องรู้ว่า backend เป็น Markdown lexical หรือ graph/vector เพียงสลับ profile config ช่วยให้ comparison เป็นธรรมและ repo ไม่แตกเป็นสองโครงการ

## HTML vs Obsidian

- Obsidian เป็น editor/viewer ที่ดีแต่เพิ่ม app dependency
- HTML static report เปิดได้ทุกเครื่อง แชร์ง่ายและสร้าง dashboard/filter ได้
- canonical memory ยังควรเป็น Markdown/YAML/JSONL เพราะ diff, version control และ agent parsing ง่ายกว่า
- สรุป: **เปลี่ยน UI เป็น HTML ได้ แต่ไม่ควรเปลี่ยน storage เป็น HTML**

## Decision rule

- ถ้า Lite ชนะหรือเท่า Full ภายใต้ CI และใช้ token/latency ต่ำกว่า ให้เลือก Lite เป็น default
- ถ้า Full ชนะเฉพาะ long-horizon/multimodal ให้ใช้ adaptive profile ไม่เปิดทุก module ทุก task
- ถ้า Wiki ชนะ Lite ให้ศึกษาว่า loss เกิดจาก skill abstraction หรือ retrieval ก่อนเพิ่ม graph
- ถ้า raw trajectories ชนะ skills ให้แก้ compiler/provenance gate ไม่ใช่เพิ่มจำนวน skill

