from django.db import models

class Reservation(models.Model):
    # 성별 및 회원 유형 선택지 정의
    GENDER_CHOICES = [('M', '남성'), ('F', '여성')]
    USER_TYPE_CHOICES = [
        ('interior', '인테리어 업체'),
        ('owner', '건축주'),
        ('student', '학생'),
        ('etc', '기타'),
    ]

    # 1. 예약 날짜 및 시간 (예: 2026-08-05 10:15)
    reservation_datetime = models.DateTimeField(verbose_name="예약 날짜 및 시간")
    
    # 2. 고객 기본 정보
    name = models.CharField(max_length=50, verbose_name="이름")
    gender = models.CharField(max_length=2, choices=GENDER_CHOICES, verbose_name="성별")
    phone_number = models.CharField(max_length=20, verbose_name="전화번호")
    
    # 3. 고객 유형
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, verbose_name="고객 유형")
    
    # 4. 취향 선택 카드 결과 나열 (예: "주택, 목재, 높은 층고")
    taste_results = models.TextField(verbose_name="공간 취향 결과")
    
    # 5. 신청 일시 (데이터가 들어오는 실시간 시각 자동 저장)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="신청 일시")

    # 6. 예약 10분 전 안내 문자 발송 여부 (중복 발송 방지용)
    reminder_sent = models.BooleanField(default=False, verbose_name="안내문자 발송완료")

    def __str__(self):
        return f"{self.name} - {self.reservation_datetime.strftime('%m/%d %H:%M')}"