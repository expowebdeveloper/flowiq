from apscheduler.schedulers.background import BackgroundScheduler

from loan_recommendation.bank_sync.services import sync_banks


scheduler = BackgroundScheduler()


def start_scheduler():

    scheduler.add_job(

        sync_banks,

        trigger="interval",

        hours=24,

        id="bank_sync",

        replace_existing=True

    )

    scheduler.start()

    print("✅ Bank Scheduler Started")