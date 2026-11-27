"""Single-process worker. Run separately or via the optional FastAPI lifespan, not both."""
import time,os,logging
import app
import notifications,channel_live,google_calendar,reporting,push_notifications,domains,message_notifications,workflow_controls,smartstore_sync,coupang_catalog,order_sync
from store import DEMO
logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')

def tick_once():
    # Independent integrations must not starve the rest of the worker when one fails.
    jobs=[
        ('ENABLE_SMARTSTORE_SYNC',smartstore_sync.tick),
        ('ENABLE_SMARTSTORE_ORDER_SYNC',order_sync.tick),
        ('ENABLE_COUPANG_CATALOG',coupang_catalog.tick),
        ('ENABLE_AUTO_WORKFLOW_REMINDERS',workflow_controls.tick_reminders),
        ('ENABLE_AUTO_MESSAGES',message_notifications.tick),
        ('ENABLE_AUTO_DOMAINS',domains.tick),
        ('ENABLE_AUTO_PUSH',push_notifications.tick),
        ('ENABLE_AUTO_REPORTS',reporting.tick),
        ('ENABLE_AUTO_EMAIL',notifications.tick),
        ('ENABLE_AUTO_CALENDAR',google_calendar.tick),
    ]
    for flag,job in jobs:
        if os.getenv(flag)!='1':continue
        try:job()
        except Exception as exc:logging.error('%s failed: %s',flag,type(exc).__name__)
    if channel_live.enabled():
        try:
            for _ in range(10):
                if not channel_live.process_staff_one():break
            for _ in range(10):
                if not channel_live.process_one():break
        except Exception as exc:logging.error('Channel processing failed: %s',type(exc).__name__)

def loop(stop=None):
    logging.info('Worker started. demo=%s auto_email=%s channels=%s',DEMO,os.getenv('ENABLE_AUTO_EMAIL')=='1',channel_live.enabled())
    while stop is None or not stop.is_set():
        try:tick_once()
        except Exception:logging.exception('Worker iteration failed')
        if stop is None:time.sleep(5)
        else:stop.wait(5)

if __name__=='__main__':loop()
