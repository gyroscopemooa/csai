"""Single-process worker. Run separately or via the optional FastAPI lifespan, not both."""
import time,os,logging
import app
import notifications,channel_live,google_calendar,reporting,push_notifications,domains,message_notifications
from store import DEMO
logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')

def tick_once():
    if os.getenv('ENABLE_AUTO_MESSAGES')=='1':message_notifications.tick()
    if os.getenv('ENABLE_AUTO_DOMAINS')=='1':domains.tick()
    if os.getenv('ENABLE_AUTO_PUSH')=='1':push_notifications.tick()
    if os.getenv('ENABLE_AUTO_REPORTS')=='1':reporting.tick()
    if os.getenv('ENABLE_AUTO_EMAIL')=='1':notifications.tick()
    if os.getenv('ENABLE_AUTO_CALENDAR')=='1':google_calendar.tick()
    if channel_live.enabled():
        for _ in range(10):
            if not channel_live.process_one():break

def loop(stop=None):
    logging.info('Worker started. demo=%s auto_email=%s channels=%s',DEMO,os.getenv('ENABLE_AUTO_EMAIL')=='1',channel_live.enabled())
    while stop is None or not stop.is_set():
        try:tick_once()
        except Exception:logging.exception('Worker iteration failed')
        if stop is None:time.sleep(5)
        else:stop.wait(5)

if __name__=='__main__':loop()
