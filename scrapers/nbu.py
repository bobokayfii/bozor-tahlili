from scrapers.base import TextSectionScraper


class NBUScraper(TextSectionScraper):
    """NBU (O'zmilliybank) retail kredit kategoriyalari SQB kabi alohida
    sahifalarda joylashgan (nbu.uz/jismoniy-shaxslarga-kreditlar/... — real
    saytda tekshirilgan, Task 6 tadqiqotiga qarang).

    MUHIM: NBU saytida hozircha faqat 6 ta retail kredit mahsuloti bor:
    Ipoteka, Avtokredit, Mikroqarz, Ta'lim krediti, Overdraft, National Green.
    Alohida "kredit karta" yoki "iste'mol krediti" sahifasi topilmadi (eski
    /uz/physical/credits/iste-mol-krediti/ manzili 404 qaytardi — sayt qayta
    qurilgan ko'rinadi). Shu sababli quyidagi ikkita kategoriya uchun
    taxminiy (best-guess) manzillar ishlatilgan:
      - kredit_karta -> Overdraft sahifasi eng yaqin analog sifatida
        ishlatilgan (aylanma shaxsiy kredit liniyasi, karta orqali emas,
        lekin funksional jihatdan eng o'xshashi). BU TAXMIN, tasdiqlanmagan.
      - istemol_krediti -> mos joriy sahifa topilmadi; boshqa kategoriyalar
        bilan bir xil URL naqshiga (/jismoniy-shaxslarga-kreditlar/<slug>)
        asoslangan taxminiy manzil ishlatilgan va u HOZIRDA 404 qaytaradi.
    Ushbu ikkala holat ham topshiriq hisobotida aniq bayon qilingan."""

    bank_name = "NBU"
    url = "https://nbu.uz/jismoniy-shaxslarga-kreditlar"
    CATEGORY_URLS = {
        # Tasdiqlangan (real, ishlaydi):
        "avtokredit": "https://nbu.uz/jismoniy-shaxslarga-kreditlar/avtokreditlar",
        "mikroqarz": "https://nbu.uz/jismoniy-shaxslarga-kreditlar/mikroqarzlar",
        # Taxminiy (best-guess) — quyidagi sinf docstringiga qarang:
        "kredit_karta": "https://nbu.uz/jismoniy-shaxslarga-kreditlar/overdraft",
        "istemol_krediti": "https://nbu.uz/jismoniy-shaxslarga-kreditlar/istemol-krediti",
    }
