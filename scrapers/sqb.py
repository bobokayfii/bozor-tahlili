from scrapers.base import TextSectionScraper


class SQBScraper(TextSectionScraper):
    """SQB retail kredit kategoriyalari bitta sahifada emas, balki har biri
    o'zining alohida mahsulot sahifasida joylashgan (real saytda tekshirilgan
    — Task 5 hisobotidagi tadqiqotga qarang). Shuning uchun CATEGORY_URLS
    ishlatiladi: har bir kategoriya o'z URL'idan alohida fetch qilinadi va
    butun sahifa matni bo'lim sifatida ishlatiladi (CATEGORY_HEADINGS kerak
    emas, chunki har bir sahifa allaqachon bitta mahsulotga bag'ishlangan)."""

    bank_name = "SQB"
    url = "https://sqb.uz/uz/individuals/credits/"
    CATEGORY_URLS = {
        "avtokredit": "https://sqb.uz/uz/individuals/autoloans/avtokredit-imkon-uz/",
        "mikroqarz": "https://sqb.uz/uz/individuals/credits/mikrokredit-uz/",
        "kredit_karta": "https://sqb.uz/uz/individuals/credits/credit-card-new-uz/",
        "istemol_krediti": "https://sqb.uz/uz/individuals/credits/consumer-credit-new-uz/",
    }
    # consumer-credit-new-uz sahifasida "Foiz stavkasi:" jadvalidan tashqarida
    # ham boshqa % belgilar bor (masalan, "Qarz yuki ko'rsatkichi 50% dan
    # oshmasligi" talabi va ipoteka mahsulotiga cross-sell banneri "yillik
    # 17%"). CATEGORY_HEADINGS bo'lmasa butun sahifa matni bitta bo'lim
    # sifatida olinadi va shu begona foizlar rate_min/rate_max'ni buzadi.
    # Shuning uchun bu yerda faqat haqiqiy stavka jadvali bilan chegaralanadi.
    CATEGORY_HEADINGS = {
        "istemol_krediti": ("Kredit miqdori:", "Imtiyozli davr"),
    }
