import aiohttp
import json
import logging
import datetime

# Konfigurasi logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

POSITION_API_URL = "https://www.binance.com/bapi/futures/v2/private/future/leaderboard/getOtherPosition"
BASE_INFO_API_URL = "https://www.binance.com/bapi/futures/v2/public/future/leaderboard/getOtherLeaderboardBaseInfo"
MARK_PRICE_API_URL = "https://fapi.binance.com/fapi/v1/premiumIndex"

def _safe_float(value, default=0.0) -> float:
    """Konversi aman ke float dengan nilai default jika gagal."""
    logger.debug(f"Konversi nilai ke float: {value}")
    try:
        result = float(value or default) if value is not None else default
        logger.debug(f"Hasil konversi: {result}")
        return result
    except (ValueError, TypeError) as e:
        logger.warning(f"Gagal mengonversi {value} ke float: {e}")
        return default

async def get_other_position(session: aiohttp.ClientSession, encrypted_uid: str) -> dict | str:
    """Mendapatkan posisi trading dari Binance Futures Leaderboard secara asinkronus."""
    payload = {
        "encryptedUid": encrypted_uid,
        "tradeType": "PERPETUAL"
    }
    logger.debug(f"Payload untuk get_other_position: {payload}")

    headers = {
        'User-Agent': "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Mobile Safari/537.36",
        'Accept-Encoding': "gzip, deflate, br, zstd",
        'Content-Type': "application/json",
        'fvideo-token': "RmgxXbZg2T4VUE/15YvsgQBdjApiuq7CL0KHBTaxExfY9Qcp9NGgbp0unx/LtNwSTG+iU9EML5Lkf7Ga/7Agq3Kd6tsHL/IbgVv3a+bAa92AxrPf5FzcJYoAkQDjj8biTkg3N2AT9gRvsgvqqjugdwt58doYism+GtCxAErTYO+bPyqJumHUuZwNe7j+0R+Zk=3e",
        'sec-ch-ua-platform': "\"Android\"",
        'csrftoken': "4adae86afd683f51960dde44d733d4d0",
        'lang': "en",
        'sec-ch-ua': "\"Chromium\";v=\"134\", \"Not:A-Brand\";v=\"24\", \"Brave\";v=\"134\"",
        'sec-ch-ua-mobile': "?1",
        'x-trace-id': "414ea84f-461d-4aa8-a748-54e17076ebb9",
        'fvideo-id': "33dde122bc96a882a0a31240de4d8ac8478f0d49",
        'bnc-uuid': "7d3480e4-25ee-456a-9be1-9f6717d3b8f3",
        'x-ui-request-trace': "414ea84f-461d-4aa8-a748-54e17076ebb9",
        'x-passthrough-token': "",
        'clienttype': "web",
        'device-info': "eyJzY3JlZW5fcmVzb2x1dGlvbiI6IjgzNSwzNzYiLCJhdmFpbGFibGVfc2NyZWVuX3Jlc29sdXRpb24iOiI4MzUsMzc2Iiwic3lzdGVtX3ZlcnNpb24iOiJBbmRyb2lkIDEwIiwiYnJhbmRfbW9kZWwiOiJtb2JpbGUgIEsgIiwic3lzdGVtX2xhbmciOiJlbi1VUyIsInRpbWV6b25lIjoiR01UKzA3OjAwIiwidGltZXpvbmVPZmZzZXQiOi00MjAsInVzZXJfYWdlbnQiOiJNb3ppbGxhLzUuMCAoTGludXg7IEFuZHJvaWQgMTA7IEspIEFwcGxlV2ViS2l0LzUzNy4zNiAoS0hUTUwsIGxpa2UgR2Vja28pIENocm9tZS8xMzQuMC4wLjAgTW9iaWxlIFNhZmFyaS81MzcuMzYiLCJsaXN0X3BsdWdpbiI6IlJNT1BteUNCLFZXTEZwY3QiLCJjYW52YXNfY29kZSI6ImZjOTAzMjhmIiwid2ViZ2xfdmVuZG9yIjoiQVJNIiwid2ViZ2xfcmVuZGVyZXIiOiJNYWxpLUc3MjAtSW1tb3J0YWxpcyBNQzEyIiwiYXVkaW8iOiIxMjQuMDE4MzM2OTM5NzQ5MTMiLCJwbGF0Zm9ybSI6IkxpbnV4IGFybXY4MSIsIndlYl90aW1lem9uZSI6IkFzaWEvSmFrYXJ0YSIsImRldmljZV9uYW1lIjoiQ2hyb21lIFYxMzQuMC4wLjAgKEFuZHJvaWQpIiwiZmluZ2VycHJpbnQiOiI4ZTNjYTQ3ODYxZDBhNWQ5ZjA2ZTRhNTkzZmUyOTM4NyIsImRldmljZV9pZCI6IiIsInJlbGF0ZWRfZGV2aWNlX2lkcyI6IiJ9",
        'sec-gpc': "1",
        'accept-language': "en-US,en;q=0.5",
        'origin': "https://www.binance.com",
        'sec-fetch-site': "same-origin",
        'sec-fetch-mode': "cors",
        'sec-fetch-dest': "empty",
        'referer': "https://www.binance.com/en/futures-activity/leaderboard/user/um?encryptedUid=5018838FFE413B7A80D2529393DB1D7A",
        'priority': "u=1, i",
        'Cookie': "BNC_FV_KEY=33dde122bc96a882a0a31240de4d8ac8478f0d49; language=en; currentAccount=; logined=y; BNC-Location=ID; sensorsdata2015jssdkcross=%7B%22distinct_id%22%3A%2265165582%22%2C%22first_id%22%3A%221950f082aab622-0544324976c3ab8-b457453-313960-1950f082aac1267%22%2C%22props%22%3A%7B%22%24latest_traffic_source_type%22%3A%22%E7%9B%B4%E6%8E%A5%E6%B5%81%E9%87%8F%22%2C%22%24latest_search_keyword%22%3A%22%E6%9C%AA%E5%8F%96%E5%88%B0%E5%80%BC_%E7%9B%B4%E6%8E%A5%E6%89%93%E5%BC%80%22%2C%22%24latest_referrer%22%3A%22%22%2C%22%24latest_utm_source%22%3A%22internal%22%2C%22%24latest_utm_medium%22%3A%22homepage%22%2C%22%24latest_utm_campaign%22%3A%22trading_dashboard%22%7D%2C%22identities%22%3A%22eyIkaWRlbnRpdHlfY29va2llX2lkIjoiMTk1MGYwODJhYWI2MjItMDU0NDMyNDk3NmMzYWI4LWI0NTc0NTMtMzEzOTYwLTE5NTBmMDgyYWFjMTI2NyIsIiRpZGVudGl0eV9sb2dpbl9pZCI6IjY1MTY1NTgyIn0%3D%22%2C%22history_login_id%22%3A%7B%22name%22%3A%22%24identity_login_id%22%2C%22value%22%3A%2265165582%22%7D%2C%22%24device_id%22%3A%221950f082aab622-0544324976c3ab8-b457453-313960-1950f082aac1267%22%7D; futures-layout=pro; se_gd=QVbVQQhkaFbBVIP8ZExFgZZDADBUTBTW1BU9QUk9lFcUwCVNWV5W1; se_gsd=CjgmOztnIgAjCQkCNDUyMzUHUFNWBQIFUVVFU1xaV1FaHVNT1; cr00=C4A6BFA9980E07400B5E0CF7E07E76E8; d1og=web.65165582.2F4B1CE9CF950147F91FF203ADBDA1EE; r2o1=web.65165582.D9C2454CCD0A2E4704B2DD6964B6D967; f30l=web.65165582.E7B6AF8943EFB034AB2BC0E54FD3FD1F; __BNC_USER_DEVICE_ID__={\"983c8cafb075d8ac82093cad828ac768\":{\"date\":1740808837864,\"value\":\"\"}}; bnc-uuid=7d3480e4-25ee-456a-9be1-9f6717d3b8f3; BNC_FV_KEY_T=101-5nQxZBI2bU1tztJme7vv0dOXeS1ImTXvXFAWCnwCO1dDcarwH6L0huw3fEZZzm0baXS5UcgHN0zq4Kp1YQhLDQ%3D%3D-jtPmJwfkUi0LURDIoI%2FvIg%3D%3D-16; BNC_FV_KEY_EXPIRE=1740998699938; p20t=web.65165582.ADAEEB30485FBD8A42124A1B8664792D; lang=en; theme=dark"
    }

    try:
        logger.info(f"Fetching position data untuk encryptedUid {encrypted_uid}")
        async with session.post(POSITION_API_URL, data=json.dumps(payload), headers=headers) as response:
            if response.status != 200:
                error_text = await response.text()
                logger.error(f"HTTP error {response.status} untuk {encrypted_uid}: {error_text}")
                raise aiohttp.ClientResponseError(
                    response.request_info,
                    response.history,
                    status=response.status,
                    message=f"Unexpected status: {error_text}"
                )
            
            data = await response.json()
            logger.debug(f"Raw API response untuk {encrypted_uid}: {data}")

            if data.get("code") != "000000" or not data.get("success"):
                logger.error(f"API error untuk {encrypted_uid}: {data.get('message', 'Unknown error')}")
                return f"Error from Binance API: {data.get('message', 'Unknown error')}"

            position_data = {
                "user_address": encrypted_uid,
                "profile_url": f"https://www.binance.com/en/futures-activity/leaderboard/user/um?encryptedUid={encrypted_uid}",
                "positions": []
            }

            for pos in data["data"]["otherPositionRetList"]:
                position = {
                    "coin": pos.get("symbol", ""),
                    "size": _safe_float(pos.get("amount")),
                    "entry_price": _safe_float(pos.get("entryPrice")),
                    "position_value": _safe_float(pos.get("markPrice") * abs(pos.get("amount"))),
                    "unrealized_pnl": _safe_float(pos.get("pnl")),
                    "leverage": _safe_float(pos.get("leverage")),
                    "updateTime": datetime.datetime.fromtimestamp(pos["updateTimeStamp"] / 1000).strftime('%Y-%m-%d %H:%M:%S')
                }
                position_data["positions"].append(position)
                logger.debug(f"Posisi diproses untuk {encrypted_uid}: {position}")

            logger.info(f"Successfully processed position info untuk {encrypted_uid}")
            return position_data

    except aiohttp.ClientResponseError as e:
        logger.error(f"HTTP error fetching position info untuk {encrypted_uid}: {e}", exc_info=True)
        return f"Error occurred while fetching position info: {e}"
    except aiohttp.ClientError as e:
        logger.error(f"Network error fetching position info untuk {encrypted_uid}: {e}", exc_info=True)
        return f"Error occurred while fetching position info: {e}"
    except Exception as e:
        logger.error(f"Unexpected error fetching position info untuk {encrypted_uid}: {e}", exc_info=True)
        return f"Error occurred while fetching position info: {e}"

async def get_other_leaderboard_base_info(session: aiohttp.ClientSession, encrypted_uid: str) -> dict | str:
    """Mendapatkan informasi dasar (termasuk nickname) dari Binance Futures Leaderboard secara asinkronus."""
    payload = {
        "encryptedUid": encrypted_uid
    }
    logger.debug(f"Payload untuk get_other_leaderboard_base_info: {payload}")

    headers = {
        'User-Agent': "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Mobile Safari/537.36",
        'Accept-Encoding': "gzip, deflate, br, zstd",
        'Content-Type': "application/json",
        'fvideo-token': "UXQLQOuJgualPo5+Z1RnPbahk53QPqipPMYrwXVNvHYx662sqGkmKyRaIiFM/l9OZ+HsraN6/KVve5ioeaRLRKB8sfYHTfonBZiWaOPtSPe7vsvZpe7Nclg9izzc9GqwBpW03fXjc8S/d+gouc8tMdYbgJh1tLFAtNKgoYrdbSjjOoCYrWUAl7sT+rlVKjAdM=47",
        'sec-ch-ua-platform': "\"Android\"",
        'csrftoken': "4adae86afd683f51960dde44d733d4d0",
        'lang': "en",
        'sec-ch-ua': "\"Chromium\";v=\"134\", \"Not:A-Brand\";v=\"24\", \"Brave\";v=\"134\"",
        'sec-ch-ua-mobile': "?1",
        'x-trace-id': "6ea2e3f0-a928-4bbf-88da-a579c95dd49b",
        'fvideo-id': "33dde122bc96a882a0a31240de4d8ac8478f0d49",
        'bnc-uuid': "7d3480e4-25ee-456a-9be1-9f6717d3b8f3",
        'x-ui-request-trace': "6ea2e3f0-a928-4bbf-88da-a579c95dd49b",
        'x-passthrough-token': "",
        'clienttype': "web",
        'device-info': "eyJzY3JlZW5fcmVzb2x1dGlvbiI6IjgzNSwzNzYiLCJhdmFpbGFibGVfc2NyZWVuX3Jlc29sdXRpb24iOiI4MzUsMzc2Iiwic3lzdGVtX3ZlcnNpb24iOiJBbmRyb2lkIDEwIiwiYnJhbmRfbW9kZWwiOiJtb2JpbGUgIEsgIiwic3lzdGVtX2xhbmciOiJlbi1VUyIsInRpbWV6b25lIjoiR01UKzA3OjAwIiwidGltZXpvbmVPZmZzZXQiOi00MjAsInVzZXJfYWdlbnQiOiJNb3ppbGxhLzUuMCAoTGludXg7IEFuZHJvaWQgMTA7IEspIEFwcGxlV2ViS2l0LzUzNy4zNiAoS0hUTUwsIGxpa2UgR2Vja28pIENocm9tZS8xMzQuMC4wLjAgTW9iaWxlIFNhZmFyaS81MzcuMzYiLCJsaXN0X3BsdWdpbiI6IlJNT1BteUNCLFZXTEZwY3QiLCJjYW52YXNfY29kZSI6ImZjOTAzMjhmIiwid2ViZ2xfdmVuZG9yIjoiQVJNIiwid2ViZ2xfcmVuZGVyZXIiOiJNYWxpLUc3MjAtSW1tb3J0YWxpcyBNQzEyIiwiYXVkaW8iOiIxMjQuMDE4MzM2OTM5NzQ5MTMiLCJwbGF0Zm9ybSI6IkxpbnV4IGFybXY4MSIsIndlYl90aW1lem9uZSI6IkFzaWEvSmFrYXJ0YSIsImRldmljZV9uYW1lIjoiQ2hyb21lIFYxMzQuMC4wLjAgKEAnZHJvaWQpIiwiZmluZ2VycHJpbnQiOiI4ZTNjYTQ3ODYxZDBhNWQ5ZjA2ZTRhNTkzZmUyOTM4NyIsImRldmljZV9pZCI6IiIsInJlbGF0ZWRfZGV2aWNlX2lkcyI6IiJ9",
        'sec-gpc': "1",
        'accept-language': "en-US,en;q=0.5",
        'origin': "https://www.binance.com",
        'sec-fetch-site': "same-origin",
        'sec-fetch-mode': "cors",
        'sec-fetch-dest': "empty",
        'referer': "https://www.binance.com/en/futures-activity/leaderboard/user/um?encryptedUid=B0D80847B206AB5D53AF57424AB89B60",
        'priority': "u=1, i",
        'Cookie': "BNC_FV_KEY=33dde122bc96a882a0a31240de4d8ac8478f0d49; language=en; currentAccount=; logined=y; BNC-Location=ID; sensorsdata2015jssdkcross=%7B%22distinct_id%22%3A%2265165582%22%2C%22first_id%22%3A%221950f082aab622-0544324976c3ab8-b457453-313960-1950f082aac1267%22%2C%22props%22%3A%7B%22%24latest_traffic_source_type%22%3A%22%E7%9B%B4%E6%8E%A5%E6%B5%81%E9%87%8F%22%2C%22%24latest_search_keyword%22%3A%22%E6%9C%AA%E5%8F%96%E5%88%B0%E5%80%BC_%E7%9B%B4%E6%8E%A5%E6%89%93%E5%BC%80%22%2C%22%24latest_referrer%22%3A%22%22%2C%22%24latest_utm_source%22%3A%22internal%22%2C%22%24latest_utm_medium%22%3A%22homepage%22%2C%22%24latest_utm_campaign%22%3A%22trading_dashboard%22%7D%2C%22identities%22%3A%22eyIkaWRlbnRpdHlfY29va2llX2lkIjoiMTk1MGYwODJhYWI2MjItMDU0NDMyNDk3NmMzYWI4LWI0NTc0NTMtMzEzOTYwLTE5NTBmMDgyYWFjMTI2NyIsIiRpZGVudGl0eV9sb2dpbl9pZCI6IjY1MTY1NTgyIn0%3D%22%2C%22history_login_id%22%3A%7B%22name%22%3A%22%24identity_login_id%22%2C%22value%22%3A%2265165582%22%7D%2C%22%24device_id%22%3A%221950f082aab622-0544324976c3ab8-b457453-313960-1950f082aac1267%22%7D; futures-layout=pro; se_gd=QVbVQQhkaFbBVIP8ZExFgZZDADBUTBTW1BU9QUk9lFcUwCVNWV5W1; se_gsd=CjgmOztnIgAjCQkCNDUyMzUHUFNWBQIFUVVFU1xaV1FaHVNT1; cr00=C4A6BFA9980E07400B5E0CF7E07E76E8; d1og=web.65165582.2F4B1CE9CF950147F91FF203ADBDA1EE; r2o1=web.65165582.D9C2454CCD0A2E4704B2DD6964B6D967; f30l=web.65165582.E7B6AF8943EFB034AB2BC0E54FD3FD1F; __BNC_USER_DEVICE_ID__={\"983c8cafb075d8ac82093cad828ac768\":{\"date\":1740808837864,\"value\":\"\"}}; bnc-uuid=7d3480e4-25ee-456a-9be1-9f6717d3b8f3; BNC_FV_KEY_T=101-5nQxZBI2bU1tztJme7vv0dOXeS1ImTXvXFAWCnwCO1dDcarwH6L0huw3fEZZzm0baXS5UcgHN0zq4Kp1YQhLDQ%3D%3D-jtPmJwfkUi0LURDIoI%2FvIg%3D%3D-16; BNC_FV_KEY_EXPIRE=1740998699938; p20t=web.65165582.ADAEEB30485FBD8A42124A1B8664792D; lang=en; theme=dark"
    }

    try:
        logger.info(f"Fetching base info untuk encryptedUid {encrypted_uid}")
        async with session.post(BASE_INFO_API_URL, data=json.dumps(payload), headers=headers) as response:
            if response.status != 200:
                error_text = await response.text()
                logger.error(f"HTTP error {response.status} untuk {encrypted_uid}: {error_text}")
                raise aiohttp.ClientResponseError(
                    response.request_info,
                    response.history,
                    status=response.status,
                    message=f"Unexpected status: {error_text}"
                )
            
            data = await response.json()
            logger.debug(f"Raw API response untuk {encrypted_uid}: {data}")

            if data.get("code") != "000000" or not data.get("success"):
                logger.error(f"API error untuk {encrypted_uid}: {data.get('message', 'Unknown error')}")
                return f"Error from Binance API: {data.get('message', 'Unknown error')}"

            base_info = {
                "nickName": data["data"].get("nickName", ""),
                "userPhotoUrl": data["data"].get("userPhotoUrl", ""),
                "positionShared": data["data"].get("positionShared", False),
                "followerCount": data["data"].get("followerCount", 0),
                "twitterUrl": data["data"].get("twitterUrl", "")
            }
            logger.debug(f"Data base info yang diproses: {base_info}")

            logger.info(f"Successfully processed base info untuk {encrypted_uid}")
            return base_info

    except aiohttp.ClientResponseError as e:
        logger.error(f"HTTP error fetching base info untuk {encrypted_uid}: {e}", exc_info=True)
        return f"Error occurred while fetching base info: {e}"
    except aiohttp.ClientError as e:
        logger.error(f"Network error fetching base info untuk {encrypted_uid}: {e}", exc_info=True)
        return f"Error occurred while fetching base info: {e}"
    except Exception as e:
        logger.error(f"Unexpected error fetching base info untuk {encrypted_uid}: {e}", exc_info=True)
        return f"Error occurred while fetching base info: {e}"

async def get_markprice(session: aiohttp.ClientSession, symbol: str) -> str:
    """Mendapatkan mark price dari Binance Futures API secara asinkronus."""
    params = {"symbol": symbol}
    logger.debug(f"Parameter untuk get_markprice: {params}")

    try:
        logger.info(f"Fetching mark price untuk simbol {symbol}")
        async with session.get(MARK_PRICE_API_URL, params=params) as response:
            if response.status != 200:
                error_text = await response.text()
                logger.error(f"HTTP error {response.status} untuk {symbol}: {error_text}")
                raise aiohttp.ClientResponseError(
                    response.request_info,
                    response.history,
                    status=response.status,
                    message=f"Unexpected status: {error_text}"
                )
            
            data = await response.json()
            logger.debug(f"Raw API response untuk {symbol}: {data}")

            mark_price = data.get("markPrice", "N/A")
            logger.debug(f"Mark price untuk {symbol}: {mark_price}")
            return mark_price

    except aiohttp.ClientResponseError as e:
        logger.error(f"HTTP error fetching mark price untuk {symbol}: {e}", exc_info=True)
        return "N/A"
    except aiohttp.ClientError as e:
        logger.error(f"Network error fetching mark price untuk {symbol}: {e}", exc_info=True)
        return "N/A"
    except Exception as e:
        logger.error(f"Unexpected error fetching mark price untuk {symbol}: {e}", exc_info=True)
        return "N/A"