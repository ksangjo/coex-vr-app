from django.urls import path
from . import views

urlpatterns = [
    # 대기·시간선택·예약폼·설문·완료 화면을 모두 이 한 경로에서 처리 (SPA)
    path('', views.main_page, name='main_page'),
    # 외부 크론이 호출하는 안내 문자 발송 엔드포인트 (?token=... 필요)
    path('cron/send-reminders/', views.send_reminders_cron, name='send_reminders_cron'),
]
