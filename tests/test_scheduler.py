from unittest.mock import MagicMock, patch

from scheduler import build_scheduler


def test_build_scheduler_registers_one_interval_job():
    fake_session_factory = MagicMock()
    scheduler = build_scheduler(fake_session_factory, interval_hours=6)

    jobs = scheduler.get_jobs()
    assert len(jobs) == 1
    assert jobs[0].trigger.interval.total_seconds() == 6 * 3600


def test_scheduled_job_calls_run_all_scrapers_with_session():
    fake_session = MagicMock()
    fake_session_factory = MagicMock()
    fake_session_factory.return_value.__enter__.return_value = fake_session

    scheduler = build_scheduler(fake_session_factory, interval_hours=1)
    job_func = scheduler.get_jobs()[0].func

    with patch("scheduler.run_all_scrapers") as mock_run_all:
        job_func()

    mock_run_all.assert_called_once_with(fake_session)
