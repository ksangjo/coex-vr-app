from django.shortcuts import render, redirect
from django.utils import timezone
from .models import Reservation
from datetime import datetime

def main_page(request):
    """1~4단계: 현재 시간 이후의 타임슬롯 목록을 생성하여 화면에 전달"""
    # 15분 단위 전체 타임슬롯 리스트 생성 (10:00 ~ 17:45 시작 타임 기준)
    all_slots = []
    for hour in range(10, 18):
        for minute in [0, 15, 30, 45]:
            if hour == 17 and minute > 45: 
                continue
            all_slots.append(f"{hour:02d}:{minute:02d}")

    # 현재 실제 한국 시간 확인 (페어 기간인 8월 5일~8일 상황을 시뮬레이션)
    # 실제 현장 운영을 위해 현재 시, 분을 추출합니다.
    now = timezone.localtime(timezone.now())
    current_time_str = now.strftime("%H:%M")

    # 이미 데이터베이스(DB)에 예약 완료된 시간대 목록 가져오기 (오늘 날짜 기준)
    booked_slots = Reservation.objects.filter(
        reservation_datetime__year=2026,
        reservation_datetime__month=8,
        reservation_datetime__day=now.day if now.month == 8 else 5
    ).values_list('reservation_datetime', flat=True)
    
    # 비교하기 편하게 'HH:MM' 문자열 리스트로 변환
    booked_times = [dt.strftime("%H:%M") for dt in booked_slots]

    # 화면 템플릿으로 시간 데이터 송출
    context = {
        'all_slots': all_slots,
        'current_time': current_time_str,
        'booked_times': booked_times,
        # 실시간 날짜 확인용 (페어 기간 외에는 기본 8/5 타겟팅)
        'display_day': now.day if now.month == 8 and 5 <= now.day <= 8 else 5
    }
    return render(request, 'reservation/main.html', context)

def survey_page(request):
    """5단계: 예약 정보를 임시 저장(세션)하고 취향 선택 밸런스 게임 페이지를 보여줌"""
    if request.method == 'POST':
        time_str = request.POST.get('reservation_time')
        name = request.POST.get('name')
        gender = request.POST.get('gender')
        phone_number = request.POST.get('phone_number')
        user_type = request.POST.get('user_type')

        now = timezone.now()
        current_day = now.day if now.month == 8 and 5 <= now.day <= 8 else 5
        full_datetime_str = f"2026-08-{current_day:02d} {time_str}"

        request.session['temp_reservation'] = {
            'reservation_datetime': full_datetime_str,
            'name': name,
            'gender': gender,
            'phone_number': phone_number,
            'user_type': user_type,
        }
        return render(request, 'reservation/survey.html')
    return redirect('main_page')

def submit_taste(request):
    """최종 저장 후 리다이렉트 에러 해결을 위해 명확하게 메인으로 이동시킴"""
    if request.method == 'POST':
        taste_results = request.POST.get('taste_results')
        temp_data = request.session.get('temp_reservation')

        if temp_data:
            res_datetime = datetime.strptime(temp_data['reservation_datetime'], "%Y-%m-%d %H:%M")
            
            # DB에 정상 인서트
            Reservation.objects.create(
                reservation_datetime=res_datetime,
                name=temp_data['name'],
                gender=temp_data['gender'],
                phone_number=temp_data['phone_number'],
                user_type=temp_data['user_type'],
                taste_results=taste_results
            )
            del request.session['temp_reservation']
            
    # redirect 할 때 url 패턴명('main_page')을 정확히 선언하여 오류 원천 차단
    return redirect('main_page')