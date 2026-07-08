from django.shortcuts import render
from django.utils import timezone
from django.conf import settings
from django.db import IntegrityError, transaction
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from .models import Reservation
from .reminders import send_due_reminders
from datetime import datetime


# 페어 운영 기간(2026-08-05 ~ 08-08). 이 기간 안에서만 "지나간 시간" 슬롯을 마감한다.
def _is_fair_now(now):
    return now.year == 2026 and now.month == 8 and 5 <= now.day <= 8


@never_cache
def main_page(request):
    """
    대기 → 시간선택 → 예약자정보 → 설문(3단계) → 완료까지 모든 화면을 한 URL('/')에서
    처리하는 SPA(단일 페이지) 진입점.

    - GET  : 타임슬롯을 계산해 페이지를 렌더링한다.
    - POST : action 값에 따라 아래 3가지 비동기 작업을 처리한다.
        * create_reservation : '확인 및 다음' 시점에 예약 레코드 생성 (취향은 빈 값)
        * save_survey        : Survey 3단계 카드 클릭 순간 취향 결과를 update
        * reset              : '홈으로 돌아가기' 시 세션의 이전 유저 흔적 제거

    @never_cache 로 브라우저 뒤로가기(bfcache) 시 이전 유저 화면이 되살아나지 않게 막는다.
    """
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create_reservation':
            return _create_reservation(request)
        if action == 'save_survey':
            return _save_survey(request)
        if action == 'reset':
            # 이전 유저와 예약 레코드를 잇던 연결 고리만 제거 (관리자 로그인 등은 보존)
            request.session.pop('reservation_id', None)
            return JsonResponse({'ok': True})
        return JsonResponse({'ok': False, 'error': '알 수 없는 요청입니다.'}, status=400)

    # ---- GET: 타임슬롯 계산 후 렌더링 ----
    now = timezone.localtime(timezone.now())
    current_time_str = now.strftime("%H:%M")

    is_fair_now = _is_fair_now(now)
    display_day = now.day if is_fair_now else 5

    # 이미 예약 완료된 시간대(표시 날짜 기준)를 'HH:MM' 문자열로 확보
    booked_slots = Reservation.objects.filter(
        reservation_datetime__year=2026,
        reservation_datetime__month=8,
        reservation_datetime__day=display_day,
    ).values_list('reservation_datetime', flat=True)
    booked_times = [timezone.localtime(dt).strftime("%H:%M") for dt in booked_slots]

    # 15분 단위 전체 슬롯(10:00 시작 ~ 17:45 시작). 예약됨/지나감이면 마감 처리.
    all_slots = []
    for hour in range(10, 18):
        for minute in [0, 15, 30, 45]:
            start = f"{hour:02d}:{minute:02d}"
            end_total = hour * 60 + minute + 15
            end = f"{end_total // 60:02d}:{end_total % 60:02d}"

            is_booked = start in booked_times
            is_past = is_fair_now and start < current_time_str

            all_slots.append({
                'start': start,
                'label': f"{start}~{end}",
                'disabled': is_booked or is_past,
            })

    context = {
        'all_slots': all_slots,
        'display_day': display_day,
    }
    return render(request, 'reservation/main_page.html', context)


def _create_reservation(request):
    """'확인 및 다음' 시점: 예약 레코드를 생성하고 세션에 id를 담는다.
    이름+전화번호가 이미 존재하면 IntegrityError 를 잡아 안내 문구로 돌려준다."""
    time_str = request.POST.get('reservation_time')
    name = (request.POST.get('name') or '').strip()
    gender = request.POST.get('gender')
    phone_number = (request.POST.get('phone_number') or '').strip()
    user_type = request.POST.get('user_type')

    company_name = (request.POST.get('company_name') or '').strip()
    client_status = (request.POST.get('client_status') or '').strip()
    other_reason = (request.POST.get('other_reason') or '').strip()

    # 서버측 최소 검증 (프론트 검증이 뚫려도 잘못된 데이터가 저장되지 않도록)
    if not (time_str and name and gender and phone_number and user_type):
        return JsonResponse({'ok': False, 'error': '입력 정보가 올바르지 않습니다.'}, status=400)

    now = timezone.localtime(timezone.now())
    current_day = now.day if _is_fair_now(now) else 5
    full_datetime_str = f"2026-08-{current_day:02d} {time_str}"
    try:
        naive = datetime.strptime(full_datetime_str, "%Y-%m-%d %H:%M")
    except ValueError:
        return JsonResponse({'ok': False, 'error': '시간 정보가 올바르지 않습니다.'}, status=400)
    # USE_TZ=True 환경이므로 Asia/Seoul 기준 aware datetime 으로 저장 (안내문자 발송 시각 정확도 확보)
    res_datetime = timezone.make_aware(naive)

    try:
        # atomic 세이브포인트로 감싸 IntegrityError 발생 시에도 트랜잭션이 깨지지 않게 함
        with transaction.atomic():
            reservation = Reservation.objects.create(
                reservation_datetime=res_datetime,
                name=name,
                gender=gender,
                phone_number=phone_number,
                user_type=user_type,
                company_name=company_name if user_type == 'interior' else None,
                client_status=client_status if user_type == 'owner' else None,
                other_reason=other_reason if user_type == 'etc' else None,
                taste_results='',
            )
    except IntegrityError:
        # 이름+전화번호 유니크 제약 위반 → 에러를 던지지 않고 안내로 전환
        return JsonResponse({'ok': False, 'error': '이미 예약된 정보입니다.'})

    request.session['reservation_id'] = reservation.id
    return JsonResponse({'ok': True})


def _save_survey(request):
    """Survey 3단계(마지막 카드) 클릭 순간: 취향 결과를 기존 예약 레코드에 update."""
    reservation_id = request.session.get('reservation_id')
    taste_results = (request.POST.get('taste_results') or '').strip()

    if not reservation_id:
        return JsonResponse({'ok': False, 'error': '예약 세션이 만료되었습니다.'}, status=400)

    updated = Reservation.objects.filter(id=reservation_id).update(taste_results=taste_results)
    if not updated:
        return JsonResponse({'ok': False, 'error': '예약을 찾을 수 없습니다.'}, status=404)
    return JsonResponse({'ok': True})


@csrf_exempt
def send_reminders_cron(request):
    """
    외부 크론(cron-job.org 등)이 주기적으로 호출하는 안내 문자 발송 엔드포인트.

    Render 무료 플랜은 트래픽이 없으면 슬립되어 내부 스케줄러가 멈추므로,
    외부에서 이 주소를 1분마다 호출해 (1) 앱을 깨우고 (2) 발송을 실행한다.
    ?token=... 값이 settings.CRON_SECRET_TOKEN 과 일치할 때만 동작한다.
    """
    token = request.GET.get('token', '')
    if not settings.CRON_SECRET_TOKEN or token != settings.CRON_SECRET_TOKEN:
        return HttpResponseForbidden('invalid token')

    sent = send_due_reminders()
    return JsonResponse({'ok': True, 'sent': sent})
