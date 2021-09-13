from apscheduler.schedulers.background import BlockingScheduler
from django.core.management.base import BaseCommand
from crat.tasks import update_rates
from crat.settings import config


class Command(BaseCommand):
    help = 'Run blocking scheduler to create periodical tasks'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Preparing scheduler'))
        scheduler = BlockingScheduler()
        scheduler.add_job(update_rates.send, 'interval', seconds=60 * config.rates_update_timeout_minutes)
        self.stdout.write(self.style.NOTICE('Start scheduler'))
        scheduler.start()
