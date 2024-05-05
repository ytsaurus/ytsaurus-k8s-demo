try:
    from k8s_deployer.main import (  # NOQA
        create_function,
        db_watcher_function,
        remove_function,
        send_monitoring_metrics,
    )
except Exception:
    pass

try:
    from registration_backend.index import register, timeslots  # NOQA
except Exception:
    pass
