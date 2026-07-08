from __future__ import annotations

from apscheduler.schedulers.blocking import BlockingScheduler

from db.database import get_engine, get_session_factory, init_db
from scrapers.orchestrator import run_all_scrapers


def build_scheduler(session_factory, interval_hours: int = 24) -> BlockingScheduler:
    scheduler = BlockingScheduler()

    def job() -> None:
        with session_factory() as session:
            run_all_scrapers(session)

    scheduler.add_job(job, "interval", hours=interval_hours)
    return scheduler


if __name__ == "__main__":
    engine = get_engine()
    init_db(engine)
    factory = get_session_factory(engine)
    build_scheduler(factory, interval_hours=24).start()
