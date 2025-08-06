# Compatibility helpers -----------------------------------------------------

from datetime import timedelta
from types import SimpleNamespace
from django_rq import get_scheduler


def _apply(func, args=None, kwargs=None):
    args = args or []
    kwargs = kwargs or {}
    task_id = str(uuid.uuid4())
    start = timezone.now()
    CeleryTaskLog.objects.create(
        task_id=task_id,
        name=func.__name__,
        args=list(args),
        kwargs=kwargs,
        eta=start,
        started_at=start,
        status="STARTED",
        business_id=kwargs.get("business_id"),
    )
    try:
        result = func(*args, **kwargs)
    except Exception as exc:
        CeleryTaskLog.objects.filter(task_id=task_id).update(
            finished_at=timezone.now(),
            status="FAILURE",
            result=str(exc),
            traceback=traceback.format_exc(),
        )
        raise
    else:
        CeleryTaskLog.objects.filter(task_id=task_id).update(
            finished_at=timezone.now(),
            status="SUCCESS",
            result="" if result is None else str(result),
        )
        return result


def _apply_async(func, args=None, kwargs=None, countdown=0, headers=None):
    args = args or []
    kwargs = kwargs or {}
    if headers and "business_id" in headers:
        kwargs.setdefault("business_id", headers["business_id"])
    eta = timezone.now() + timedelta(seconds=countdown)
    task_id = str(uuid.uuid4())
    if countdown:
        scheduler = get_scheduler("default")
        job = scheduler.enqueue_in(
            timedelta(seconds=countdown), func, *args, job_id=task_id, **kwargs
        )
    else:
        job = func.delay(*args, job_id=task_id, **kwargs)
    CeleryTaskLog.objects.create(
        task_id=task_id,
        name=func.__name__,
        args=list(args),
        kwargs=kwargs,
        eta=eta,
        status="SCHEDULED",
        business_id=kwargs.get("business_id"),
    )
    return SimpleNamespace(id=task_id)


# Fix the job setup
for _f in (send_follow_up, refresh_expiring_tokens, cleanup_celery_logs):
    _f.apply = lambda args=None, kwargs=None, f=_f: _apply(f, args, kwargs)
    _f.apply_async = lambda args=None, kwargs=None, countdown=0, headers=None, f=_f: _apply_async(f, args, kwargs, countdown, headers)