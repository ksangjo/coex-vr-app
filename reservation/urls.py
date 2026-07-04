from django.urls import path
from . import views

urlpatterns = [
    path('', views.main_page, name='main_page'),
    path('survey/', views.survey_page, name='survey_page'),
    path('submit-taste/', views.submit_taste, name='submit_taste'),
    # 외부 크론이 호출하는 안내 문자 발송 엔드포인트 (?token=... 필요)
    path('cron/send-reminders/', views.send_reminders_cron, name='send_reminders_cron'),
]