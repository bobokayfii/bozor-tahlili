from datetime import datetime, timezone

from sqlalchemy.orm import Session

from db.models import ProductRow, ScrapeRunRow
from scrapers.registry import ALL_SCRAPERS


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

        try:
            products = scraper.run()

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
