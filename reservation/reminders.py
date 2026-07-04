"""
'예약 10분 전' 안내 문자를 보내는 핵심 로직.

이 함수(send_due_reminders)는 두 곳에서 공용으로 호출됩니다.
  1) scheduler.py 의 APScheduler 작업(1분마다 자동 실행)
  2) (선택) views.py 의 외부 크론 엔드포인트

DB만 보고 판단하므로, 어디서 호출하든 결과는 동일하고 중복 발송되지 않습니다.
"""
import logging
from datetime import timedelta

from django.db import close_old_connections
from django.utils import timezone

from .models import Reservation
from .sms import send_sms

logger = logging.getLogger(__name__)

# 예약 시간 몇 분 전에 보낼지 (요구사항: 10분 전)
REMINDER_MINUTES_BEFORE = 10


def build_message(reservation):
    """실제로 발송할 문자 문구를 만든다. (원하는 대로 자유롭게 수정하세요)"""
    start = timezone.localtime(reservation.reservation_datetime).strftime("%H:%M")
    return (
        f"[igloo-vr] {reservation.name}님, 예약하신 VR 체험이 "
        f"약 {REMINDER_MINUTES_BEFORE}분 뒤 {start}에 시작됩니다. "
        f"부스로 와주세요!"
    )


def send_due_reminders():
    """
    지금 시점에서 '10분 전 안내'를 보내야 하는 예약을 찾아 문자를 발송한다.

    - reminder_sent=False (아직 안 보낸 것)
    - 예약 시간이 '지금 ~ 10분 뒤' 사이 (즉 10분 앞으로 다가온 것)
    - 이미 지난 예약은 제외
    를 대상으로 하며, 발송에 성공하면 reminder_sent=True 로 표시해 중복을 막는다.
    """
    close_old_connections()  # 백그라운드 스레드의 오래된 DB 연결 정리

    now = timezone.now()
    threshold = now + timedelta(minutes=REMINDER_MINUTES_BEFORE)

    targets = Reservation.objects.filter(
        reminder_sent=False,
        reservation_datetime__gt=now,        # 아직 시작 안 한 예약
        reservation_datetime__lte=threshold,  # 10분 이내로 다가온 예약
    )

    sent_count = 0
    for reservation in targets:
        if not reservation.phone_number:
            continue
        success, _ = send_sms(reservation.phone_number, build_message(reservation))
        if success:
            reservation.reminder_sent = True
            reservation.save(update_fields=["reminder_sent"])
            sent_count += 1

    if sent_count:
        logger.info("예약 10분 전 안내 문자 %d건 발송 완료", sent_count)
    return sent_count
