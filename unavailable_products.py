"""Ba'zi banklar ma'lum bir toifada aniq mahsulotga ega emas (masalan, AgroBank
hozircha "Iste'mol krediti" mahsulotini taklif qilmaydi). Bunday holatlar
Product/ProductRow sxemasi orqali emas (u har doim aniq stavka/muddat/summa
talab qiladi), balki shu alohida, engil ro'yxat orqali frontendga "mahsulot
mavjud emas" sifatida ko'rsatiladi — reyting/saralash mantig'iga (masalan,
eng past stavkani hisoblash) aralashmaydi."""

from dataclasses import dataclass


@dataclass(frozen=True)
class UnavailableBank:
    bank: str
    reason: str


UNAVAILABLE_BANKS: dict[str, list[UnavailableBank]] = {
    "avtokredit_brend_birlamchi": [
        # SQB'ning "JAC-Avto imkon krediti" (jac-avto-imkon-uz) sahifasining
        # o'zida ham, uni ko'rsatuvchi avtokreditlar ro'yxati kartochkasida
        # ham 2026-08-10 holatiga ko'ra aniq "(Vaqtincha to'xtatilgan)"
        # yozuvi bor — jonli saytdan to'g'ridan-to'g'ri tasdiqlangan.
        UnavailableBank(bank="SQB", reason="Vaqtincha to'xtatilgan"),
    ],
    "istemol_krediti": [
        UnavailableBank(bank="AgroBank", reason="Mahsulot mavjud emas"),
    ],
    "mikroqarz_onlayn": [
        # Mikrokreditbank'ning "mikroqarzlar" hub sahifasidagi "Onlayn
        # Mikroqarz" (Ommabop, Mavrid ilovasi orqali) kartochkasi 2026-08-12
        # holatiga ko'ra endi "Vaqtincha to'xtatilgan" deb yozilmagan (bu
        # yozuv 2026-08-10'da bor edi, hozir yo'q) — lekin kartochkaning
        # o'zida hech qanday stavka/muddat/summa ko'rsatilmagan, faqat
        # Mavrid ilovasini yuklab olish taklif qilinadi (Google Play/App
        # Store havolalari). Saytda haqiqiy raqamlar yo'qligi sababli
        # Product qurib bo'lmaydi — pptx'dagi "26-29%, 50 mln" taxminiy
        # raqamlarini tasdiqlab bo'lmadi, shu sabab ular ishlatilmadi.
        UnavailableBank(bank="Mikrokreditbank", reason="Faqat mobil ilova orqali, saytda stavka ko'rsatilmagan"),
    ],
}


def get_unavailable_banks(category: str) -> list[UnavailableBank]:
    return UNAVAILABLE_BANKS.get(category, [])
