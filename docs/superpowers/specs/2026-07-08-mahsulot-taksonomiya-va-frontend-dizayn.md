# Mahsulot taksonomiyasini kengaytirish va yangi frontend — Dizayn hujjati

**Sana:** 2026-07-08
**Holat:** Muhokama qilindi, tasdiqlandi
**Bog'liq hujjat:** [`2026-07-07-bank-mahsulot-tahlili-design.md`](2026-07-07-bank-mahsulot-tahlili-design.md) — bu hujjat o'sha MVP'ning "Keyingi bosqichlar" qismini davom ettiradi (kategoriya kengaytirish, ilgari rejalashtirilgan).

## 1. Maqsad va kontekst

MVP dashboard (Streamlit) ishga tushirilgach, ikkita muammo aniqlandi:

1. **Toraygan taksonomiya.** Hozirgi tizim faqat 4 kategoriyani biladi (avtokredit, mikroqarz, kredit_karta, istemol_krediti), holbuki `bozor tahlil.xlsx`da tashkilot belgilagan to'liq jismoniy shaxs mahsulot ro'yxati (16 kategoriya) va `Raqobatchi_banklar_tahlili_ChB_31_03_2026 y].pptx` (qo'lda tayyorlangan taqqoslash hisoboti, 31.03.2026) bor — bular hozirgi tizimga kiritilmagan.
2. **Streamlit'ning dizayn chegarasi.** Streamlit standart widget/toolbar/branding'i ustidan chinakam korporativ dizayn qurish imkonsiz — CSS bilan yashirish mumkin, lekin tub xatti-harakat o'zgarmaydi. Buyurtmachi (bank ichidagi foydalanuvchi) uchun professional ko'rinish talab qilinadi.

`Raqobatchi_banklar_tahlili_ChB_31_03_2026 y].pptx`ni tahlil qilish shuni ko'rsatdiki, PowerPoint hisobotidagi 16 kategoriyaning barchasi **bir xil jadval tuzilishida emas**:

- **11 tasi — "kredit mahsuloti" tipi** (avtokredit x5, mikroqarz x2, kredit karta, iste'mol krediti, ipoteka x2): ustunlar bank, mahsulot nomi, yillik foiz stavkasi, muddat, imtiyozli davr, kredit miqdori, to'lov usuli (annuitet/differensial), kredit kafolati, boshlang'ich badal, maxsus shartlar.
- **5 tasi butunlay boshqa tuzilishda:** omonat UZS/USD (omonat nomi, muddat, yillik %, minimal miqdor, qo'shimcha kiritish, qisman chiqim, muddatidan oldin yechish shartlari), plastik karta x2 (karta turi × operatsiya turi narx matritsasi), xalqaro pul o'tkazmalari (bank komissiyalari ro'yxati).

Bu hujjat faqat **11 ta "kredit mahsuloti" tipidagi kategoriya**ni qamrab oladi. Qolgan 5 tasi (omonat, plastik karta, xalqaro o'tkazma) tuzilishi butunlay boshqacha bo'lgani uchun keyingi alohida dizayn hujjatiga qoldiriladi (bitta jadvalga zo'rlab sig'dirish noto'g'ri bo'lardi).

## 2. Ko'lam

**Ushbu bosqichga kiradi:**
- 11 ta kredit-tipidagi kategoriya uchun markazlashtirilgan taksonomiya registri
- `ProductRow` modeliga yangi maydonlar (imtiyozli davr, to'lov usuli, maxsus shartlar)
- Yangi React/Vite/TypeScript frontend, Streamlit dashboard'ni to'liq almashtiradi
- Vizual dizayn: to'q ko'k (`#0e2c56`) asos, qizil (`#d9455f`) faqat faol holat chizig'i va CTA uchun minimal urg'u, Fraunces (sarlavha) + Inter (matn/raqam) tipografiya juftligi — brauzerda mokap orqali tasdiqlangan
- Mavjud 4 kategoriya (avtokredit, mikroqarz, kredit_karta, istemol_krediti) key'lari o'zgarmaydi, yangi 7 kategoriya bo'sh holatda ("hozircha ma'lumot yo'q") sidebar'da ko'rinadi

**Ushbu bosqichga kirmaydi:**
- Omonat, plastik karta, xalqaro o'tkazma kategoriyalari (boshqa ma'lumot tuzilishi — alohida dizayn kerak)
- Yangi 7 kategoriya uchun real scraper yozish (har biri uchun bank sayti tadqiqoti kerak — bosqichma-bosqich, kategoriya-kategoriya qo'shiladi)
- 5 tadan ortiq bank qo'shish (PowerPoint hisobotida 15+ bank bor, lekin bu alohida qaror — hozirgi MVP ko'lami 5 bank bilan cheklangan)
- "Tavsiya olish" (AI-tahlil) qismini qayta dizayn qilish — bu keyingi bosqich, hozircha mavjud shaklda ikkinchi darajali blok sifatida saqlanadi

## 3. Kategoriya taksonomiyasi

`categories.py` — yangi markazlashtirilgan registr, backend va frontend shu bitta manbadan o'qiydi:

| Kalit | Nomi | Holat |
|---|---|---|
| `avtokredit` | Avtokredit (birlamchi bozor) | ✅ mavjud (5 bank) |
| `avtokredit_ikkilamchi` | Avtokredit (ikkilamchi bozor) | 🔜 bo'sh |
| `avtokredit_brend_birlamchi` | Brendli avtokredit — birlamchi (GM/BYD/KIA/Hyundai/Renault/LADA/VW/Skoda/Chery) | 🔜 bo'sh |
| `avtokredit_brend_ikkilamchi` | Brendli avtokredit — ikkilamchi | 🔜 bo'sh |
| `avtokredit_elektro` | Elektromobil avtokrediti | 🔜 bo'sh |
| `mikroqarz` | Mikroqarz (oflayn) | ✅ mavjud (5 bank) |
| `mikroqarz_onlayn` | Mikroqarz (onlayn) | 🔜 bo'sh |
| `kredit_karta` | Kredit kartalari | ✅ mavjud (5 bank) |
| `istemol_krediti` | Iste'mol krediti | ✅ mavjud (5 bank) |
| `ipoteka_tijorat` | Ipoteka krediti (tijorat) | 🔜 bo'sh |
| `ipoteka_davlat` | Ipoteka krediti (Iqtisodiyot va moliya vazirligi mablag'lari hisobidan) | 🔜 bo'sh |

Har bir registr yozuvi: `key`, `label_uz`, `schema="credit"`. Yangi kategoriya qo'shish = registrga bitta yozuv qo'shish + tegishli bank scraperlariga `CATEGORY_URLS`/`CATEGORY_HEADINGS` yozish (mavjud `TextSectionScraper` arxitekturasi buni allaqachon qo'llab-quvvatlaydi, `scrapers/base.py`ga qarang).

## 4. Ma'lumotlar modeli o'zgarishi

`db/models.py`dagi `ProductRow`ga PowerPoint jadvaliga mos yangi ixtiyoriy maydonlar qo'shiladi (mavjud maydonlar o'zgarmaydi — orqaga qarab mos, eski qatorlar yangi ustunlarda `NULL` bilan qoladi):

```python
grace_period_months: Mapped[int | None] = mapped_column(Integer, nullable=True)   # Imtiyozli davri
payment_method: Mapped[str | None] = mapped_column(String(50), nullable=True)      # "annuitet" | "differensial" | "annuitet_yoki_differensial"
special_terms: Mapped[str | None] = mapped_column(Text, nullable=True)             # Maxsus shartlari (erkin matn)
```

`scrapers/base.py`dagi `Product` dataclass va `_build_product` shu uch maydonni ham to'ldiradigan (hozircha `None` qaytaradigan, keyinchalik parsing kengaytiriladigan) qilib yangilanadi. Mavjud scraperlar (`sqb.py`, `nbu.py`, `ipoteka.py`, `hamkor.py`, `agro.py`) va ularning testlari buzilmaydi, chunki maydonlar ixtiyoriy.

API tarafida `api/main.py`dagi `_row_to_dict` yangi uch maydonni ham javobga qo'shadi. `CATEGORY_URLS`/`CATEGORY_HEADINGS` orqali ishlaydigan scraper arxitekturasi o'zgarmaydi.

## 5. Frontend arxitekturasi

**Texnologiya:** React 18 + Vite + TypeScript. `frontend/` papkasi repo tub qismida, mavjud `api/` va `dashboard/` bilan bir qatorda.

```
frontend/
├── src/
│   ├── components/
│   │   ├── Sidebar.tsx          # 11 kategoriya, faol holat belgilash
│   │   ├── ProductTable.tsx     # Bank bo'yicha taqqoslash jadvali
│   │   └── RecommendPanel.tsx   # Mavjud "Tavsiya olish" — ikkinchi darajali
│   ├── lib/
│   │   ├── api.ts               # fetch wrapper (/products, /recommend)
│   │   └── categories.ts        # Backend categories.py bilan mos ro'yxat
│   ├── styles/
│   │   └── tokens.css           # Rang/tipografiya token'lari (3-bo'limdagi mokapga mos)
│   └── App.tsx
├── index.html
├── vite.config.ts
└── package.json
```

**Backend integratsiyasi:** `api/main.py`ga `fastapi.middleware.cors.CORSMiddleware` qo'shiladi, `http://localhost:5173` (Vite dev server) uchun ruxsat. Ishlab chiqarishga joylashtirishda ruxsat etilgan origin muhit o'zgaruvchisidan olinadi.

**Streamlit dashboard olib tashlanadi:** `dashboard/app.py` va `tests/dashboard/` — React frontend to'liq almashtirgach o'chiriladi (ikkita parallel UI'ni saqlashning ma'nosi yo'q, `README.md`dagi "Dashboard'ni ishga tushirish" bo'limi yangilanadi).

## 6. Vizual dizayn

Brauzer-asosli mokap orqali tasdiqlangan (uch bosqichli iteratsiya):

- **Asosiy rang:** to'q ko'k `#0e2c56` (sidebar foni)
- **Urg'u rangi:** qizil `#d9455f` — **faqat** faol sidebar bandining chap chizig'i va "Tavsiya olish" CTA tugmasi uchun; fon sifatida ishlatilmaydi
- **Tipografiya:** sarlavhalar — Fraunces (serif, 500/600 og'irlik), matn/jadval — Inter (400–700), raqamlar `font-variant-numeric: tabular-nums` bilan tekislanadi
- **Jadval:** minimalist, chiziqlar `#eceef3`, foiz stavkasi eng arzon qiymatda yashil (`#1a7f4a`) urg'u bilan ajratiladi

To'liq mokap: brainstorming seansi davomida yaratilgan (`.superpowers/brainstorm/` — vaqtinchalik, `.gitignore`ga qo'shildi).

## 7. Xatolarni boshqarish

Mavjud xatti-harakat saqlanadi: scraper xatosi bitta bankka ta'sir qiladi (`scrapers/orchestrator.py`), OpenAI xatosi tizimni to'xtatmaydi. Frontend tarafida: `/products` so'rovi muvaffaqiyatsiz bo'lsa yoki bo'sh natija qaytarsa, foydalanuvchiga "Bu kategoriya uchun hozircha ma'lumot yo'q" xabari ko'rsatiladi (Streamlit versiyasidagi kabi xatti-harakat, yangi dizaynda takrorlanadi).

## 8. Testlash

- **Backend:** mavjud pytest suite + yangi uch maydon uchun DB va API testlari; 80%+ qamrov saqlanadi (`db/`, `recommender/`, `scrapers/orchestrator.py`, `api/`).
- **Frontend:** Vitest + React Testing Library — `lib/api.ts` va `lib/categories.ts` uchun unit testlar; bitta Playwright smoke-test (sidebar bandini bosish → jadval mos kategoriya ma'lumotiga yangilanishini tekshiradi).

## 9. Keyingi bosqichlar (ushbu dizayndan keyin)

- Qolgan 7 ta kredit kategoriyasi uchun bank-bank, kategoriya-kategoriya scraper qo'shish
- Omonat (UZS/USD) — alohida ma'lumot modeli va jadval dizayni
- Plastik karta narxlar matritsasi — alohida ma'lumot modeli
- Xalqaro pul o'tkazmalari komissiyalari — alohida ma'lumot modeli
- 5 tadan ortiq bankka kengaytirish (agar kerak bo'lsa)
- "Tavsiya olish" (AI-tahlil, 2-bosqich) qismini qayta dizayn qilish