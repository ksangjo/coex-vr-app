import os
import sys

from django.apps import AppConfig


class ReservationConfig(AppConfig):
    name = 'reservation'

    def ready(self):
        """
        Django가 앱을 로드할 때 호출됨. 여기서 스케줄러를 켠다.
        단, 아래 경우에는 켜지 않는다.
          - migrate / collectstatic 등 배포·관리 명령 실행 중 (불필요 + 오류 방지)
          - runserver 자동 리로더의 '부모' 프로세스 (중복 실행 방지)
        """
        from django.conf import settings

        if not getattr(settings, "SCHEDULER_AUTOSTART", False):
            return

        # 관리 명령으로 실행된 경우에는 스케줄러를 켜지 않는다.
        management_commands = {
            "migrate", "makemigrations", "collectstatic",
            "shell", "createsuperuser", "test",
        }
        if any(cmd in sys.argv for cmd in management_commands):
            return

        # runserver는 코드 변경 감지를 위해 프로세스를 2개 띄운다.
        # 실제 작업 프로세스(RUN_MAIN=true)에서만 스케줄러를 켜 중복을 막는다.
        if "runserver" in sys.argv and os.environ.get("RUN_MAIN") != "true":
            return

        from . import scheduler
        scheduler.start()
