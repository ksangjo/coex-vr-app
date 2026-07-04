"""
APScheduler 설정.

웹 프로세스(gunicorn) 안에서 백그라운드 스레드로 1분마다
reminders.send_due_reminders() 를 실행한다.

가볍고(추가 DB 테이블 불필요) Render 무료 웹 서비스에서도 동작하지만,
무료 플랜은 트래픽이 없으면 15분 뒤 슬립(spin down)되어 스케줄러도 멈춥니다.
이 한계와 해결책은 아래 안내(설명)와 views.py의 크론 엔드포인트를 참고하세요.
"""
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from .reminders import send_due_reminders

logger = logging.getLogger(__name__)

# 스케줄러가 두 번 시작되는 것을 막기 위한 모듈 단위 플래그
_scheduler = None


def start():
    """스케줄러를 시작한다. (이미 실행 중이면 무시)"""
    global _scheduler
    if _scheduler is not None:
        return

    scheduler = BackgroundScheduler(timezone="Asia/Seoul")
    # 1분마다 실행. max_instances=1, coalesce=True 로 겹침/밀린 실행을 방지.
    scheduler.add_job(
        send_due_reminders,
        trigger="interval",
        minutes=1,
        id="send_due_reminders",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    _scheduler = scheduler
    logger.info("예약 안내 문자 스케줄러 시작됨 (1분 간격)")
