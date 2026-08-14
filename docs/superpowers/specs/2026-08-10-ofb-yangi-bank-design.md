# OFB (Orient Finans Bank) — yangi bank qo'shish — Dizayn hujjati

**Sana:** 2026-08-10
**Holat:** Muhokama qilindi, tasdiqlandi

## 1. Maqsad va kontekst

Foydalanuvchi tomonidan taqdim etilgan raqobatchi tahlili (PPTX, faqat qidiruv
ko'rsatkichi sifatida ishlatiladi — hech qanday raqam to'g'ridan-to'g'ri
ishlatilmaydi) barcha 11 ta kredit jadvalida OFB'ni tilga oladi, lekin
platformada OFB uchun umuman scraper yo'q edi (`scrapers/registry.py`da yo'q).
Bu eng katta va izchil bo'shliq bo'lgani sabab OFB'ni yangi bank sifatida
qo'shish kerak.

## 2. Domen va arxitektura tekshiruvi

Domen: **ofb.uz**. `fetch_html` (oddiy `requests.get`, JS bajarmaydi) bilan
to'g'ridan-to'g'ri tekshirildi — sahifalar server tomonida render qilingan
(37-47 ming belgili to'liq matn qaytadi, JS-SPA bo'sh-DOM muammosi yo'q).

**Muhim eslatma:** sayt navigatsiyasida "Sayt sinov rejimida ishlamoqda"
(sayt test/sinov holatida) degan banner bor. Bu ehtimol ichki texnik
belgi (masalan yangi dizaynga o'tish jarayoni) — sahifalardagi raqamlar
o'zaro izchil va PPTX'dagi mustaqil (raqobatchi tomonidan alohida
to'plangan) raqamlar bilan mos keladi, shuning uchun haqiqiy amaldagi
ma'lumot sifatida ishonch bilan ishlatish mumkin, lekin bu holat orchestrator/
monitoring bosqichida hisobga olinishi lozim (sayt "sinov" holatidan
chiqqanda URL struktura o'zgarishi mumkin).

## 3. Tanlangan kategoriyalar va qamrov (barchasi jonli saytdan tekshirilgan)

- **`avtokredit`** — "Oson avtokredit" (`/kreditlar/oson-avtokredit`): FAQ
  formatida aniq raqamlar — "Avtokreditning maksimal miqdori — 800 mln
  so'mgacha", "Avtokreditni 60 oygacha", stavka boshlang'ich badal ulushiga
  bog'liq to'rt bosqichli jadval (25% dan — 24,5%; 30% dan — 23,9%; 40%
  dan — 22,9%; 50% dan — 21,9%), min boshlang'ich badal 25%.
- **`avtokredit_elektro`** — "Avtokredit BYD" (`/kreditlar/avtokredit-byd`):
  xuddi shu FAQ shabloni — 800 mln so'mgacha, 36 yoki 60 oy, stavka jadvali
  (25% dan — 21,5%; 30% dan — 20,9%; 40% dan — 19,9%; 50% dan — 18,9%), min
  boshlang'ich badal 25%. (Saytda yana alohida "Denza"/"BYD Carryover
  New"/"BYD Special Offer" sahifalari ham bor — bularning barchasi xuddi
  shu BYD dasturining aniq model-nomli marketing variantlari, alohida
  mahsulot sifatida qo'shilmaydi — boshqa banklardagi "bitta vakillik
  mahsuloti" konvensiyasi bilan bir xil.)
- **`mikroqarz`** — "Ishonch" mikroqarzi (`/kreditlar/mikroqarzlar` hub
  sahifasidagi kartochka): 100 mln so'mgacha, 36 oygacha, 24% dan.
- **`mikroqarz_onlayn`** — "Onlayn mikroqarz" (`/kreditlar/onlayn-mikroqarz`):
  hero-kartochkada 50 mln so'mgacha va 30% aniq ko'rsatilgan; muddat esa
  faqat pastroqdagi FAQ javobida ("Mikroqarz muddati" -> "24 oygacha")
  bor — hero-kartochkada yo'q, shu sabab FAQ bo'limi ham tekshirilishi
  shart.
- **`ipoteka_davlat`** — "Foydali ipoteka" (`/kreditlar/foydali-ipoteka`):
  aralash davlat+bank mablag'i ("Davlat qismi bo'yicha — yiliga 17%, Bank
  tomonidan beriladigan qism bo'yicha — yiliga 25%" — bevosita "davlat
  dasturi" so'zi bilan bog'langan), summa "1,06 mlrd so'mgacha — Toshkentda
  (480 mln so'mgacha davlat dasturi bo'yicha, qolgan summa — bank
  hisobidan)", muddat 240 oygacha (20 yil). PPTX'ning o'zi ham OFB'ni aynan
  shu turkumga ("за счет средств Министерства финансов") joylashtirgan —
  mustaqil tasdiq.
- **`kredit_karta`** — "Kredit karta Niyat" (`/kartalar/niyat-kredit-kartasi`
  — boshqa OFB kredit mahsulotlaridan farqli, `/kartalar/` yo'lida, `/kreditlar/`da
  emas): limit 50 mln so'mgacha (qayta tiklanadigan), stavka 34%, imtiyozli
  (foizsiz) davr 45 kun, "Amal qilish muddati" 3 yil (36 oy).

**Chiqarib tashlangan kategoriyalar va sabablari:**
- `istemol_krediti` — `/kreditlar/istemol-kreditlari` sahifasi mavjud (URL
  ishlaydi, sahifa sarlavhasi bor), lekin sahifa tanasida "Iste'mol krediti"
  nomli haqiqiy mahsulot kartochkasi yoki aniq stavka/summa umuman yo'q —
  hozircha bu mahsulot aslida faol emas ko'rinadi.
- `ipoteka_tijorat` — PPTX'da "OFB | Ipoteka krediti (birlamchi 2.0)" deb
  alohida qator bor, lekin ofb.uz saytida bunga mos alohida (faqat
  bankning o'z mablag'i, davlat dasturisiz) ipoteka sahifasi topilmadi —
  vaqt cheklovi sabab qidiruv davom ettirilmadi, keyingi partiyada qayta
  ko'rib chiqilishi mumkin.
- `avtokredit_ikkilamchi`, `avtokredit_brend_ikkilamchi` — PPTX'da OFB bu
  ikkalasida ham bor, lekin bu partiyada vaqt yetishmagani sabab
  tekshirilmadi.
- Overdraft mahsulotlari (`/kreditlar/overdraft`,
  `/kreditlar/qulay-hamyon-overdrafti`) — platformada mos alohida kategoriya
  yo'q (`kredit_karta`dan farqli haqiqiy qayta tiklanadigan overdraft), shu
  sabab kiritilmadi.

## 4. Arxitektura

Boshqa banklar bilan bir xil: `scrapers/ofb.py`, `TextSectionScraper`dan
meros, `CATEGORY_URLS` (har bir kategoriya o'z alohida sahifasidan, `mikroqarz`
bundan mustasno — u `mikroqarzlar` hub sahifasining bitta kartochkasidan
olinadi). Ko'p sahifalarda bir xil "N. <sarlavha>\n...\n<qiymat>" FAQ/raqamli
ro'yxat shabloni takrorlanadi (`01. Kredit summasi`, `02. Kredit muddati`,
`03. Foiz stavkasi` kabi yoki oddiy "Savol?\n...\nJavob." formatida) — har bir
kategoriya uchun maxsus `_build_*_product()` metodi kerak (umumiy bitta
CATEGORY_HEADINGS yetarli emas, chunki har sahifada raqamli javoblar orasida
boshqa aloqasiz % bor — masalan qarzni kechiktirish jarimasi kabi).

`mikroqarz` va `mikroqarz_onlayn` ikkalasi ham **bitta hub sahifadan**
(`/kreditlar/mikroqarzlar`) olinadi — ikkita alohida HTTP so'rovi o'rniga bir
marta fetch qilinib, ikkita mahsulot ham shu bitta matndan ajratib olinadi
(mikroqarz_onlayn uchun esa qo'shimcha ravishda alohida `/kreditlar/onlayn-mikroqarz`
sahifasidan faqat muddat FAQ javobi olinadi, chunki hub kartochkada muddat
yo'q).

Jami: 1 bank, 6 ta mahsulot.

## 5. Testlar va tekshiruv

Boshqa banklar bilan bir xil: har bir kategoriya uchun jonli sahifadan
olingan haqiqiy HTML fixture, `fetch_html` mock qilinadi, real tekshirilgan
qiymatlarga tayangan testlar.
