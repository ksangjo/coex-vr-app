from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # 1. 관리자 페이지 주소 (기본값인 'admin/' 그대로 사용합니다)
    path('admin/', admin.site.urls), 
    
    # 2. 내 예약 앱 주소 연결
    path('', include('reservation.urls')), 
]