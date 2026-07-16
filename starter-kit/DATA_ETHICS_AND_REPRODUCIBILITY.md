# Data, Ethics, Safety และ Reproducibility

## สำหรับผู้วิจัยที่เป็นเภสัชกร

งานระยะแรกเป็น software-agent research ไม่ใช่ clinical study อย่านำข้อมูลผู้ป่วย, prescription, hospital documents, LINE chats, images หรือข้อมูลที่ระบุตัวบุคคลได้เข้า repo แม้จะตั้ง private

ถ้าจะทำ healthcare extension ภายหลัง ต้องแยก protocol ใหม่และตรวจ IRB/EC, PDPA, data-use agreement, clinical safety และ human oversight ตามสถาบัน/ประเทศ

## Data classes

| Class | Example | Allowed now |
|---|---|---|
| public benchmark | official task containers | yes ตาม license |
| synthetic fixtures | generated fake events | yes |
| public papers/docs | licensed/open source | yes เก็บ metadata; เคารพลิขสิทธิ์ |
| private source code | employer/personal repo | แยกจาก release และขอสิทธิ์ |
| patient/PII/PHI | prescriptions, records | no |
| secrets | API keys/tokens | no in repo |

## Prompt injection threat

PDF/webpage/repository อาจมีข้อความสั่ง agent ให้เปิดเผยข้อมูลหรือรันคำสั่ง ให้ label converted content เป็น `untrusted_external_content` และห้ามยกระดับเป็น instruction/skill โดยไม่มี evidence + policy gate

## Memory poisoning

- skill candidate ต้องมี source episodes และ verifier outcome
- conflicting evidence ลด confidence หรือสร้าง review queue
- candidate จาก failure เดียวห้าม promote เป็น verified
- skill ที่ทำให้ negative transfer ต้อง deprecate แต่ไม่ลบ audit trail
- benchmark memory store เป็น isolated disposable directory

## Reproducibility manifest

ทุก run ต้องบันทึก:

- timestamp/timezone
- exact model ID และ reasoning effort
- Codex/harness/package/container versions
- repo commit SHA และ dirty state
- task manifest hash
- condition/profile/config hash
- token budget, time limit, tools/network policy
- seed/temperature ถ้ามี
- raw verifier output และ infrastructure events

## Cost accounting

รวม token ทุก call ของ action agent, extraction, consolidation, retrieval/reranking, judges และ repair attempts แยกรายงาน cached tokens/credits หาก provider ให้ข้อมูล แต่ใช้ total billable/usage view อย่างสม่ำเสมอ

## Release hygiene

- license scan dependencies/data
- secret scan ก่อน push
- remove benchmark solutions และ copyrighted full text ที่แจกต่อไม่ได้
- publish catalog metadata/links แทนการ bundle PDF
- redact local absolute paths/usernames
- generate synthetic sample memory

## Model drift

CLI-hosted models อาจอัปเดต บันทึก run window สั้นและ randomized blocks ถ้ารันข้าม version ให้แยก cohort ห้ามรวมเงียบ ๆ

## Human review

PI ตรวจอย่างน้อย:

- random 20 episodes: factual/provenance accuracy
- random 20 skill activations: relevance/harm
- all protocol deviations
- all abstract numbers/citations
- qualitative examples เพื่อไม่เปิดเผยข้อมูล

