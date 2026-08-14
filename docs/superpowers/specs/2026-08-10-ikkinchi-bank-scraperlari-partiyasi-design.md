# Ikkinchi bank scraperlari partiyasi — Dizayn hujjati

**Sana:** 2026-08-10
**Holat:** Muhokama qilindi, tasdiqlandi

## 1. Maqsad va kontekst

Birinchi pilot bosqichda (2026-08-06) Anorbank, Asia Alliance Bank va Garant bank uchun scraperlar qo'shildi (18 ta bank endi qamrab olingan). Qolgan 13 ta bankdan (BDB, Trastbank, Davr Bank, OFB, AVO Bank, Poytaxt Bank, Universalbank, Apex Bank, Hayot Bank, Madad Invest Bank, KDB, Ziraat, Saderat Bank) foydalanuvchi bilan kelishilgan holda yana 3 tasi tanlandi, xuddi birinchi bosqichdagi jarayon bo'yicha: server-rendered ekanligi va aniq summa e'lon qilishi tekshirilgan holda.

## 2. Tanlangan banklar va qamrov

Barchasi jonli saytdan to'g'ridan-to'g'ri tekshirilgan (`curl` orqali, JS render qilinmagan holda):

- **Saderat Bank** (saderatbank.uz) — 2 ta kategoriya: `avtokredit`, `istemol_krediti`
- **Apex Bank** (apexbank.uz) — 3 ta kategoriya: `mikroqarz`, `mikroqarz_onlayn`, `ipoteka_tijorat`
- **BDB / Biznesni rivojlantirish banki** (brb.uz) — 3 ta kategoriya: `avtokredit`, `mikroqarz`, `ipoteka_davlat`

Jami: 3 bank, 8 ta mahsulot.

**Chiqarib tashlangan kategoriyalar va sabablari** (har biri aniq tekshirilgan, taxmin qilinmagan):
- Saderat: `ipoteka_tijorat` — maksimal summa "MHOning 8 baravari" (bazaviy hisoblash miqdori ko'paytiruvchisi) sifatida berilgan, aniq so'm raqami yo'q — Octobank'dagi bilan bir xil muammo. `mikroqarz`/`mikroqarz_onlayn`/`kredit_karta`/`avtokredit_ikkilamchi`/brend variantlari/`ipoteka_davlat` — bunday sahifalar saytda umuman mavjud emas.
- Apex Bank: `avtokredit` va `avtokredit_brend_birlamchi` (11 ta brend sahifasi bor!) — aniq summa faqat interaktiv kalkulyator slayderining `min`/`max` HTML atributida bor, ko'rinadigan matnda yo'q; bu ma'lumot manbai ishonchliligi past (bank rasman e'lon qilgan raqam emas, faqat UI cheklovi bo'lishi mumkin) — xavfsizlik uchun chiqarib tashlandi. `kredit_karta` (UZCARD) — imtiyozli davr faqat KUNLARDA berilgan (55 kun), bizning sxema OYLARNI talab qiladi — to'g'ridan-to'g'ri ishlatib bo'lmaydi, shu sabab bu partiyada chiqarib tashlandi. `istemol_krediti`, `avtokredit_ikkilamchi`, `avtokredit_elektro`, `ipoteka_davlat` — mos sahifa yo'q.
- BDB: `mikroqarz_onlayn` — bosh sahifadagi kartochka "vaqtincha to'xtatilgan" deb ko'rsatadi, lekin batafsil sahifaning o'zida bunday belgi yo'q — bu nomuvofiqlik xavfli, chiqarib tashlandi. `ipoteka_tijorat` — foiz stavkasi jadvali HTML jadval strukturasiga bog'liq (matn tekislanganda sarlavhalar yo'qoladi), ishonchli regex yozib bo'lmaydi. `kredit_karta`/overdraft — haqiqiy qayta tiklanadigan kredit liniyasi emas, mavjud kartaga bog'liq overdraft. `avtokredit_ikkilamchi`, brend/elektro variantlari — ko'pchiligida faqat "shartnoma qiymatining N%" formulasi bor, aniq summa yo'q (Octobank naqshi); BYD bilan bog'liq "mikroqarz" mahsulotlari esa aslida tadbirkorlik/biznes-reja talab qiladigan mahsulotlar, individual iste'molchi mahsuloti emas — chiqarib tashlandi.

## 3. Arxitektura — o'zgarish yo'q

Birinchi pilot bosqichdagi bilan bir xil: har bir bank uchun `scrapers/{bank}.py` fayli, `TextSectionScraper`dan meros, `scrapers/registry.py`ga ro'yxatdan o'tkaziladi. Uchala bankning sahifalarida ham takroriy sarlavha (hero-kartochka vs batafsil jadval) va noaniq foiz kontaminatsiyasi xavfi borligi sababli, har bir kategoriya uchun maxsus `_build_*_product()` metodlari ishlatiladi (Aloqabank/Anorbank/Asia Alliance Bank naqshiga o'xshab), umumiy bitta `CATEGORY_HEADINGS` yetarli emas.

Saderat Bank'ning `avtokredit` sahifasida qiymat o'z yorlig'idan OLDIN keladi (masalan "25% dan\nboshlang'ich to'lov") va muddat/summa "60 gacha oylar"/"600 gacha million so'm" kabi teskari so'z tartibida yozilgan — bu ikkalasi uchun ham bankka xos regex kerak (mavjud `extract_term_months`/`extract_amount_som` standart "N oygacha"/"N mln so'm" tartibini kutadi).

BDB'ning `ipoteka_davlat` muddati "20 yilgacha" (240 oy) — `extract_term_months`ning 120 oylik chegarasidan oshadi, shu sabab bu yerda ham to'g'ridan-to'g'ri regex ishlatiladi (`aab.py`dagi bir xil yechim).

## 4. Testlar va tekshiruv

Birinchi bosqichdagi bilan bir xil: har bir kategoriya uchun jonli sahifadan olingan haqiqiy HTML fixture, `fetch_html` mock qilinadi, real tekshirilgan qiymatlarga tayangan testlar.
