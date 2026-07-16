# Paper Roadmap

## เป้าหมายฉบับแรก

ทำ paper ที่ตอบคำถามแคบแต่แข็งแรง:

> Lite procedural memory ที่ bounded และมี provenance ช่วย CLI agents ข้าม session ได้จริงหรือไม่ และ Full modules เพิ่มประโยชน์คุ้มต้นทุนหรือไม่

อย่าพยายามพิสูจน์ multimodal, personalized memory, autonomous science และ human-brain fidelity ทั้งหมดใน paper เดียว

## Recommended paper sequence

### Paper A — Lite core + controlled benchmark

- no-memory vs Wiki vs raw trajectory vs Lite
- SkillEvolBench primary + Terminal-Bench pilot/secondary
- token efficiency, transfer, repeated error
- open schema/harness

นี่คือ minimum publishable paper และควรเสร็จก่อน Full

### Paper B — Full selective memory

- Lite vs Full modules/ablations
- proactive intervention, consolidation, hybrid retrieval
- MemoryArena/MemGym/LongCLI stress
- memory growth, negative transfer, cross-domain

### Future healthcare paper

ทำหลังระบบทั่วไปเสถียร ใช้ข้อมูล synthetic/public เท่านั้นก่อน เช่น guideline navigation หรือ medication-information workflow ต้องมี domain expert validation, safety policy และไม่ claim clinical efficacy จาก agent benchmark

## Manuscript structure

1. Abstract — problem, method, protocol, principal quantified result, limitation
2. Introduction — context≠experience, gap, contribution
3. Related Work — agent memory, procedural skill, context efficiency, benchmarks, research wiki/agents
4. Method — event/episode/skill/capsule, Lite/Full, lifecycle, safety
5. Experimental Setup — conditions, benchmarks, models, budget, metrics, statistics
6. Results — preregistered primary first; cost-quality frontier; transfer; ablations
7. Analysis — failure recurrence, harmful activation, memory growth, examples
8. Discussion — when Lite wins, when Full is worth it
9. Limitations/Ethics
10. Conclusion

## Figures

- Figure 1: event→episode→skill→capsule loop
- Figure 2: Lite/Full shared core and optional modules
- Figure 3: success vs total tokens Pareto frontier
- Figure 4: acquisition→deployment transfer by condition
- Figure 5: memory size / repeated error over sessions

## Tables

- Table 1: related-system capability matrix
- Table 2: benchmark/condition/budget
- Table 3: primary results with CI
- Table 4: module ablations + incremental tokens/latency
- Table 5: failure taxonomy/negative transfer

## Claim-evidence audit

ก่อน submission สร้างตาราง:

| Claim ID | Manuscript sentence | Evidence file/table | Analysis script | Protocol status | Human checked |
|---|---|---|---|---|---|

ทุกตัวเลขใน abstract ต้องผ่าน audit นี้

## Writing order

1. Methods + protocol ก่อนรัน final
2. Results จาก frozen analysis
3. Figures/tables
4. Discussion/limitations
5. Introduction/related work
6. Abstract สุดท้าย

## Venue strategy

อย่าเลือก venue จากความฝันก่อนเห็นผล หลัง Lite main study ให้ประเมิน contribution/scale/reproducibility แล้วเลือก workshop, short paper, findings หรือ full conference ตาม evidence จริง Preprint ทำได้เมื่อ artifact และ limitations พร้อม

## Final checklist

- protocol tag และ deviations appendix
- environment/container hashes
- raw results + analysis scripts
- seed/model/reasoning/token accounting
- license/data statements
- related work updated ก่อนส่ง
- citation/author/title checked จาก primary source
- no patient data, secrets หรือ benchmark solutions ใน release
- README reproduction ใช้ fresh clone ผ่าน

