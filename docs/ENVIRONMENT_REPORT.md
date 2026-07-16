# Environment Readiness Report — Experience Brain

**ตรวจเมื่อ:** 2026-07-16  
**ขอบเขต:** ตรวจแบบ read-only เท่านั้น — ไม่มีการติดตั้งโปรแกรม, ไม่มีการแก้ไข `BENCHMARK_PROTOCOL.md`, และไม่มีการรัน benchmark

## สรุปสำหรับ PI

เครื่องนี้ **พร้อมสำหรับเริ่มสร้าง Lite และทำงานที่ไม่ใช้ container** แต่ยัง **ไม่พร้อมสำหรับ Terminal-Bench 2.0** เพราะ Docker Engine ยังไม่ทำงาน

| หัวข้อ | สถานะ | ความหมายแบบง่าย |
|---|---|---|
| Windows | ผ่าน | Windows 11 64-bit ใช้งานได้ |
| Git | ผ่าน | ติดตั้งแล้ว (`2.54.0`) |
| Docker Desktop/CLI | ต้องดำเนินการ | มีคำสั่ง Docker แต่ service ที่รัน container ยังปิดอยู่ |
| Python | ผ่าน พร้อมข้อควรระวัง | `python` คือ 3.11.9 ตามขั้นต่ำ; แต่ `py` จะเลือก 3.14 เป็นค่าเริ่มต้น |
| Node.js / npm | ผ่าน | Node `22.22.2`, npm `10.9.7` สูงกว่าเกณฑ์ Node 20+ |
| Codex CLI | ผ่าน | `codex-cli 0.144.4` พบในเครื่อง |
| พื้นที่ดิสก์ | ผ่าน | ไดรฟ์ C: ว่าง `166.94 GB` มากกว่าเกณฑ์ `20–40 GB` |
| Git repository จริง | ยังไม่มี | ทั้งโฟลเดอร์นี้และ `starter-kit` ไม่มี `.git`; จึงยังบันทึก commit SHA หรือ freeze เวอร์ชันตาม protocol ไม่ได้ |
| Dependencies ของโค้ด | ยังตรวจไม่ได้ | starter kit ยังไม่มี source code, `pyproject.toml`, `requirements.txt`, `package.json`, lockfile หรือ Dockerfile |

## รายละเอียดที่ตรวจพบ

### ระบบปฏิบัติการและพื้นที่

- OS: Microsoft Windows 11 Home Single Language, build 22631, 64-bit
- ดิสก์ C:: ทั้งหมด 476.07 GB, ว่าง 166.94 GB
- WSL 2 มีองค์ประกอบของ Docker Desktop อยู่ แต่ยังไม่พบ Linux distribution สำหรับงานทั่วไปจากผลตรวจนี้

### เครื่องมือ

| เครื่องมือ | เวอร์ชัน/สถานะ | ข้อสังเกต |
|---|---|---|
| Git | `2.54.0.windows.1` | พร้อมใช้หลังสร้างหรือ clone repository |
| Docker CLI | `29.0.1` | CLI มีอยู่ แต่เชื่อมต่อ Docker Engine ไม่ได้ เพราะ Docker Desktop Linux engine ยังไม่รัน |
| Python (`python`) | `3.11.9` | เป็นตัวที่ควรใช้สร้าง virtual environment ของโครงการในระยะแรก |
| Python launcher (`py`) | ค่าเริ่มต้น `3.14.0`; มี `3.11` ด้วย | อย่าใช้ `py` โดยไม่ระบุเวอร์ชัน เพราะอาจได้ 3.14 ซึ่งบางแพ็กเกจวิจัยยังไม่รองรับ |
| Node.js | `22.22.2` | ผ่านเกณฑ์ 20+ |
| npm | `10.9.7` | พร้อมใช้เมื่อ repo มี `package.json` |
| Codex CLI | `0.144.4` | พบคำสั่งและเวอร์ชัน; สถานะการลงชื่อเข้าใช้ไม่ได้ตรวจในรายงานนี้ |

## Dependency ที่ยังขาดหรือยังยืนยันไม่ได้

1. **Docker Engine ที่กำลังทำงาน** — ต้องเปิด Docker Desktop และรอจนสถานะเป็น Running ก่อนใช้ benchmark แบบ container
2. **Git repository ที่ clone แล้ว** — ต้องสร้าง GitHub repository หรือ clone repository เป้าหมายก่อน เพื่อให้ทุก run บันทึก commit SHA ตาม benchmark protocol ได้
3. **โค้ดและไฟล์ dependency ของโครงการ** — starter kit เป็นเอกสารวางแผน จึงยังไม่กำหนด Python/Node packages, เวอร์ชันที่ล็อก, หรือ container image
4. **สิทธิ์เข้าถึงบริการที่ใช้จริง** — ยังต้องยืนยันภายหลังว่า Codex/API และ GitHub account เข้าถึงได้ โดยไม่ใส่ secret ลงใน repository

> ผลข้อนี้ไม่ใช่ความผิดพลาดของเครื่อง: เป็นเพราะโครงการยังอยู่ก่อนขั้น scaffold ตาม `START_HERE.md` จึงยังไม่มี dependency ที่ระบุให้ติดตั้งอย่างเป็นทางการ

## คำสั่งที่เสนอสำหรับภายหลัง (ยังไม่ได้รัน)

คำสั่งเหล่านี้เป็นเพียงรายการเตรียมการ ให้รันหลัง PI อนุมัติและเมื่อมี repo/ไฟล์ dependency จริงแล้วเท่านั้น

### Windows 11 (เครื่องปัจจุบัน)

1. เปิด **Docker Desktop** จาก Start Menu แล้วรอให้ขึ้น “Engine running”; ตรวจด้วย:

   ```powershell
   docker info
   ```

2. หากยังไม่มี repository จริง ให้ clone หลังสร้าง repo บน GitHub:

   ```powershell
   git clone <REPOSITORY_URL> experience-brain
   cd experience-brain
   ```

3. เมื่อมี dependency manifest แล้ว ให้ใช้ Python 3.11 อย่างชัดเจน (ตัวอย่างสำหรับ `requirements.txt`):

   ```powershell
   py -3.11 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   ```

4. หาก repo มี `package-lock.json` ให้ใช้:

   ```powershell
   npm ci
   ```

### macOS

```bash
# ติดตั้ง Homebrew ก่อนหากเครื่องยังไม่มี: https://brew.sh
brew install git python@3.11 node
# ติดตั้ง Docker Desktop จาก https://www.docker.com/products/docker-desktop/
git clone <REPOSITORY_URL> experience-brain
cd experience-brain
python3.11 -m venv .venv
source .venv/bin/activate
# รันเมื่อ repo มี requirements.txt
python -m pip install -r requirements.txt
# รันเมื่อ repo มี package-lock.json
npm ci
```

### Ubuntu/Debian Linux

```bash
sudo apt update
sudo apt install -y git python3.11 python3.11-venv python3-pip nodejs npm
# ติดตั้ง Docker Engine ตามคู่มือทางการ: https://docs.docker.com/engine/install/ubuntu/
git clone <REPOSITORY_URL> experience-brain
cd experience-brain
python3.11 -m venv .venv
source .venv/bin/activate
# รันเมื่อ repo มี requirements.txt
python -m pip install -r requirements.txt
# รันเมื่อ repo มี package-lock.json
npm ci
```

## ความเสี่ยงด้านดิสก์ เวลา และค่าใช้จ่าย

| ประเภท | ระดับ | เหตุผลและวิธีควบคุม |
|---|---|---|
| ดิสก์ | ปานกลาง | เอกสารกำหนด 20–40 GB สำหรับ Terminal-Bench; ตอนนี้มี 166.94 GB จึงพอ แต่ Docker images, build cache และผลลัพธ์ซ้ำอาจกินพื้นที่เพิ่มมากกว่าที่คาดได้. ตรวจพื้นที่ก่อนดึง image และตั้งจุดตรวจเป็นระยะ |
| เวลา setup | ต่ำ–ปานกลาง | เปิด Docker และ clone repo ใช้เวลาไม่นาน แต่การดึง container image ครั้งแรกขึ้นกับอินเทอร์เน็ตและขนาด image |
| เวลา benchmark | สูง | Protocol ต้องเปรียบเทียบ C0–C3 ภายใต้เงื่อนไขเท่ากัน และอย่างน้อย 3 runs ต่อ condition; งาน full study จึงมากกว่ารัน task ชุดเดียว 12 เท่า ก่อนรวม pilot และ ablation |
| ค่า API/Codex | สูงหากไม่กำหนดเพดาน | Protocol นับทั้ง token ที่ใช้ทำงานและ token เบื้องหลังของ memory/consolidation. เอกสารยังไม่ระบุ model, token cap หรือราคา จึงคำนวณจำนวนเงินที่น่าเชื่อถือไม่ได้; ต้องกำหนด daily cap และ stop rule ก่อน pilot |
| ความน่าเชื่อถือของผล | สูงหากไม่ freeze เวอร์ชัน | Protocol กำหนดให้ freeze Codex, harness, dependency lock และ container digest. ขณะนี้ยังไม่มี repo/lockfile จึงยังทำขั้นนี้ไม่ได้ |
| Python version | ปานกลาง | การใช้ `py` เฉย ๆ จะได้ Python 3.14 แทน 3.11. ให้ pin เป็น 3.11 จนกว่าจะยืนยันว่า dependencies รองรับ 3.14 |

## ลำดับที่แนะนำก่อนเริ่ม benchmark

1. สร้างหรือ clone Git repository เป้าหมาย และเก็บ starter kit นี้ไว้ใน repository นั้น
2. เปิด Docker Desktop แล้วตรวจว่า `docker info` สำเร็จ
3. ให้ Codex scaffold Lite เพื่อสร้าง dependency manifest และ lockfile
4. ตรวจ dependency, pin Python 3.11, และรัน unit tests/BrainBench-Mini ก่อน
5. ก่อน pilot ให้ freeze เวอร์ชันและ budget ตาม `BENCHMARK_PROTOCOL.md` โดยไม่เปลี่ยน protocol

## ข้อสรุป

ฮาร์ดแวร์และเครื่องมือหลักของเครื่องนี้เพียงพอสำหรับเริ่มโครงการแล้ว. สิ่งที่ขาดเป็นเรื่องการเปิด Docker Engine และการเปลี่ยนจาก starter kit ไปเป็น Git repository ที่มี code/lockfiles; หลังสองข้อนี้พร้อม จึงควรตรวจ dependency รอบที่สองก่อนเริ่ม pilot benchmark.
