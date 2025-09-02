"""
Management команда для очищення orphaned RQ jobs.

Orphaned jobs - це RQ задачі які існують в Redis черзі, 
але не мають відповідного запису в LeadPendingTask.

Запуск:
python manage.py cleanup_orphaned_jobs --dry-run  # Показати що буде видалено
python manage.py cleanup_orphaned_jobs           # Видалити orphaned jobs
"""

import logging
from django.core.management.base import BaseCommand
from django_rq import get_queue, get_scheduler
from webhooks.models import LeadPendingTask

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Clean up orphaned RQ jobs that have no corresponding LeadPendingTask records"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )
        parser.add_argument(
            '--queue',
            default='default',
            help='Queue name to check (default: default)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        queue_name = options['queue']
        
        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 DRY RUN MODE - No actual changes will be made"))
        
        self.stdout.write(f"Checking queue: {queue_name}")
        
        try:
            queue = get_queue(queue_name)
            scheduler = get_scheduler(queue_name)
            
            # Отримуємо всі job IDs з черги
            queue_job_ids = set(queue.job_ids)
            scheduled_job_ids = set(scheduler.get_jobs())
            all_rq_job_ids = queue_job_ids | {job.id for job in scheduled_job_ids}
            
            self.stdout.write(f"Found {len(queue_job_ids)} jobs in queue")
            self.stdout.write(f"Found {len(scheduled_job_ids)} jobs in scheduler")
            self.stdout.write(f"Total RQ jobs: {len(all_rq_job_ids)}")
            
            if not all_rq_job_ids:
                self.stdout.write(self.style.SUCCESS("✅ No RQ jobs found - nothing to clean"))
                return
            
            # Отримуємо всі task_ids з LeadPendingTask
            db_task_ids = set(
                LeadPendingTask.objects.values_list('task_id', flat=True)
            )
            self.stdout.write(f"Found {len(db_task_ids)} tasks in database")
            
            # Знаходимо orphaned jobs
            orphaned_job_ids = all_rq_job_ids - db_task_ids
            
            if not orphaned_job_ids:
                self.stdout.write(self.style.SUCCESS("✅ No orphaned jobs found"))
                return
            
            self.stdout.write(
                self.style.WARNING(f"🔍 Found {len(orphaned_job_ids)} orphaned RQ jobs:")
            )
            
            cancelled_count = 0
            error_count = 0
            
            for job_id in orphaned_job_ids:
                try:
                    # Спробуємо отримати деталі job для кращого логування
                    job = queue.fetch_job(job_id)
                    
                    if job:
                        job_func = getattr(job, 'func_name', 'unknown')
                        job_args = getattr(job, 'args', [])
                        job_created = getattr(job, 'created_at', 'unknown')
                        
                        self.stdout.write(
                            f"  📋 Job {job_id[:16]}... - Func: {job_func}, Args: {job_args}, Created: {job_created}"
                        )
                        
                        # Фільтруємо тільки send_follow_up jobs
                        if 'send_follow_up' not in str(job_func):
                            self.stdout.write(f"    ⏭️ Skipping non-follow-up job")
                            continue
                            
                        if not dry_run:
                            job.cancel()
                            cancelled_count += 1
                            self.stdout.write(f"    ✅ Cancelled orphaned job")
                        else:
                            self.stdout.write(f"    🔍 Would cancel this job")
                            
                    else:
                        # Job не знайдено в черзі, можливо в scheduler
                        scheduled_job = None
                        for sched_job in scheduled_job_ids:
                            if sched_job.id == job_id:
                                scheduled_job = sched_job
                                break
                        
                        if scheduled_job:
                            self.stdout.write(
                                f"  📅 Scheduled Job {job_id[:16]}... - Found in scheduler"
                            )
                            
                            if not dry_run:
                                scheduler.cancel(job_id)
                                cancelled_count += 1
                                self.stdout.write(f"    ✅ Cancelled orphaned scheduled job")
                            else:
                                self.stdout.write(f"    🔍 Would cancel this scheduled job")
                        else:
                            self.stdout.write(f"  ❓ Job {job_id[:16]}... - Not found in queue or scheduler")
                        
                except Exception as e:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(f"  ❌ Error processing job {job_id[:16]}...: {e}")
                    )
            
            # Підсумок
            if dry_run:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"🔍 DRY RUN COMPLETE: Found {len(orphaned_job_ids)} orphaned jobs that would be cancelled"
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ CLEANUP COMPLETE: Cancelled {cancelled_count} orphaned jobs"
                    )
                )
                if error_count > 0:
                    self.stdout.write(
                        self.style.WARNING(f"⚠️ {error_count} jobs had errors during cleanup")
                    )
            
            # Логування для моніторингу
            if not dry_run and (cancelled_count > 0 or error_count > 0):
                logger.info(f"[CLEANUP] Orphaned jobs cleanup: cancelled={cancelled_count}, errors={error_count}")
                
        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f"❌ Fatal error during cleanup: {e}")
            )
            logger.error(f"[CLEANUP] Fatal error: {e}")
            logger.exception("Cleanup exception details")
            return
        
        self.stdout.write("🏁 Cleanup command completed")
