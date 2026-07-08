"""
문자(SMS) 발송 전용 모듈 — SOLAPI 연동.

회사에서 사용하는 SOLAPI(https://solapi.com) REST API로 문자 1건을 발송한다.
별도 SDK 없이 표준 라이브러리(hmac/hashlib/secrets)와 requests 만으로 구현했다.

인증: API Key 기반 HMAC-SHA256 서명 방식.
  - 서명 대상 문자열 = date(ISO8601) + salt
  - signature = HMAC_SHA256(API_SECRET, date + salt) 의 hex 문자열
  - Authorization 헤더:
      HMAC-SHA256 apiKey=..., date=..., salt=..., signature=...

발신번호(SOLAPI_SENDER)는 SOLAPI 콘솔에 사전 등록·승인된 번호여야 한다.
민감정보(API Key/Secret)는 코드에 직접 쓰지 않고 settings(=환경변수)에서 읽어온다.
"""
import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timezone

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# 단일 메시지 발송 엔드포인트. 고정(static) IP가 필요하면
# https://api-static.solapi.com 도메인으로 교체하면 된다.
SOLAPI_SEND_URL = "https://api.solapi.com/messages/v4/send"


def _auth_headers():
    """SOLAPI API Key 기반 HMAC-SHA256 인증 헤더를 생성한다."""
    # ISO8601(UTC). SOLAPI는 서버 시각과 15분 이내 차이만 허용한다.
    date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    salt = secrets.token_hex(16)  # 매 요청 무작위 솔트(12~64자)
    signature = hmac.new(
        settings.SOLAPI_API_SECRET.encode(),
        (date + salt).encode(),
        hashlib.sha256,
    ).hexdigest()
    authorization = (
        f"HMAC-SHA256 apiKey={settings.SOLAPI_API_KEY}, "
        f"date={date}, salt={salt}, signature={signature}"
    )
    return {
        "Authorization": authorization,
        "Content-Type": "application/json",
    }


def send_sms(to_number, message):
    """
    한 명에게 문자 1건을 발송한다.

    :param to_number: 받는 사람 전화번호 (예: '010-1234-5678' 또는 '01012345678')
    :param message:   보낼 문자 내용
    :return: (성공여부: bool, 응답데이터: dict)
    """
    # SOLAPI는 숫자만 받는다. 하이픈 등 제거.
    receiver = to_number.replace("-", "").strip()
    sender = settings.SOLAPI_SENDER.replace("-", "").strip()

    # 테스트 모드: 실제 발송·과금 없이 흐름만 점검(API 호출을 아예 하지 않음).
    if getattr(settings, "SOLAPI_TEST_MODE", False):
        logger.info("[SOLAPI 테스트모드] 실제 발송 생략 -> %s / 내용: %s", receiver, message)
        return True, {"testmode": True, "to": receiver, "text": message}

    # type(SMS/LMS)을 지정하지 않으면 SOLAPI가 글자 수에 따라 자동 판별한다.
    # (안내 문자는 90바이트를 넘어 LMS로 나갈 수 있으므로 자동 판별에 맡긴다.)
    payload = {
        "message": {
            "to": receiver,
            "from": sender,
            "text": message,
        }
    }

    try:
        resp = requests.post(
            SOLAPI_SEND_URL,
            json=payload,
            headers=_auth_headers(),
            timeout=10,
        )
        result = resp.json()
    except Exception as e:
        logger.error("SMS 발송 요청 실패: %s", e)
        return False, {"error": str(e)}

    # SOLAPI 응답: statusCode 가 '2000'(정상 접수)이면 성공.
    # 실패 시에는 errorCode/errorMessage 가 담겨 온다.
    success = str(result.get("statusCode")) == "2000"
    if success:
        logger.info("SMS 발송 성공 -> %s", receiver)
    else:
        logger.error("SMS 발송 실패 -> %s / 응답: %s", receiver, result)
    return success, result
