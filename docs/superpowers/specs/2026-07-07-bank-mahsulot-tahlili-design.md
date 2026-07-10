

# Bank mahsulotlari bozor tahlili va AI tavsiya tizimi — Dizayn hujjati

**Sana:** 2026-07-07
**Holat:** Tasdiqlangan (MVP ko'lami)

## 1. Maqsad va kontekst

Hozirda raqobatchi banklar tariflari oyiga bir marta qo'lda tayyorlanadigan PowerPoint hisobotlar orqali kuzatib boriladi (`Raqobatchi_banklar_tahlili_ChB_31_03_2026 y].pptx` va `Рақобатчи_банклар_таҳлили_ММБ_кредит_MART_2026_yil.pptx`). Bu jarayonni avtomatlashtirish va ustiga AI-asoslangan tavsiya qatlamini qo'shish kerak: foydalanuvchi bergan mezonlar (masalan, mikroqarz, muayyan summa, garovsiz) asosida qaysi bank mahsuloti mos kelishini va nima uchun mosligini ko'rsatadigan tizim.

Loyiha 4 mustaqil kichik tizimdan iborat: ma'lumot yig'ish, saqlash/kategoriyalash, AI tavsiya, taqdim etish (dashboard). Ushbu hujjat MVP — birinchi bosqich — ko'lamini belgilaydi.

## 2. MVP ko'lami

- **Foydalanuvchi:** Ichki foydalanish (bank/tashkilot ichidagi marketing yoki strategiya bo'limi). Tashqi/ommaviy foydalanuvchilar MVP doirasiga kirmaydi.
- **Segment:** Faqat jismoniy shaxslar mahsulotlari — Avtokredit (1lamchi va 2lamchi bozor), Mikroqarz, Kredit karta, Iste'mol krediti (4 kategoriya).
- **Banklar (pilot):** SQB, NBU, Ipoteka Bank, HamkorBank, AgroBank (5 ta). Qolgan banklar keyingi bosqichda qo'shiladi.
- **Ma'lumot manbai:** Har bir bankning rasmiy sayti — avtomatik scraping (MVP'dan boshlab, qo'lda kiritish yo'q).
- **Muhit:** Avval lokal kompyuterda ishga tushiriladi va sinaladi. Cloud/serverga joylashtirish keyingi bosqich.
- **AI:** OpenAI API (mavjud kalit) — tavsiya matnini generatsiya qilish uchun. Scoring (ballash) qoida-asoslangan, LLM faqat tabiiy tildagi tushuntirish yozadi.

**MVP doirasidan tashqarida (keyingi bosqichlar):** yuridik shaxslar mahsulotlari, qolgan ~10 bank, tashqi/ommaviy versiya, cloud deployment, real-time scraping monitoring dashboard.

## 3. Arxitektura




Bitta Python loyihasi (monolit):

```
bank-analiz/
├── scrapers/          # Har bir bank uchun alohida modul
│   ├── sqb.py, nbu.py, ipoteka.py, hamkor.py, agro.py
│   └── base.py        # Umumiy interfeys (yangi bank qo'shish oson bo'lishi uchun)
├── db/
│   ├── models.py       # SQLAlchemy modellari
│   └── database.py
├── recommender/
│   └── scoring.py       # Qoida-asoslangan scoring + OpenAI orqali tushuntirish
├── api/
│   └── main.py          # FastAPI endpointlari
├── dashboard/
│   └── app.py           # Streamlit UI
├── scheduler.py          # Muntazam scraping (APScheduler)
└── data/bank_products.db # SQLite
```

**Texnologiyalar:** Python, Playwright (yoki requests+BeautifulSoup, sayt turiga qarab), SQLite + SQLAlchemy, FastAPI, Streamlit, APScheduler, OpenAI SDK.

## 4. Komponentlar

1. **Scraper modullari** — har biri mustaqil, bitta bank saytini o'qib standart `Product` obyektiga aylantiradi: bank, kategoriya, mahsulot nomi, yillik foiz stavkasi, muddat, garov talabi, boshlang'ich badal, kredit miqdori (min/max), manba URL, olingan sana. `base.py`dagi umumiy interfeysga amal qiladi (`scrape() -> list[Product]`), shu orqali yangi bank qo'shish boshqa qismlarga ta'sir qilmaydi.
2. **Ma'lumotlar bazasi** — `products` jadvali (yuqoridagi maydonlar + `scraped_at` vaqt belgisi, tarixni saqlash uchun yangi yozuv sifatida qo'shiladi, eskisi o'chirilmaydi) va `scrape_runs` jadvali (har bir scraping seansi holati: muvaffaqiyatli/xato, xato matni, vaqt).
3. **Recommender** — foydalanuvchi mezonlari (kategoriya, summa, muddat, garov kerak/emas) asosida mos mahsulotlarni vaznli formula bilan ballaydi (masalan: stavka 40%, garov talabi 25%, muddat moslashuvchanligi 20%, komissiya/qo'shimcha shartlar 15%), eng yaxshi 3 tasini OpenAI orqali tabiiy tildagi tushuntirish bilan qaytaradi.
4. **API** — FastAPI: `GET /products` (filtrlash bilan), `POST /recommend` (mezonlarni qabul qilib top-3 tavsiyani qaytaradi).
5. **Dashboard** — Streamlit: kategoriya bo'yicha taqqoslash jadvali, filtrlar (bank, stavka oralig'i, muddat), "Tavsiya olish" formasi va natija ko'rinishi.

## 5. Ma'lumotlar oqimi

1. Scheduler belgilangan intervalda (masalan har 24 soatda) barcha 5 ta scraperni ketma-ket ishga tushiradi.
2. Har bir scraper mahsulot ro'yxatini qaytaradi → DB'ga yangi qator sifatida yoziladi (tarix saqlanadi — vaqt o'tishi bilan stavka o'zgarishini kuzatish imkonini beradi).
3. Foydalanuvchi Streamlit'da kategoriya + mezon kiritadi → `/recommend` chaqiriladi → DB'dan har bir bankning **eng so'nggi** mos mahsulotlari olinadi → scoring hisoblanadi → top-3 OpenAI'ga yuborilib tushuntirish matni olinadi → natija ko'rsatiladi.

## 6. Xatolarni boshqarish

- Har bir scraper alohida try/except bilan o'ralgan — bitta bank sayti ishlamay qolsa (masalan sayt tuzilishi o'zgargan), qolgan banklarga ta'sir qilmaydi; xato `scrape_runs` jadvaliga log qilinadi.
- Scrape natijasi kutilgan formatga mos kelmasa (bo'sh yoki noto'g'ri struktura) — yangi ma'lumot yozilmaydi, oldingi muvaffaqiyatli ma'lumot dashboard'da "oxirgi yangilangan: [sana]" belgisi bilan ko'rsatilaveradi.
- OpenAI API xatosi yoki kvota tugashi — tizim to'xtamaydi, tushuntirish matni o'rniga faqat raqamli reyting (scoring) ko'rsatiladi.

## 7. Testlash

- Har bir scraper uchun saqlangan (mock) HTML fayl asosida unit test — real saytga bog'liq bo'lmasdan ishlaydi.
- Scoring formulasi uchun unit testlar (aniq kirish → kutilgan reyting tartibi).
- DB modellari uchun asosiy CRUD testlari.
- Coverage maqsadi: asosiy logika (scoring, DB) uchun 80%+; scraperlar uchun mock-based testlar yetarli, real sayt bilan integratsion test ixtiyoriy (chunki sayt tuzilishi tez-tez o'zgarishi mumkin).

## 8. Keyingi bosqichlar (MVP dan keyin)

- Qolgan banklarni scraping qamroviga qo'shish
- Yuridik shaxslar segmentini qo'shish (2-fayl asosida)
- Cloud/serverga joylashtirish va scheduler'ni doimiy ishlaydigan qilish
- Tashqi/ommaviy versiya uchun autentifikatsiya, huquqiy ogohlantirishlar va yuklama (load) rejasi