"""
문자(SMS) 발송 전용 모듈.

국내 문자 서비스 중 '알리고(Aligo)'는 별도 SDK 없이 requests(HTTP)만으로
연동되어 비전공자가 가장 따라 하기 쉬워서 이걸 기본으로 구현했습니다.
(CoolSMS를 쓰고 싶으면 send_sms() 내부만 교체하면 되며, 나머지 코드는 그대로 재사용됩니다.)

발신번호(sender)는 알리고에 사전 등록·승인된 '내 번호'로 고정됩니다.
API 키 등 민감정보는 코드에 직접 쓰지 않고 settings(=환경변수)에서 읽어옵니다.
"""
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

ALIGO_SEND_URL = "https://apis.aligo.in/send/"


def send_sms(to_number, message):
    """
    한 명에게 문자 1건을 발송한다.

    :param to_number: 받는 사람 전화번호 (예: '010-1234-5678' 또는 '01012345678')
    :param message:   보낼 문자 내용
    :return: (성공여부: bool, 응답데이터: dict)
    """
    # 알리고는 하이픈(-)이 있어도 되지만, 안전하게 숫자만 남긴다.
    receiver = to_number.replace("-", "").strip()

    payload = {
        "key": settings.ALIGO_API_KEY,      # 알리고에서 발급받은 API Key
        "user_id": settings.ALIGO_USER_ID,  # 알리고 로그인 아이디
        "sender": settings.ALIGO_SENDER,    # 사전 등록한 발신번호(내 번호)
        "receiver": receiver,               # 받는 사람
        "msg": message,                     # 내용
        "msg_type": "SMS",                  # 90byte 이하 단문. 길면 'LMS'
    }

    # 테스트 모드: 실제 발송·과금 없이 성공 응답만 돌려준다(문구/연동 점검용).
    if getattr(settings, "ALIGO_TEST_MODE", False):
        payload["testmode_yn"] = "Y"

    try:
        resp = requests.post(ALIGO_SEND_URL, data=payload, timeout=10)
        result = resp.json()
    except Exception as e:
        logger.error("SMS 발송 요청 실패: %s", e)
        return False, {"error": str(e)}

    # 알리고 응답: result_code 가 1(또는 '1')이면 성공, 그 외는 실패.
    success = str(result.get("result_code")) == "1"
    if success:
        logger.info("SMS 발송 성공 -> %s", receiver)
    else:
        logger.error("SMS 발송 실패 -> %s / 응답: %s", receiver, result)
    return success, result
