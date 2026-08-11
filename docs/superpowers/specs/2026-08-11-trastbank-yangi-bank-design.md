# TrastBank — yangi bank qo'shish — Dizayn hujjati

**Sana:** 2026-08-11
**Holat:** Muhokama qilindi, tasdiqlandi

## 1. Maqsad va kontekst

PPTX raqobatchi tahlilida (faqat qidiruv ko'rsatkichi sifatida ishlatiladi,
hech qanday raqam to'g'ridan-to'g'ri ishlatilmaydi) TrastBank bir nechta
kredit jadvalida tilga olinadi (ba'zilarida "vaqtincha to'xtatilgan" deb ham
belgilangan), lekin platformada TrastBank uchun umuman scraper yo'q edi.

## 2. Domen va arxitektura tekshiruvi

Domen: **trustbank.uz** (o'zbekcha nomi "Trastbank" bo'lsa ham, domen
inglizcha "trust" yozilishi bilan). `fetch_html` bilan to'g'ridan-to'g'ri
tekshirildi — sahifalar server tomonida render qilinadi (21-27 ming belgili
to'liq matn qaytadi).

## 3. Tanlangan kategoriyalar va qamrov (barchasi jonli saytdan tekshirilgan)

- **`mikroqarz`** — `/uz/private/crediting/microloans/` ("Mikroqarz"):
  sahifada UCHTA mijoz-toifasi ketma-ket keladi ("Doimiy daromadga ega
  bo'lgan mijozlar uchun" — 100 mln, 12/36/60 oy, 28-31,9% (ta'minot
  turiga qarab ikki sub-jadval); "O'zini-o'zi band qilgan shaxslarga" — 50
  mln, 12/24/36 oy, 28-30%; "...ish haqi loyihasi...Ta'lim va sog'liqni
  saqlash xodimlari uchun" — 100 mln, 12/36/60 oy, 24-27,9%), "Mikroqarz
  rasmiylashtirishda talab qilinadigan hujjatlar" bo'limigacha bitta
  bo'lak sifatida olinadi — barcha uch toifaning stavka/muddat qiymatlari
  birlashtirilib rate_min/rate_max (24,0-31,9%) va term_min/term_max
  (12-60 oy) hisoblanadi, amount esa eng kattasi (100 mln, ikki toifada
  bir xil) olinadi. Sahifa muqaddimasida aniq "Mikroqarzning imtiyozli
  davri: mavjud emas" — 0 oy. (DIQQAT: saytda yana alohida "Qulay
  mikroqarz" nomli, kichikroq ikkinchi mahsulot ham bor —
  `/uz/private/crediting/mikroqarzlar/`, 5/10 mln so'm, 19,5-20,9%, 36 oy —
  bu mustaqil, kichikroq mahsulot, "microloans" sahifasidagi asosiy
  "Mikroqarz"dan farqli, boshqa banklardagi "bitta vakillik mahsuloti"
  konvensiyasi bilan mos ravishda chiqarib tashlangan.)
- **`ipoteka_tijorat`** —
  `/uz/private/crediting/bankning-o-z-mablag-lari-hisobidan-ajratiladigan-ipoteka-krediti/`
  ("Bankning o'z mablag'lari hisobidan..."): raqamlangan jadval, davlat
  mablag'i haqida hech qanday ishora yo'q (sof bank mablag'i, birlamchi VA
  ikkilamchi bozordan). Muddat 120 oygacha, stavka 23% (doimiy daromadli) /
  24% (o'zini o'zi band qilgan), boshlang'ich badal 20%/25%, summa
  "700,0 mln so'mgacha" (BHM-asosli ikkita nisbat qiymati — 2500/3000
  barobar — ham bor, lekin literal 700 mln son ustuvor va ishonchli
  manba). To'lov usuli "Annuitet yoki differensial". Muqaddima paragrafida
  aniq "Kreditning imtiyozli davri mavjud emas" — 0 oy.
- **`ipoteka_davlat`** — `/uz/private/crediting/sharq-bahori-ipoteka-krediti/`
  ("Sharq bahori ipoteka krediti"): "Iqtisodiyot va moliya vazirligi
  mablag'lari hisobidan" deb aniq yozilgan davlat-dasturi ipoteka mahsuloti
  (Yangi Toshkent shahridagi "Sharq bahori" turar-joy majmuasidan xonadon
  xaridi uchun). "Kreditning maksimal miqdori: 800,0 mln so'mdan ko'p
  bo'lmagan miqdorda" (davlat qismi alohida 480 mln sub-limitga ega, lekin
  umumiy 800 mln ustuvor). Muddat "240 oydan ko'p bo'lmagan". Stavka 17%
  (doimiy daromadli) / 18% (o'zini o'zi band qilgan) — sahifada yana
  alohida shart bor: agar garov 20 kun ichida rasmiylashtirilmasa, stavka
  25%ga o'zgaradi — bu JARIMA sharti, asosiy stavka oralig'iga
  kiritilmaydi. Boshlang'ich badal 15% (davlat qismi) / 20% (bank qismi).
  To'lov usuli "Annuitet yoki differensial". Imtiyozli davr haqida sahifada
  aniq gap yo'q — `None` qoldiriladi.

**Chiqarib tashlangan kategoriyalar va sabablari** (har biri aniq
tekshirilgan, taxmin qilinmagan):
- `avtokredit` (`/auto/`) — sahifada uchta mijoz-toifasi bo'yicha to'liq
  stavka/muddat/boshlang'ich-badal jadvali bor, lekin hech qanday aniq
  maksimal SUMMA (so'm) hech qayerda ko'rsatilmagan — faqat bo'sh
  kalkulyator maydoni ("Talab qilinadigan kredit summasini kiriting").
  Octobank naqshi bilan bir xil — aniq son yo'q, chiqarib tashlandi.
- `avtokredit_brend_birlamchi` (KIA/Chery/Haval/Changan) — xuddi shu sabab,
  aniq summa yo'q.
- `istemol_krediti` ("Universal" iste'mol krediti) — summa BHM
  ko'paytiruvchisi sifatida berilgan ("BHMning 100/200 barobarigacha"),
  literal so'm raqami yo'q — Octobank naqshi.
- Birlamchi bozordan uy-joy ipoteka krediti (alohida sahifa) — summa
  "kredit miqdorining uy-joy (garov) qiymatiga nisbati" sifatida (LTV
  nisbat, literal son emas) berilgan — chiqarib tashlandi.
- `kredit_karta` — mos, alohida "revolving" kredit-karta mahsuloti
  (limit+stavka+imtiyozli davr bilan) topilmadi — faqat oddiy to'lov
  kartalari (VISA-Humo, UzCard-MasterCard) tilga olingan.
- "Golden house property group" ipoteka, "O'zshahar qurilish invest"
  ipoteka, "Rasmiy daromad manbaiga ega bo'lmaganlar uchun" ipoteka —
  quruvchi-xos yoki niche variantlar, vaqt cheklovi sabab bu partiyada
  tekshirilmadi.
- Quyosh panellari krediti, "Biznesga ilk qadam" — platformaning mavjud
  kategoriyalariga mos kelmaydi.
- Overdraft — boshqa banklardagi kabi mos alohida kategoriya yo'q.

## 3.1. Yangi texnik nozikliklar (bu bankka xos, ilgari uchramagan)

- **So'z shaklidagi foizlar**: `ipoteka_tijorat` va `ipoteka_davlat`
  sahifalarida stavka/boshlang'ich-badal "%" belgisi bilan EMAS, "23 foiz"/
  "20 foiz" so'z shaklida yozilgan — standart `extract_percentages` faqat
  "%" belgisini taniydi, hech narsa topmaydi. Maxsus regex kerak:
  `re.compile(r"(\d{1,2}(?:[.,]\d{1,2})?)\s*foiz")`.
- **Vergul-o'nlik "N,0 mln" naqshi**: `ipoteka_tijorat`da "700,0 mln
  so'mgacha", `ipoteka_davlat`da "800,0 mln so'mdan ko'p bo'lmagan" — bu
  yerdagi ",0" standart `extract_amount_som`ning mln-regexini
  (`\d{1,5}\s*mln`) chalg'itadi: regex vergul keyingi "0" dan
  boshlab moslikni topib oladi ("0 mln" -> 0 so'm!). Chaqirishdan oldin
  ",0 mln" -> " mln" almashtirish kerak (Kapitalbank'dagi ",00 so" -> "
  so" konvensiyasi bilan bir xil yechim).
- **"N oydan ko'p bo'lmagan" muddat shakli**: `ipoteka_davlat`da "240
  oydan ko'p bo'lmagan muddatga" — standart `extract_term_months` faqat
  "N oygacha"/"N oydan M oygacha" naqshlarini taniydi, bu yangi shaklni
  emas. Maxsus regex: `re.search(r"(\d{1,3})\s*oydan\s*ko", term_section)`.

## 4. Arxitektura

Boshqa banklar bilan bir xil: `scrapers/trastbank.py`, `TextSectionScraper`dan
meros, har bir kategoriya o'z alohida sahifasidan (`CATEGORY_URLS`). Ko'p
sahifalarda raqamlangan jadval (invoice-uslubidagi "1/2/3..." qatorlar)
formatidan foydalaniladi — har bir band nomi (masalan "Kredit miqdori",
"Yillik foiz stavkasi") sahifada FAQAT bir marta uchraydi, shu sabab
extract_section bilan ikki qo'shni band orasidan to'g'ridan-to'g'ri olish
yetarli, ko'p bosqichli toraytirish shart emas (Ipoteka mahsulotlarida).

`mikroqarz` sahifasida esa uch bosqichli (12/36/60 oy) muddat-stavka
jadvali bor — barcha uchta qiymat yig'ilib rate_min/rate_max va
term_min/term_max hisoblanadi (SQB avtokredit'dagi bilan bir xil naqsh).

Jami: 1 bank, 3 ta mahsulot.

## 5. Testlar va tekshiruv

Boshqa banklar bilan bir xil: har bir kategoriya uchun jonli sahifadan
olingan haqiqiy HTML fixture, `fetch_html` mock qilinadi, real tekshirilgan
qiymatlarga tayangan testlar.
