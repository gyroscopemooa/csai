"""Run separately: python worker.py. No live email by default, even with keys."""
import time,os,logging
import app
import notifications,channel_live,google_calendar
from store import DEMO
logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
if __name__=='__main__':
    logging.info('Worker started. demo=%s auto_email=%s channels=%s',DEMO,os.getenv('ENABLE_AUTO_EMAIL')=='1',channel_live.enabled())
    while True:
        try:
            if os.getenv('ENABLE_AUTO_EMAIL')=='1':notifications.tick()
            if os.getenv('ENABLE_AUTO_CALENDAR')=='1':google_calendar.tick()
            if channel_live.enabled():
                for _ in range(10):
                    if not channel_live.process_one():break
        except Exception:logging.exception('Worker iteration failed')
        time.sleep(5)
