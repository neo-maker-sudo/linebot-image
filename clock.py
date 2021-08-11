from apscheduler.schedulers.blocking import BlockingScheduler
import requests

sched = BlockingScheduler()


@sched.scheduled_job('interval', id="keepruning_jobs", minutes=20)
def keepruning():
    url = "https://neo-linebot-image.herokuapp.com/"
    r = requests.get(url)


sched.start()
