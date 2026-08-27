# Auth (login/parol) va Admin Panel — Dizayn hujjati

**Sana:** 2026-08-27
**Holat:** Muhokama qilindi, tasdiqlandi

## 1. Maqsad va kontekst

Hozirgi loyihada hech qanday autentifikatsiya yo'q — `api/main.py`dagi barcha endpointlar (`/products`, `/recommend`, `/export-excel` va h.k.) ochiq, DB'da userlar jadvali umuman mavjud emas, frontendda esa router kutubxonasi ham ishlatilmaydi (`Sidebar` state-based navigatsiya bilan ishlaydi).

Bu hujjat butun saytni login/parol bilan yopishni, ikkita rolni (`admin`, `user`) va admin uchun foydalanuvchilarni boshqarish panelini (qo'shish, ro'yxat, tahrirlash) belgilaydi.

## 2. Ko'lam

**Kiradi:**
- Butun sayt login talab qiladi — login qilmasdan hech qanday sahifa/API javob bermaydi
- Ikkita rol: `admin`, `user`
- `role=admin` bo'lganda header'da "Dashboard" tugmasi ko'rinadi, bosilganda admin panelga o'tadi (`role=user`da tugma umuman ko'rinmaydi)
- Admin panel: userlar ro'yxati, yangi user qo'shish (username, parol, role), mavjud userni tahrirlash (username, parol, role)
- Chiroyli, bank logotiplari (SQB va boshqalar) bilan bezatilgan auth sahifa
- Sessiya 30 kun davom etadi (JWT, `localStorage`)
- Birinchi admin `ADMIN_USERNAME`/`ADMIN_PASSWORD` env o'zgaruvchilar orqali avtomatik yaratiladi
- Admin o'z rolini `user`ga o'zgartira olmaydi (o'zini tizimdan chetlatib qo'yishning oldini olish)

**Kirmaydi (keyingi bosqichga qoldiriladi):**
- User o'chirish
- Foydalanuvchi o'z parolini o'zi almashtirishi
- "Parolni unutdim" oqimi
- Ko'p faktorli autentifikatsiya

## 3. Ma'lumotlar modeli

`db/models.py`ga yangi jadval:

```python
class UserRow(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20))  # "admin" | "user"
    created_at: Mapped[datetime] = mapped_column(DateTime)
```

`role` uchun alohida enum jadval kerak emas — `Literal["admin", "user"]` bilan Pydantic darajasida tekshiriladi, DB darajasida oddiy `String`.

## 4. Backend — auth mexanizmi

Yangi `auth/` paketi:

- `auth/security.py`:
  - `hash_password(password: str) -> str` — `bcrypt` orqali
  - `verify_password(password: str, password_hash: str) -> bool`
  - `create_access_token(user_id: int, username: str, role: str) -> str` — `PyJWT`, `exp` claim = 30 kun, `SECRET_KEY` env o'zgaruvchidan (`AUTH_SECRET_KEY`, bo'lmasa startup'da xato bilan to'xtaydi — bu xavfsizlik uchun majburiy)
  - `decode_access_token(token: str) -> dict | None` — muddati tugagan/noto'g'ri bo'lsa `None`

- `auth/dependencies.py`:
  - `get_current_user(request)` — `Authorization: Bearer <token>` headerini o'qiydi, token yo'q/yaroqsiz bo'lsa `401` (`HTTPException`)
  - `require_admin(user=Depends(get_current_user))` — `role != "admin"` bo'lsa `403`

Yangi `requirements.txt` qatorlar: `PyJWT`, `bcrypt`.

`AUTH_SECRET_KEY` — `.env.example`ga qo'shiladi (production'da Railway "Variables" bo'limida sozlanadi, xuddi `OPENAI_API_KEY` kabi).

### Bootstrap (birinchi admin)

`api/main.py`dagi `lifespan` funksiyasiga (mavjud scheduler init'i bilan bir qatorda): agar `users` jadvalida hech qanday qator bo'lmasa va `ADMIN_USERNAME`/`ADMIN_PASSWORD` env o'zgaruvchilar mavjud bo'lsa — shu login/parol bilan `role="admin"` qator yaratiladi. Ikkalasi ham yo'q bo'lsa, hech narsa qilinmaydi (log orqali ogohlantirish chiqadi: "Admin akkaunt topilmadi, ADMIN_USERNAME/ADMIN_PASSWORD env o'zgaruvchilarni sozlang").

### Endpointlar

| Method | Path | Himoya | Tavsif |
|---|---|---|---|
| POST | `/auth/login` | yo'q | `{username, password}` → `{access_token, username, role}` yoki `401` |
| GET | `/auth/me` | `get_current_user` | `{username, role}` — sahifa yangilanganda sessiyani tiklash uchun |
| GET | `/admin/users` | `require_admin` | `[{id, username, role, created_at}]` |
| POST | `/admin/users` | `require_admin` | `{username, password, role}` → yangi user, `409` agar username band |
| PATCH | `/admin/users/{id}` | `require_admin` | `{username?, password?, role?}` → yangilangan user; agar `id == joriy_admin_id` va `role="user"` yuborilsa → `400` |

Mavjud barcha endpointlar (`/products`, `/categories`, `/unavailable-banks`, `/recommend`, `/explain-product`, `/export-excel`, `/export-excel-all`, `/trigger-scrape`) `Depends(get_current_user)` oladi.

CORS middleware'ga o'zgarish shart emas — `allow_headers=["*"]` `Authorization` headerini ham qamrab oladi.

## 5. Frontend

### Auth holati

`lib/AuthContext.tsx` — mavjud `LanguageContext.tsx` bilan bir xil patternda:
- Token `localStorage`da `bozor-tahlili-token` kaliti bilan saqlanadi
- Provider yuklanganda token bo'lsa `GET /auth/me` chaqiradi; muvaffaqiyatli bo'lsa `{username, role}` state'ga yoziladi, `401` kelsa token tozalanadi
- `login(username, password)`, `logout()` funksiyalari expose qilinadi
- `useAuth()` hook

`lib/api.ts` — barcha `fetch` chaqiruvlariga `Authorization: Bearer <token>` header qo'shiladi (token `localStorage`dan o'qiladi); javob `401` bo'lsa, token tozalanadi va sahifa `AuthContext` orqali login holatiga qaytadi (custom event yoki `AuthContext`ning o'zi `api.ts`dan import qilingan kichik "logout callback" registratori orqali — dumaloq import bo'lmasligi uchun oddiy `let onUnauthorized: (() => void) | null` pattern ishlatiladi).

### Navigatsiya

Router kutubxonasi qo'shilmaydi (loyiha hozir ham state-based). `App.tsx`da:

```
view: 'login' | 'app' | 'admin'
```

- `user == null` → `LoginPage`
- `user != null && view == 'admin'` → `AdminPanel` (faqat `role == 'admin'` bo'lsa bu holatga o'tish mumkin)
- aks holda → hozirgi asosiy ilova

### Yangi komponentlar

- **`components/LoginPage.tsx`** — markazlashtirilgan karta, fonida/atrofida bank logotiplari (`assets/bank-logos/*.svg`, mavjud `lib/bankLogos.ts`dan foydalaniladi) yumshoq tarzda joylashtiriladi (masalan xira/kichik grid yoki subtle marquee — `design-quality` talablariga mos, generic forma bo'lmasligi kerak). Username + parol input, "Kirish" tugma, xato xabari joyi.
- **`components/AdminPanel.tsx`** — sarlavha + "Ortga" tugma (asosiy ilovaga qaytish), userlar jadvali (`username`, `role`, `created_at`), har qatorda "Tahrirlash" tugmasi. Qo'shish ham, tahrirlash ham bitta `UserFormModal.tsx` komponenti orqali amalga oshiriladi — mavjud modal naqshidan (`.modal-overlay`, `.modal-btn-primary`, "Compare mode" dizaynida ishlatilgan) foydalaniladi, `role="dialog"` `aria-modal="true"`, `Esc` bilan yopiladi. Forma: username, parol (tahrirlashda bo'sh qoldirilsa parol o'zgarmaydi — placeholder "o'zgartirmaslik uchun bo'sh qoldiring"), role select. Tepada "Yangi user qo'shish" tugmasi shu modalni bo'sh holatda ochadi.
- Header (`App.tsx` ichidagi mavjud `banner` qismi)ga: joriy `username`, `role == 'admin'` bo'lsa "Dashboard" tugma, va "Chiqish" tugma qo'shiladi.

### Xato holatlari

- Login xato (`401`) → forma ostida "Login yoki parol noto'g'ri" xabari
- `AdminPanel`da username band (`409`) → forma xatosi "Bu login band"
- O'z-o'zini demote (`400`) → forma xatosi "O'z rolingizni o'zgartira olmaysiz"
- Har qanday himoyalangan so'rov `401` qaytarsa → avtomatik login sahifasiga

## 6. Testing

**Backend** (`tests/api/test_auth.py`, mavjud pytest+fixture patterniga mos, `sqlite:///:memory:`):
- To'g'ri login → token qaytadi
- Noto'g'ri parol → `401`
- Himoyalangan endpoint (masalan `/products`) tokensiz → `401`
- Admin-only endpoint (`/admin/users`) `role=user` token bilan → `403`
- Yangi user qo'shish → `/admin/users` ro'yxatida ko'rinadi
- Username band bo'lsa → `409`
- Admin o'zini `role=user` qilishga urinsa → `400`

**Frontend** (vitest + RTL, mavjud komponent testlariga mos):
- `LoginPage` — muvaffaqiyatli/xato login smoke test
- `AdminPanel` — user qo'shish/tahrirlash forma smoke test
- `role=user` bo'lganda "Dashboard" tugma render bo'lmasligi

Coverage maqsadi: `auth/` va yangi `api/main.py` endpointlar uchun 80%+ (loyihaning umumiy standartiga mos).
