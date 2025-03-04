import aiohttp
import asyncio
import configparser
import logging
import json
from shared import TARGETED_USER_ADDRESSES, user_addresses_lock, USER_NICKNAMES

logger = logging.getLogger(__name__)  # Hanya definisikan logger, konfigurasi ada di main.py

# Membaca konfigurasi
logger.info("Memulai pembacaan konfigurasi dari config.ini")
config = configparser.ConfigParser()
if not config.read('config.ini'):
    logger.error("File config.ini tidak ditemukan")
    raise FileNotFoundError("File config.ini tidak ditemukan")

try:
    telegram_bot_token = config['telegram']['bottoken']
    telegram_chat_id = config['telegram']['chatid']
    admins = [int(admin.strip()) for admin in config['telegram']['admins'].split(',')]
    logger.debug(f"Konfigurasi Telegram: bottoken={telegram_bot_token[:10]}..., chatid={telegram_chat_id}, admins={admins}")
except KeyError as e:
    logger.error(f"Konfigurasi tidak lengkap di config.ini: {e}")
    raise Exception(f"Pastikan file config.ini memiliki bagian [telegram] dengan 'bottoken', 'chatid', dan 'admins'")
except ValueError as e:
    logger.error(f"Format 'admins' di config.ini tidak valid: {e}")
    raise Exception("Daftar 'admins' harus berupa angka yang dipisahkan koma (contoh: -123456789,123456)")

if not telegram_chat_id or not telegram_chat_id.lstrip('-').isdigit():
    logger.error(f"telegram_chat_id tidak valid: {telegram_chat_id}")
    raise ValueError("chatid di config.ini harus berupa angka (bisa negatif) dan tidak boleh kosong")
telegram_chat_id = str(telegram_chat_id)

async def telegram_send_message(session: aiohttp.ClientSession, message: str, chat_id: str = telegram_chat_id) -> bool:
    """Mengirim pesan ke Telegram secara asinkronus."""
    logger.debug(f"Mengirim pesan ke chat_id: {chat_id}, pesan: {message[:50]}...")
    if not chat_id or not chat_id.lstrip('-').isdigit():
        logger.error(f"chat_id tidak valid: {chat_id}")
        return False

    api_url = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'html',
        'disable_web_page_preview': True
    }
    logger.debug(f"Payload untuk telegram_send_message: {payload}")

    try:
        async with session.post(api_url, json=payload) as response:
            response.raise_for_status()
            logger.info(f"Pesan berhasil dikirim ke chat {chat_id}")
            return True
    except aiohttp.ClientError as e:
        logger.error(f"Gagal mengirim pesan ke chat {chat_id}: {e}", exc_info=True)
        return False

def load_user_addresses() -> list:
    """Memuat daftar user_addresses dari file JSON (synchronous)."""
    logger.info("Memuat user_addresses dari user_addresses.json")
    try:
        with open('user_addresses.json', 'r') as f:
            addresses = json.load(f)
            logger.debug(f"Daftar user_addresses yang dimuat: {addresses}")
            return addresses
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.warning(f"Gagal memuat user_addresses.json: {e}, mengembalikan list kosong")
        return []

async def update_user_addresses(user_address: str) -> bool:
    """Menambahkan user_address ke user_addresses.json dan memori dengan validasi ketat."""
    logger.debug(f"Menambahkan user_address: {user_address}")
    with user_addresses_lock:
        user_addresses = TARGETED_USER_ADDRESSES.copy()

        if user_address in user_addresses:
            logger.warning(f"User_address {user_address} sudah ada")
            return False

        # Validasi: harus string, alfanumerik, minimal 32 karakter (sesuai encryptedUid Binance)
        if not isinstance(user_address, str) or not user_address or len(user_address) < 32 or not user_address.isalnum():
            logger.warning(f"Alamat tidak valid: {user_address}")
            return False

        user_addresses.append(user_address)
        try:
            with open('user_addresses.json', 'w') as f:
                json.dump(user_addresses, f, indent=2)
            TARGETED_USER_ADDRESSES[:] = user_addresses
            logger.info(f"Berhasil menambahkan {user_address} ke user_addresses.json")
            logger.debug(f"Daftar TARGETED_USER_ADDRESSES setelah pembaruan: {TARGETED_USER_ADDRESSES}")
            return True
        except IOError as e:
            logger.error(f"Gagal memperbarui user_addresses.json: {e}", exc_info=True)
            return False

async def remove_user_address(index: int) -> bool:
    """Menghapus user_address berdasarkan nomor urutan dari file dan memori."""
    logger.debug(f"Menghapus user_address pada indeks: {index}")
    with user_addresses_lock:
        user_addresses = TARGETED_USER_ADDRESSES.copy()

        if not isinstance(index, int) or index < 0 or index >= len(user_addresses):
            logger.warning(f"Indeks tidak valid: {index}")
            return False

        removed_address = user_addresses.pop(index)
        try:
            with open('user_addresses.json', 'w') as f:
                json.dump(user_addresses, f, indent=2)
            TARGETED_USER_ADDRESSES[:] = user_addresses
            logger.info(f"Berhasil menghapus {removed_address} dari user_addresses.json")
            logger.debug(f"Daftar TARGETED_USER_ADDRESSES setelah penghapusan: {TARGETED_USER_ADDRESSES}")
            return True
        except IOError as e:
            logger.error(f"Gagal memperbarui user_addresses.json: {e}", exc_info=True)
            return False

async def process_telegram_updates(session: aiohttp.ClientSession, offset: int = None, retries=3):
    """Memproses pesan masuk dari Telegram dan menangani perintah /add, /list, /remove."""
    api_url = f"https://api.telegram.org/bot{telegram_bot_token}/getUpdates"
    params = {'timeout': 30, 'offset': offset} if offset else {'timeout': 30}  # Timeout dikurangi ke 30 detik
    logger.debug(f"Parameter untuk getUpdates: {params}")

    for attempt in range(retries):
        try:
            logger.info(f"Memulai polling update Telegram (percobaan {attempt + 1}/{retries})")
            async with session.get(api_url, params=params) as response:
                response.raise_for_status()
                data = await response.json()
                logger.debug(f"Raw API response dari getUpdates: {data}")

                if not data.get('ok') or not data.get('result'):
                    logger.debug("Tidak ada update baru dari Telegram")
                    return offset

                for update in data['result']:
                    update_id = update['update_id']
                    message = update.get('message', {})
                    chat_id = message.get('chat', {}).get('id')
                    text = message.get('text', '')
                    logger.debug(f"Memproses update ID {update_id} dari chat {chat_id}: {text}")

                    if chat_id not in admins:
                        logger.warning(f"Chat ID {chat_id} tidak memiliki izin untuk perintah")
                        await telegram_send_message(session, "Anda tidak memiliki izin untuk menggunakan perintah ini.", str(chat_id))
                        continue

                    if text.startswith('/add'):
                        parts = text.split(maxsplit=1)
                        logger.debug(f"Perintah /add diterima: {parts}")
                        if len(parts) < 2:
                            await telegram_send_message(session, "Format salah. Gunakan: /add <encryptedUid>", str(chat_id))
                            continue
                        user_address = parts[1].strip()
                        if await update_user_addresses(user_address):
                            await telegram_send_message(session, f"Berhasil menambahkan {user_address}", str(chat_id))
                        else:
                            await telegram_send_message(session, f"Gagal menambahkan {user_address}. UID tidak valid atau sudah ada.", str(chat_id))

                    elif text == '/list':
                        logger.debug("Perintah /list diterima")
                        with user_addresses_lock:
                            user_addresses = TARGETED_USER_ADDRESSES.copy()
                        if not user_addresses:
                            await telegram_send_message(session, "Daftar encryptedUid kosong.", str(chat_id))
                        else:
                            message = "Daftar encryptedUid:\n"
                            for i, addr in enumerate(user_addresses):
                                message += f"{i}. {USER_NICKNAMES.get(addr, addr)}\n"
                            await telegram_send_message(session, message, str(chat_id))
                            logger.debug(f"Daftar UID yang dikirim: {user_addresses}")

                    elif text.startswith('/remove'):
                        parts = text.split(maxsplit=1)
                        logger.debug(f"Perintah /remove diterima: {parts}")
                        if len(parts) < 2 or not parts[1].isdigit():
                            await telegram_send_message(session, "Format salah. Gunakan: /remove <nomor>", str(chat_id))
                            continue
                        index = int(parts[1])
                        if await remove_user_address(index):
                            await telegram_send_message(session, f"Berhasil menghapus UID pada nomor {index}", str(chat_id))
                        else:
                            await telegram_send_message(session, f"Gagal menghapus. Nomor {index} tidak valid.", str(chat_id))

                logger.info(f"Update Telegram diproses, offset baru: {update_id + 1}")
                return update_id + 1

        except aiohttp.ClientError as e:
            logger.error(f"Percobaan {attempt + 1} gagal: {e}", exc_info=(attempt == retries - 1))
            if attempt < retries - 1:
                await asyncio.sleep(5)  # Tunggu 5 detik sebelum retry
            else:
                logger.error(f"Gagal memproses update Telegram setelah {retries} percobaan: {e}")
                return offset

async def check_network(session: aiohttp.ClientSession) -> bool:
    """Memeriksa koneksi jaringan ke Telegram."""
    try:
        async with session.get("https://api.telegram.org") as response:
            return response.status == 200
    except aiohttp.ClientError:
        return False

async def telegram_polling():
    """Tugas asinkronus untuk polling Telegram dengan pengecekan jaringan."""
    logger.info("Memulai polling Telegram")
    timeout = aiohttp.ClientTimeout(total=70, connect=30, sock_connect=30, sock_read=70)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        offset = None
        while True:
            try:
                if not await check_network(session):
                    logger.warning("Koneksi jaringan bermasalah, menunggu 10 detik")
                    await asyncio.sleep(10)
                    continue
                offset = await process_telegram_updates(session, offset)
                await asyncio.sleep(1)
                logger.debug("Menunggu 1 detik sebelum polling berikutnya")
            except Exception as e:
                logger.error(f"Error di Telegram polling: {e}", exc_info=True)
                await asyncio.sleep(10)
                logger.debug("Menunggu 10 detik sebelum mencoba lagi setelah error")