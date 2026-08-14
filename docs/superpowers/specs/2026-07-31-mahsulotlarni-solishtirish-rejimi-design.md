# Mahsulotlarni solishtirish rejimi ("Compare mode") — Dizayn hujjati

**Sana:** 2026-07-31
**Holat:** Muhokama qilindi, tasdiqlandi

## 1. Maqsad va kontekst

Hozirgi rate board (`ProductTable.tsx`) barcha banklarni bitta ustundan tartiblab ko'rsatadi, "Market Pulse" esa faqat eng arzon bitta mahsulotni ajratib chiqaradi. Foydalanuvchi 2-3 ta muayyan mahsulotni (masalan SQB va ikkita raqobatchi) yonma-yon, barcha maydonlar bo'yicha solishtirmoqchi bo'lsa, buni faqat jadvalni ko'zdan kechirib, qo'lda qilishi kerak.

Bu hujjat rate board ustiga qo'shiladigan **solishtirish rejimi**ni belgilaydi: qatorlarni belgilash → suzuvchi panel → to'liq ekran solishtirish modali.

## 2. Ko'lam

**Kiradi:**
- Rate board qatorlarida checkbox orqali mahsulot tanlash (kategoriya ichida, maksimum 3 ta)
- Suzuvchi "Compare bar" — tanlangan mahsulotlar soni va "Solishtirish" tugmasi
- To'liq ekran solishtirish modali — transponirlangan jadval, har bir atribut qatorida "eng yaxshi qiymat" avtomatik ranglanadi
- UZ/RU tarjima, klaviatura/screen-reader qulayligi, unit testlar

**Kirmaydi:**
- AI-generatsiya qilingan solishtiruvchi izoh (backend endpoint kerak bo'lardi — keyingi bosqichga qoldirildi)
- Kategoriyalararo solishtirish (schema turlicha bo'lgani uchun ma'nosiz)
- Tanlovni URL yoki localStorage'da saqlash (v1'da faqat session-ichida, sahifa yangilanganda yo'qoladi)

## 3. Tanlash mexanizmi

- `App.tsx`da yangi state: `const [compareKeys, setCompareKeys] = useState<Set<string>>(new Set())`
- Mahsulot kaliti: `` `${product.bank}::${product.product_name}` `` (bitta kategoriya ichida yagona)
- `activeCategory` o'zgarganda `compareKeys` avtomatik bo'shatiladi (`useEffect`, dep: `[activeCategory]`)
- `ProductTable`ga yangi propslar: `compareKeys`, `onToggleCompare(key)`, `maxCompare=3`
- Har bir qatorda (rank ustunidan oldin, yangi 24px ustun) `<input type="checkbox">`:
  - Tanlangan bo'lsa — checked
  - `compareKeys.size >= maxCompare` va shu qator tanlanmagan bo'lsa — `disabled`, past opacity
  - `unavailableBanks` qatorlarida checkbox ko'rsatilmaydi (mahsulot mavjud emas, solishtirib bo'lmaydi)
- Grid ustunlari: `gridTemplateColumns()` funksiyasiga checkbox uchun qo'shimcha `24px` prefiks qo'shiladi

## 4. Compare bar (`CompareBar.tsx`, yangi komponent)

- `compareKeys.size > 0` bo'lgandagina render qilinadi (aks holda `null`)
- Pozitsiya: ekran pastida markazlashtirilgan, `position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%)`, `z-index: 90`
- Tarkib: har bir tanlangan mahsulot uchun kichik chip (bank logotipi + nomi + ✕ tugma — bosilganda `onToggleCompare(key)` chaqiriladi), o'ng tomonda **"Solishtirish (N)"** asosiy tugma (mavjud `.modal-btn-primary` uslubi) va "Bekor qilish" matn-tugma (barcha tanlovni tozalaydi)
- `role="region"` + `aria-live="polite"` — chip qo'shilganda/olib tashlanganda screen reader "N ta mahsulot tanlandi" deb o'qiydi (i18n orqali)
- Reduced-motion: kirish animatsiyasi `prefers-reduced-motion` bilan o'chadi (mavjud namunaga mos)

## 5. Solishtirish modali (`CompareModal.tsx`, yangi komponent)

- Mavjud `.modal-overlay` naqshidan foydalanadi, lekin kengroq karta: yangi CSS klass `.compare-modal-card` (`max-width: 960px`, kichik ekranlarda ichki `overflow-x: auto`)
- `role="dialog"` `aria-modal="true"`, ochilganda fokus modal ichiga o'tadi, `Esc` yopadi, overlay bosilganda ham yopiladi
- Sarlavha: "Mahsulotlarni solishtirish" / "Сравнение продуктов"
- Tarkib — transponirlangan jadval: chapda atribut nomi ustuni, o'ngda har bir tanlangan mahsulot uchun bittadan ustun
  - Ustun sarlavhasi: bank logotipi + nomi (+ `house-flag` agar SQB bo'lsa) + mahsulot nomi + ✕ (o'sha ustunni solishtirishdan chiqarish)
  - Qatorlar: **Stavka**, **Muddat**, **Maks. summa**, so'ng `getProductColumns(schema, category, lang)` natijasidan kelgan schema-ga xos ustunlar (Boshlang'ich to'lov / Imtiyozli davr / Maxsus shartlar / To'lov usuli — kategoriyaga qarab farqlanadi, xuddi asosiy jadvaldagidek)
- **"Eng yaxshi qiymat" ranglash mantiqi** (`compareLogic.ts`, yangi fayl, alohida unit-testlanadi):

  | Atribut | Yo'nalish | Izoh |
  |---|---|---|
  | Stavka (`rate_min`) | past = yaxshi | `--good` rang bilan ajratiladi |
  | Boshlang'ich to'lov (`down_payment_pct`) | past = yaxshi | `null` = solishtirilmaydi (raqam yo'q) |
  | Maks. summa (`amount_max_som`) | yuqori = yaxshi | |
  | Imtiyozli davr (`grace_period_months`) | bor (>0) = yaxshi | |
  | Muddat, To'lov usuli, Maxsus shartlar | **neytral** | Xolisona "yaxshi/yomon" yo'q — ranglanmaydi |
- Faqat 2 yoki 3 ta ustun bir xil qiymatga ega bo'lsa (teng), barchasi birdek ranglanadi (masalan ikkala bank ham eng past stavkada teng bo'lsa)
- Agar foydalanuvchi ✕ orqali 1 tagacha mahsulot qoldirsa, modal avtomatik yopiladi (solishtirish uchun kamida 2 ta shart)

## 6. Fayllar va o'zgarishlar ro'yxati

| Fayl | O'zgarish |
|---|---|
| `frontend/src/lib/compareLogic.ts` | **Yangi.** Best-value aniqlash funksiyalari (`compareLogic.test.ts` bilan) |
| `frontend/src/components/CompareBar.tsx` | **Yangi** (+ `.test.tsx`) |
| `frontend/src/components/CompareModal.tsx` | **Yangi** (+ `.test.tsx`) |
| `frontend/src/components/ProductTable.tsx` | Checkbox ustuni, `compareKeys`/`onToggleCompare`/`maxCompare` propslari |
| `frontend/src/App.tsx` | `compareKeys` state, kategoriya almashganda tozalash, `CompareBar`/`CompareModal` render qilish |
| `frontend/src/lib/i18n.ts` | Yangi kalitlar: `compareButton`, `compareBarClear`, `compareModalTitle`, `compareLiveRegion` va h.k. |
| `frontend/src/styles/tokens.css` | `.compare-bar`, `.compare-chip`, `.compare-modal-card`, `.compare-cell-best` klasslari |

## 7. Test rejasi

- `compareLogic.test.ts`: har bir atribut yo'nalishi uchun (past/yuqori/bool/neytral), teng qiymatlar holati, `null` qiymatlar holati
- `ProductTable.test.tsx`: checkbox bosilganda `onToggleCompare` chaqirilishi, `maxCompare` yetganda boshqa checkbox'lar disabled bo'lishi
- `CompareBar.test.tsx`: render/render-emas shartlari, chip ✕ bosilganda to'g'ri kalit chiqarilishi
- `CompareModal.test.tsx`: highlight to'g'ri qatorga qo'llanishi, 1 tagacha qolganda avtomatik yopilish, Esc bilan yopilish
