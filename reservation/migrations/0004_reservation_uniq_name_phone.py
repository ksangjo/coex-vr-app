# 이름 + 전화번호 결합 유니크 제약(중복 예약 방지) 추가

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reservation', '0003_reservation_client_status_reservation_company_name_and_more'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='reservation',
            constraint=models.UniqueConstraint(
                fields=('name', 'phone_number'),
                name='uniq_reservation_name_phone',
            ),
        ),
    ]
