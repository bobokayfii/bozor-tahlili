"""Ba'zi banklar ma'lum bir toifada aniq mahsulotga ega emas (masalan, TBC
Bank hozircha "Avtokredit (birlamchi bozor)" mahsulotini taklif qilmaydi).
Bunday holatlar Product/ProductRow sxemasi orqali emas (u har doim aniq
stavka/muddat/summa talab qiladi), balki shu alohida, engil ro'yxat orqali
frontendga "mahsulot mavjud emas" sifatida ko'rsatiladi — reyting/saralash
mantig'iga (masalan, eng past stavkani hisoblash) aralashmaydi."""

from dataclasses import dataclass


@dataclass(frozen=True)
class UnavailableBank:
    bank: str
    reason: str


UNAVAILABLE_BANKS: dict[str, list[UnavailableBank]] = {
    "avtokredit": [
        UnavailableBank(bank="TBC Bank", reason="Mahsulot mavjud emas"),
    ],
    "avtokredit_ikkilamchi": [
        UnavailableBank(bank="SQB", reason="Vaqtincha to'xtatilgan"),
    ],
    "avtokredit_brend_birlamchi": [
        UnavailableBank(bank="Kapitalbank", reason="Vaqtincha to'xtatilgan"),
        UnavailableBank(bank="SQB", reason="Vaqtincha to'xtatilgan"),
    ],
    "istemol_krediti": [
        UnavailableBank(bank="NBU", reason="Vaqtincha to'xtatilgan"),
        UnavailableBank(bank="AgroBank", reason="Mahsulot mavjud emas"),
    ],
}


def get_unavailable_banks(category: str) -> list[UnavailableBank]:
    return UNAVAILABLE_BANKS.get(category, [])
