# Bank Mahsulotlari Bozor Tahlili (MVP)

Raqobatchi banklarning kredit/mikroqarz mahsulotlarini avtomatik yig'ib (scraping),
saqlab va foydalanuvchi mezonlariga qarab AI-tushuntirish bilan eng mos mahsulotni
tavsiya qiluvchi tizim. To'liq dizayn hujjati:
[`docs/superpowers/specs/2026-07-07-bank-mahsulot-tahlili-design.md`](docs/superpowers/specs/2026-07-07-bank-mahsulot-tahlili-design.md).

MVP doirasi: 5 bank (SQB, NBU, Ipoteka Bank, HamkorBank, AgroBank), 4 kategoriya
(avtokredit, mikroqarz, kredit_karta, istemol_krediti), lokal muhitda ishga tushirish.

## Loyiha tuzilishi

```
db/            SQLAlchemy modellari va DB ulanishi (products, scrape_runs)
scrapers/      Har bir bank uchun alohida scraper + umumiy base.py interfeysi
               va orchestrator.py (barchasini ketma-ket ishga tushiradi)
recommender/   Qoida-asoslangan scoring (scoring.py) + OpenAI tushuntirish (explain.py)
api/           FastAPI backend (GET /products, POST /recommend)
dashboard/     Streamlit UI
scheduler.py   APScheduler orqali muntazam scraping
tests/         pytest testlari (db/, recommender/, scrapers/, api/, dashboard/)
data/          SQLite fayli (bank_products.db) — .gitignore'da, repo'ga kirmaydi
```

## O'rnatish

```bash
python -m venv .venv
```

Virtual muhitni faollashtirish:

```powershell
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

```cmd
:: Windows cmd
.venv\Scripts\activate.bat
```

```bash
# Unix/macOS
source .venv/bin/activate
```

Paketlarni o'rnatish:

```bash
# Windows (faollashtirilgan muhitda)
.venv\Scripts\pip install -r requirements.txt

# yoki faollashtirmasdan to'g'ridan-to'g'ri:
.venv\Scripts\python.exe -m pip install -r requirements.txt

# Unix/macOS
.venv/bin/pip install -r requirements.txt
```

`OPENAI_API_KEY` muhit o'zgaruvchisini o'rnating (tushuntirish generatsiyasi uchun;
kalit bo'lmasa yoki OpenAI xato qaytarsa, tizim to'xtamaydi — faqat raqamli
reyting ko'rsatiladi, `recommender/explain.py`dagi `try/except` orqali):

```cmd
:: Windows cmd
set OPENAI_API_KEY=sk-...
```

```powershell
# Windows PowerShell
$env:OPENAI_API_KEY = "sk-..."
```

```bash
# Unix/macOS
export OPENAI_API_KEY=sk-...
```

## Testlarni ishga tushirish

```bash
# Windows
.venv\Scripts\python.exe -m pytest --cov=. --cov-report=term-missing

# Unix/macOS (faollashtirilgan muhitda)
pytest --cov=. --cov-report=term-missing
```

Barcha testlar tarmoqqa yoki haqiqiy bank saytlariga bog'liq emas — scraperlar
`tests/scrapers/fixtures/`dagi saqlangan HTML namunalari asosida sinaladi, DB
testlari xotiradagi (`sqlite:///:memory:`) bazadan foydalanadi.

Coverage maqsadi (loyihaning asosiy mantig'i uchun): `db/`, `recommender/`,
`scrapers/orchestrator.py`, `api/` — 80%+. Scraper HTML-parsing modullari va
dashboard uchun to'liq branch coverage talab qilinmaydi (mos ravishda
fixture-asoslangan va smoke testlar bilan qoplangan).

## Ma'lumotlarni scraping qilish (bir martalik, qo'lda)

```bash
.venv\Scripts\python.exe -c "from db.database import get_engine, get_session_factory, init_db; from scrapers.orchestrator import run_all_scrapers; e = get_engine(); init_db(e); s = get_session_factory(e)(); run_all_scrapers(s)"
```

Yoki Python skriptida:

```python
from db.database import get_engine, get_session_factory, init_db
from scrapers.orchestrator import run_all_scrapers

engine = get_engine()
init_db(engine)
with get_session_factory(engine)() as session:
    run_all_scrapers(session)
```

Har bir bank alohida try/except bilan o'ralgan (`scrapers/orchestrator.py`) —
bitta bank sayti ishlamay qolsa, qolganlariga ta'sir qilmaydi; natija
`scrape_runs` jadvaliga (`success`/`failed` va xato matni bilan) yoziladi.
Ma'lumotlar `data/bank_products.db` (SQLite) fayliga tarix sifatida qo'shiladi
— eski yozuvlar o'chirilmaydi.

## API'ni ishga tushirish

```bash
.venv\Scripts\python.exe -m uvicorn api.main:app --reload
```

API ishga tushgach, `http://localhost:8000/docs` orqali Swagger UI'da
`GET /products` va `POST /recommend` endpointlarini sinab ko'rish mumkin.

## Dashboard'ni ishga tushirish

API alohida terminalda ishlab turgan holda:

```bash
.venv\Scripts\python.exe -m streamlit run dashboard/app.py
```

## Scheduler'ni ishga tushirish (muntazam scraping uchun)

```bash
.venv\Scripts\python.exe scheduler.py
```

Standart holatda har 24 soatda barcha 5 ta scraperni ketma-ket ishga tushiradi
(`scheduler.py`dagi `build_scheduler(..., interval_hours=24)`).

## Qo'lda end-to-end tekshiruv (operator uchun qo'llanma)

Quyidagi qadamlar avtomatlashtirilgan testlar qamrovidan tashqarida — chunki
ular haqiqiy bank saytlariga tarmoq orqali murojaat qilishni yoki uzoq muddat
ishlaydigan serverlarni talab qiladi. Operator quyidagilarni qo'lda bajarishi
kerak:

1. **Scraping**: Yuqoridagi "Ma'lumotlarni scraping qilish" buyrug'ini ishga
   tushiring. `data/bank_products.db` yaratilganini va unda `products` hamda
   `scrape_runs` jadvallarida yozuvlar paydo bo'lganini tekshiring (masalan,
   `sqlite3 data/bank_products.db "select bank, status from scrape_runs;"`
   orqali). Kutilayotgan natija: har bir bank uchun `status = success` (agar
   biror bank sayti tuzilishi o'zgargan bo'lsa, o'sha bank uchun `failed` va
   `error_message` to'ldirilgan bo'ladi — bu qolgan banklarga ta'sir
   qilmasligini tasdiqlang).
2. **API**: `uvicorn api.main:app --reload` buyrug'i bilan API'ni ishga
   tushiring, brauzerda `http://localhost:8000/docs` sahifasini oching.
   - `GET /products` endpointini `category` parametri bilan sinab, natijada
     scraping'dan olingan mahsulotlar qaytishini tekshiring.
   - `POST /recommend` endpointini haqiqiy mezonlar bilan (masalan
     `{"category": "mikroqarz", "amount_som": 50000000, "term_months": 12,
     "collateral_ok": false}`) chaqiring va javobda `recommendations`
     (top-3, ball bilan saralangan) va `explanation` (OpenAI matni yoki
     `OPENAI_API_KEY` bo'lmasa/OpenAI xato bersa — faqat reyting matni)
     qaytishini tekshiring.
3. **Dashboard**: API ishlab turganida, alohida terminalda
   `streamlit run dashboard/app.py` buyrug'ini ishga tushiring. Brauzerda
   ochilgan sahifada:
   - Kategoriya tanlang va mahsulotlar jadvali to'g'ri to'ldirilishini
     tekshiring (yoki ma'lumot yo'q bo'lsa — "Bu kategoriya uchun hozircha
     ma'lumot yo'q." xabari chiqishini tekshiring).
   - "Tavsiya olish" formasida summa, muddat va garov mezonlarini kiritib
     yuboring — natijada top-3 bank va tushuntirish matni ko'rsatilishini
     tasdiqlang.
4. Yuqoridagi qadamlarning barchasi haqiqiy internet ulanishi, ishlaydigan
   bank saytlari va (ixtiyoriy, tushuntirish matni uchun) haqiqiy
   `OPENAI_API_KEY`ni talab qiladi — shuning uchun avtomatlashtirilgan test
   suite'ga kiritilmagan va CI muhitida ishga tushirilmaydi.

## Xatolarni boshqarish (qisqacha)

- Scraper xatosi → shu bank uchun `scrape_runs.status = "failed"`, qolgan
  banklarga ta'sir qilmaydi (`scrapers/orchestrator.py`).
- OpenAI API xatosi yoki kalit yo'qligi → tushuntirish o'rniga faqat
  raqamli reyting matni qaytariladi, tizim to'xtamaydi
  (`recommender/explain.py`).
