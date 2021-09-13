from apscheduler.schedulers.background import BlockingScheduler
from django.core.management.base import BaseCommand
from crat.tasks import update_rates


class Command(BaseCommand):
    help = 'Run blocking scheduler to create periodical tasks'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Preparing scheduler'))
        scheduler = BlockingScheduler()
        scheduler.add_job(update_rates.send, 'interval', seconds=60 * 10)
        self.stdout.write(self.style.NOTICE('Start scheduler'))
        scheduler.start()
