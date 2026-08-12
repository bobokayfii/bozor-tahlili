"""Ba'zi banklar ma'lum bir toifada aniq mahsulotga vaqtincha ega emas
(masalan, SQB'ning "JAC-Avto imkon krediti" sahifasida aniq "Vaqtincha
to'xtatilgan" deb yozilgan). Bunday holatlar Product/ProductRow sxemasi
orqali emas (u har doim aniq stavka/muddat/summa talab qiladi), balki shu
alohida, yengil ro'yxat orqali frontendga ko'rsatiladi — reyting/saralash
mantig'iga (masalan, eng past stavkani hisoblash) aralashmaydi.

MUHIM: faqat status="suspended" (haqiqatan ham vaqtincha to'xtatilgan,
saytning o'zida shunday deb yozilgan) yozuvlar jadvalda ko'rsatiladi —
get_unavailable_banks() buni filtrlaydi. status="not_offered" (bank bu
mahsulotni umuman taklif qilmaydi/hech qachon taklif qilmagan) yozuvlar
faqat hujjatlashtirish/audit maqsadida shu yerda saqlanadi, lekin
jadvalda HECH QACHON ko'rsatilmaydi — bunday bank/toifa juftligi uchun
jadvalda oddiygina hech qanday qator bo'lmaydi (xuddi bu yozuv umuman
mavjud bo'lmagandek)."""

from dataclasses import dataclass
from typing import Literal

UnavailableStatus = Literal["suspended", "not_offered"]


@dataclass(frozen=True)
class UnavailableBank:
    bank: str
    reason: str
    status: UnavailableStatus = "suspended"


UNAVAILABLE_BANKS: dict[str, list[UnavailableBank]] = {
    "avtokredit_brend_birlamchi": [
        # SQB'ning "JAC-Avto imkon krediti" (jac-avto-imkon-uz) sahifasining
        # o'zida ham, uni ko'rsatuvchi avtokreditlar ro'yxati kartochkasida
        # ham 2026-08-10 holatiga ko'ra aniq "(Vaqtincha to'xtatilgan)"
        # yozuvi bor — jonli saytdan to'g'ridan-to'g'ri tasdiqlangan.
        UnavailableBank(bank="SQB", reason="Vaqtincha to'xtatilgan", status="suspended"),
    ],
    "istemol_krediti": [
        # AgroBank'ning saytida bu mahsulot uchun sahifa umuman yo'q (vaqtincha
        # to'xtatilgan emas, hech qachon taklif qilinmagan) — shu sabab
        # status="not_offered", jadvalda ko'rsatilmaydi, faqat hujjat uchun.
        UnavailableBank(bank="AgroBank", reason="Mahsulot mavjud emas", status="not_offered"),
    ],
}


def get_unavailable_banks(category: str) -> list[UnavailableBank]:
    return [item for item in UNAVAILABLE_BANKS.get(category, []) if item.status == "suspended"]
