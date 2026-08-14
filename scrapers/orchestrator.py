import threading
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from db.models import ProductRow, ScrapeRunRow
from scrapers.registry import ALL_SCRAPERS

# fetch_html'ning o'zi har bir HTTP so'rovga 15 soniyalik timeout qo'yadi,
# lekin bitta bank scraperi bir nechta sahifani ketma-ket so'raydi (masalan,
# Ipoteka Bank 7 ta kategoriya sahifasini) va sahifa matnini qayta ishlaydigan
# regex'lar tarmoqdan mustaqil ravishda ham osilib qolishi mumkin. 2026-08-14'da
# jonli Railway muhitida aynan shu sodir bo'ldi: bitta bank scraperi soatdan
# ortiq osilib qolib, run_all_scrapers ketma-ket ishlagani sabab undan keyingi
# HAMMA banklarni abadiy to'xtatib qo'ydi. Shu sabab har bir scraper.run()
# chaqiruvi alohida thread'da SCRAPER_TIMEOUT_SECONDS bilan chegaralanadi: vaqt
# tugasa, o'sha bank "failed" deb belgilanadi va navbat keyingisiga o'tadi —
# Python thread'ni majburan to'xtatib bo'lmagani uchun osilib qolgan thread
# orqa fonda (daemon sifatida) davom etaveradi, lekin u boshqa banklarni
# endi blokламайди.
SCRAPER_TIMEOUT_SECONDS = 90


def _run_scraper_with_timeout(scraper) -> tuple[list | None, Exception | None, bool]:
    """Returns (products, error, timed_out). Exactly one of products/error is
    set unless timed_out is True, in which case both are None."""
    outcome: dict = {}

    def _target():
        try:
            outcome["products"] = scraper.run()
        except Exception as exc:
            outcome["error"] = exc

    thread = threading.Thread(target=_target, daemon=True)
    thread.start()
    thread.join(timeout=SCRAPER_TIMEOUT_SECONDS)

    if thread.is_alive():
        return None, None, True
    return outcome.get("products"), outcome.get("error"), False


def run_all_scrapers(session: Session) -> None:
    for scraper_cls in ALL_SCRAPERS:
        scraper = scraper_cls()
        run = ScrapeRunRow(
            bank=scraper.bank_name,
            started_at=datetime.now(timezone.utc),
            status="running",
        )
        session.add(run)
        session.commit()

        products, error, timed_out = _run_scraper_with_timeout(scraper)

        if timed_out:
            run.status = "failed"
            run.error_message = f"{SCRAPER_TIMEOUT_SECONDS}s ichida javob bermadi (timeout)"
            run.finished_at = datetime.now(timezone.utc)
            session.commit()
            continue

        if error is not None or products is None:
            session.rollback()
            run.status = "failed"
            run.error_message = str(error) if error is not None else "Noma'lum xatolik: mahsulotlar topilmadi"
            run.finished_at = datetime.now(timezone.utc)
            session.commit()
            continue

        try:
            for product in products:
                session.add(
                    ProductRow(
                        bank=product.bank,
                        category=product.category,
                        product_name=product.product_name,
                        rate_min=product.rate_min,
                        rate_max=product.rate_max,
                        term_min_months=product.term_min_months,
                        term_max_months=product.term_max_months,
                        amount_max_som=product.amount_max_som,
                        requires_collateral=product.requires_collateral,
                        down_payment_pct=product.down_payment_pct,
                        source_url=product.source_url,
                        scraped_at=product.scraped_at,
                        grace_period_months=product.grace_period_months,
                        payment_method=product.payment_method,
                        special_terms=product.special_terms,
                    )
                )

            run.status = "success"
            run.products_found = len(products)
            run.finished_at = datetime.now(timezone.utc)
            session.commit()
        except Exception as exc:
            session.rollback()
            run.status = "failed"
            run.error_message = str(exc)
            run.finished_at = datetime.now(timezone.utc)
            session.commit()
            continue
