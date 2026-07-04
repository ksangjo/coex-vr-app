from django.shortcuts import render, redirect
from django.utils import timezone
from .models import Reservation
from datetime import datetime

def main_page(request):
    """1~4단계: 현재 시간 이후의 타임슬롯 목록을 생성하여 화면에 전달"""
    now = timezone.localtime(timezone.now())
    current_time_str = now.strftime("%H:%M")

    # 페어 기간(2026-08-05 ~ 08-08) 안에서 실제 운영 중인지 여부.
    # 이 기간 안에 있을 때에만 "지나간 시간"을 마감 처리한다.
    # (페어 기간 밖에서 테스트할 때는 현재 시각과 무관하게 모든 슬롯이 열려 있어야 함)
    is_fair_now = (now.year == 2026 and now.month == 8 and 5 <= now.day <= 8)
    display_day = now.day if is_fair_now else 5

    # 이미 데이터베이스(DB)에 예약 완료된 시간대 목록 가져오기 (표시 날짜 기준)
    booked_slots = Reservation.objects.filter(
        reservation_datetime__year=2026,
        reservation_datetime__month=8,
        reservation_datetime__day=display_day
    ).values_list('reservation_datetime', flat=True)
    # 비교하기 편하게 'HH:MM' 문자열 리스트로 변환
    booked_times = [timezone.localtime(dt).strftime("%H:%M") for dt in booked_slots]

    # 15분 단위 전체 타임슬롯 리스트 생성 (10:00 시작 ~ 17:45 시작, 마지막 종료 18:00)
    # 각 슬롯은 시작/종료/표시라벨/마감여부를 담은 딕셔너리로 전달한다.
    all_slots = []
    for hour in range(10, 18):
        for minute in [0, 15, 30, 45]:
            start = f"{hour:02d}:{minute:02d}"
            end_total = hour * 60 + minute + 15  # 종료 시간 = 시작 + 15분
            end = f"{end_total // 60:02d}:{end_total % 60:02d}"

            is_booked = start in booked_times
            is_past = is_fair_now and start < current_time_str

            all_slots.append({
                'start': start,
                'label': f"{start}~{end}",
                'disabled': is_booked or is_past,
            })

    # 화면 템플릿으로 시간 데이터 송출
    context = {
        'all_slots': all_slots,
        'display_day': display_day,
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