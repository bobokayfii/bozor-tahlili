# Yangi bank scraperlari — 1-bosqich (pilot) — Dizayn hujjati

**Sana:** 2026-08-06
**Holat:** Muhokama qilindi, tasdiqlandi

## 1. Maqsad va kontekst

Platformada hozircha 15 ta bank uchun scraper bor (`scrapers/registry.py`dagi `ALL_SCRAPERS`). Foydalanuvchi bergan to'liq O'zbekiston banklari ro'yxati (33 ta) bilan solishtirilganda, quyidagi 18 ta bank uchun hali scraper yo'q:

BDB, Trastbank, Davr Bank, OFB (Orient Finans Bank), Anorbank, Uzum Bank, AVO Bank, Asia Alliance Bank, Garant bank, Poytaxt Bank, Universalbank, Octobank, Apex Bank, Hayot Bank, Madad Invest Bank, KDB Bank Uzbekistan, Ziraat Bank Uzbekistan, Saderat Bank.

18 tasini bir yo'la qamrab olish bitta implementatsiya bosqichi uchun katta — har bir scraper haqiqiy sayt tuzilishini alohida tadqiq qilishni talab qiladi (mavjud scraperlar 100-500 qatorgacha, bankka xos parsing mantiqi bilan). Shu sabab ish **pilot bosqichga** bo'lindi: yondashuvni 3 ta bankda tasdiqlash, keyin qolganlariga o'tish.

## 2. Qamrov

**Kiradi (bu hujjat):**
- 3 ta pilot bank uchun scraper: **Anorbank**, **Octobank**, **Asia Alliance Bank** (aab.uz)
- Har biri uchun fixture-asoslangan testlar
- `registry.py`ga ro'yxatdan o'tkazish

**Kirmaydi:**
- Qolgan 15 ta bank (BDB, Trastbank, Davr Bank, OFB, AVO Bank, Garant bank, Poytaxt Bank, Universalbank, Apex Bank, Hayot Bank, Madad Invest Bank, KDB, Ziraat, Saderat) — keyingi bosqich(lar)ga qoldiriladi, bu hujjat ularni qamramaydi
- **Uzum Bank** — butun sayti client-side render qilinadigan SPA (Nuxt.js), oddiy `requests.get()` bilan bo'sh sahifa qaytadi (tekshirildi: bosh sahifa va `/uz/loans/` ikkalasi ham ~6.5 KB JS-yuklash qobig'i, real kontent yo'q). Bu muammo mavjud kodda ikki marta hujjatlashtirilgan (`scrapers/agro.py`, `scrapers/asaka.py` — ikkalasida ham "productionda hech qanday mahsulot topmasligi ehtimoli yuqori" deb ochiq yozilgan). Uzum Bank uchun scraper yozish — Playwright'ni production arxitekturasiga qo'shish (alohida qaror, xarajatlari: ~300-400MB brauzer binary, sekinroq scrape, ko'proq fragile) yoki xuddi shu ma'lum cheklov bilan uchinchi marta takrorlash degani — ikkalasi ham bu pilot doirasida hal qilinmaydi
- Yangi banklar uchun SVG logotiplar — frontend (`getBankLogo()`) logotip topilmasa shunchaki hech narsa ko'rsatmaydi (xato bermaydi), shuning uchun bloklovchi emas; alohida, ixtiyoriy keyingi ish
- Frontend kod o'zgarishlari — kerak emas (pastga qarang, 5-bo'lim)

## 3. Sayt tekshiruvi (bajarildi)

Barcha uchala pilot bank server-rendered (JS bajarilishisiz to'liq HTML qaytaradi):

| Bank | Tekshirilgan URL | Natija |
|---|---|---|
| Anorbank | `anorbank.uz/credits/` | 718 KB HTML, to'liq mahsulot ro'yxati matni bor |
| Octobank | `octobank.uz/jismoniy-shaxslarga/kredity-i-mikrozaymy` | 128 KB HTML, to'liq mahsulot ro'yxati matni bor |
| Asia Alliance Bank | `aab.uz/uz/` | 451 KB HTML, `/uz/private/crediting/` ostida ko'plab mahsulot sahifalari (overdraft, mikrozaym, avtokredit, ipoteka variantlari) |

Har uchala bankda ham har bir mahsulot turi (avtokredit, mikrozaym, ipoteka va h.k.) odatda **alohida sahifada** joylashgan — bosh "kredit" sahifasi faqat kartochkalar ro'yxati, batafsil stavka/muddat/summa jadvali har bir mahsulotning o'z sahifasida. Bu aynan Aloqabank/Asia Alliance kabi banklar uchun mavjud `CATEGORY_URLS` naqshiga mos keladi (bitta umumiy sahifa emas, kategoriya→URL xaritasi).

## 4. Arxitektura — yangi narsa yo'q

Mavjud `scrapers/base.py`dagi `TextSectionScraper` bazaviy klassi qayta ishlatiladi, hech qanday yangi abstraksiya kiritilmaydi. Har bir yangi bank uchun:

- `scrapers/{bank}.py` — `TextSectionScraper`dan meros oladigan yangi klass:
  - `bank_name`, `url` — asosiy maydonlar
  - `CATEGORY_URLS: dict[str, str]` — kategoriya kaliti (`categories.py`dagi `category_keys()`dan) → o'sha bankning mahsulot sahifasi to'liq URL manzili
  - `CATEGORY_HEADINGS` — sahifa matnidagi bo'lim sarlavhalari juftligi (boshlanish/tugash), umumiy `_build_product()` bilan ishlaydigan hollar uchun
  - Umumiy sarlavha-juftlik naqshi mos kelmagan mahsulotlar uchun (masalan, bosqichli stavka jadvali, foiz kontaminatsiyasi xavfi) — `run()` qayta yoziladi va maxsus `_build_{category}_product()` metodlari qo'shiladi, aynan `scrapers/aloqa.py`dagi naqsh bo'yicha
  - `PRODUCT_NAMES` — mahsulotning saytdagi haqiqiy nomi (berilmasa, umumiy "{bank_name} {kategoriya}" ishlatiladi)
- `scrapers/registry.py` — yangi klass import qilinadi va `ALL_SCRAPERS` ro'yxatiga qo'shiladi

**Kategoriya qamrovi cheklovi:** Har bir bank uchun 11 ta kategoriyaning (categories.py) barchasi topilishi shart emas va kutilmaydi — faqat bank saytida aniq stavka + muddat + summa ko'rsatilgan mahsulotlar qo'shiladi. Aniq son topilmasa (masalan, "cheklanmagan" yoki faqat nisbat ko'rsatilgan holatlar), `_build_product()` `None` qaytaradi va o'sha kategoriya o'tkazib yuboriladi — bu xato emas, mavjud scraperlarning barchasida shu xulq-atvor (masalan Aloqabank avtokredit).

Har bir bank uchun aniq qaysi kategoriyalar mavjudligi, qaysi sarlavhalar/regexlar ishlatilishi — implementatsiya bosqichida, real sahifa matnini o'qib chiqib aniqlanadi (oldindan spec'da qattiq belgilanmaydi, chunki bu implementatsiyaning o'zi — mavjud scraperlarning barchasida shu tarzda ishlangan, izohlarda "sahifada X shunday yozilgan, shu sabab Y regex ishlatiladi" tarzida hujjatlashtirilgan).

## 5. Frontend — o'zgarish kerak emas

Tekshirildi: `frontend/src/lib/bankLogos.ts`dagi `getBankLogo()` bank nomiga mos logotip topmasa `undefined` qaytaradi, `ProductTable.tsx`da bu `{getBankLogo(...) && <img .../>}` bilan ishlatiladi — logotip yo'qligi UI'ni buzmaydi, shunchaki logotip ko'rsatilmaydi. Bank nomi va mahsulotlar ma'lumotlar bazasidan (`ProductRow`) dinamik o'qiladi, kod ichida qattiq yozilgan bank ro'yxati yo'q. Demak yangi banklar scraperi ishga tushishi bilanoq (orchestrator ma'lumotlar bazasiga yozgach) ular platformada avtomatik ko'rinadi, frontend'ga qo'l tegmaydi.

## 6. Testlar

Har bir yangi bank uchun `tests/scrapers/test_{bank}.py`, mavjud `test_aloqa.py` naqshi bo'yicha:
- Real sahifalardan olingan HTML `tests/scrapers/fixtures/{bank}_{category}.html` sifatida saqlanadi
- `fetch_html` `unittest.mock.patch` bilan fixture matnini qaytaradigan qilib almashtiriladi (tarmoqqa chiqilmaydi)
- Har bir topilgan kategoriya uchun alohida test: `Product`ning barcha maydonlari (`rate_min/max`, `term_min/max_months`, `amount_max_som`, `down_payment_pct`, `grace_period_months`, `payment_method`, `requires_collateral`) aniq qiymatlarga tekshiriladi
- Sahifaga xos "g'alati" holatlar (masalan aniq summa yo'qligi, ikki xil mijoz toifasi uchun bosqichli stavka) alohida test + tushuntiruvchi docstring bilan qamrab olinadi

## 7. Ish tartibi (implementatsiya bosqichida, har bir bank uchun)

1. Bankning "jismoniy shaxslar uchun kreditlash" bo'limidagi barcha mahsulot sahifalarini topish (real HTTP fetch orqali)
2. Har bir sahifa matnini o'qib, qaysi `categories.py` kategoriyasiga mos kelishini va stavka/muddat/summa/boshlang'ich badal/imtiyozli davr/to'lov usuli qanday yozilganini aniqlash
3. Scraper klassini yozish (`CATEGORY_URLS` + kerak bo'lsa maxsus `_build_*` metodlari)
4. Fixture HTML'larni saqlash, testlarni yozish
5. `registry.py`ga qo'shish
6. To'liq test to'plamini ishga tushirish (`pytest`)

Uch bank ketma-ket yoki mustaqil ravishda (bir-biriga bog'liq emas) amalga oshirilishi mumkin.
