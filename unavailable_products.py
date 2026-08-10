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
        # Mikroqarz" (Ommabop, Mavrid ilovasi orqali) kartochkasining
        # o'zida 2026-08-10 holatiga ko'ra aniq "Vaqtinchalik to'xtatilgan"
        # yozuvi bor — jonli saytdan to'g'ridan-to'g'ri tasdiqlangan.
        UnavailableBank(bank="Mikrokreditbank", reason="Vaqtincha to'xtatilgan"),
    ],
}


def get_unavailable_banks(category: str) -> list[UnavailableBank]:
    return UNAVAILABLE_BANKS.get(category, [])
