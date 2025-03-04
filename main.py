import pandas as pd
import asyncio
import datetime
import logging
import time
import aiohttp
from message import telegram_send_message, telegram_polling, load_user_addresses, telegram_chat_id
from binance import get_other_position, get_other_leaderboard_base_info, get_markprice
from shared import TARGETED_USER_ADDRESSES, user_addresses_lock, USER_NICKNAMES

# Konfigurasi logging hanya di main.py
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Inisialisasi TARGETED_USER_ADDRESSES dari shared.py
logger.info("Memulai inisialisasi TARGETED_USER_ADDRESSES")
TARGETED_USER_ADDRESSES.extend(load_user_addresses())
logger.debug(f"TARGETED_USER_ADDRESSES setelah inisialisasi: {TARGETED_USER_ADDRESSES}")

ACCOUNT_INFO_URL_TEMPLATE = 'https://www.binance.com/en/futures-activity/leaderboard/user/um?encryptedUid={}'

def modify_data(data) -> pd.DataFrame:
    """Memproses data posisi dari Binance menjadi DataFrame."""
    logger.debug(f"Memproses data untuk DataFrame: {data}")
    if not data or 'positions' not in data:
        logger.warning("Struktur data tidak valid atau 'positions' tidak ada dalam data.")
        return pd.DataFrame()

    positions = data['positions']
    df = pd.DataFrame(positions)
    logger.debug(f"DataFrame awal: {df.head()}")

    required_columns = ['coin', 'size', 'entry_price', 'position_value', 'unrealized_pnl', 'leverage', 'updateTime']
    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        logger.error(f"Kolom yang diperlukan hilang: {missing_cols}")
        return pd.DataFrame()

    df.set_index('coin', inplace=True)
    df['estimatedPosition'] = df['size'].apply(lambda x: 'LONG' if x > 0 else 'SHORT')
    logger.debug(f"DataFrame setelah pemrosesan: {df.head()}")
    return df[['estimatedPosition', 'leverage', 'entry_price', 'position_value', 'unrealized_pnl', 'updateTime']]

previous_symbols = {}
previous_position_results = {}
is_first_runs = {}

async def fetch_nicknames(session: aiohttp.ClientSession):
    """Mengambil nickName untuk semua encryptedUid saat startup."""
    logger.info("Memulai pengambilan nickname untuk semua encryptedUid")
    with user_addresses_lock:
        for encrypted_uid in TARGETED_USER_ADDRESSES:
            if encrypted_uid not in USER_NICKNAMES:
                logger.debug(f"Mengambil nickname untuk encryptedUid: {encrypted_uid}")
                base_info = await get_other_leaderboard_base_info(session, encrypted_uid)
                if isinstance(base_info, dict):
                    USER_NICKNAMES[encrypted_uid] = base_info.get("nickName", encrypted_uid)
                    logger.debug(f"Nickname untuk {encrypted_uid}: {USER_NICKNAMES[encrypted_uid]}")
                else:
                    USER_NICKNAMES[encrypted_uid] = encrypted_uid  # Fallback ke encryptedUid penuh
                    logger.warning(f"Gagal mengambil nickname untuk {encrypted_uid}, menggunakan encryptedUid sebagai fallback: {USER_NICKNAMES[encrypted_uid]}")
    logger.info(f"Nickname yang berhasil diambil: {USER_NICKNAMES}")

async def send_new_position_message(session: aiohttp.ClientSession, symbol, row, encrypted_uid):
    nickName = USER_NICKNAMES.get(encrypted_uid, encrypted_uid)
    logger.debug(f"Mengirim pesan posisi baru untuk {symbol}, encryptedUid: {encrypted_uid}, nickName: {nickName}")
    estimated_position = row['estimatedPosition']
    leverage = row['leverage']
    entry_price = row['entry_price']
    position_value = row['position_value']
    pnl = row['unrealized_pnl']
    updatetime = row['updateTime']
    profile_url = ACCOUNT_INFO_URL_TEMPLATE.format(encrypted_uid)
    pnl_emoji = "🟢" if pnl >= 0 else "🔴"
    message = (
        f"⚠️ [<b>{nickName}</b>]\n"
        f"❇️ New position opened\n\n"
        f"Position: {symbol} {estimated_position} {leverage}X\n\n"
        f"💵 Base currency - USDT\n"
        f"------------------------------\n"
        f"🎯 Entry Price: {entry_price}\n"
        f"💰 Est. Entry Size: {position_value}\n"
        f"{pnl_emoji} PnL: {pnl}\n\n"
        f"🕒 Last Update:\n"
        f"{updatetime} (UTC+7)\n"
        f"🔗 <a href='{profile_url}'>VIEW PROFILE ON BINANCE</a>"
    )
    logger.debug(f"Pesan yang akan dikirim: {message}")
    success = await telegram_send_message(session, message)
    if success:
        logger.info(f"Pesan posisi baru untuk {symbol} berhasil dikirim.")
    else:
        logger.error(f"Gagal mengirim pesan posisi baru untuk {symbol}.")

async def send_closed_position_message(session: aiohttp.ClientSession, symbol, row, encrypted_uid):
    nickName = USER_NICKNAMES.get(encrypted_uid, encrypted_uid)
    logger.debug(f"Mengirim pesan posisi ditutup untuk {symbol}, encryptedUid: {encrypted_uid}, nickName: {nickName}")
    estimated_position = row['estimatedPosition']
    leverage = row['leverage']
    updatetime = row['updateTime']
    profile_url = ACCOUNT_INFO_URL_TEMPLATE.format(encrypted_uid)
    current_price = await get_markprice(session, symbol)
    logger.debug(f"Harga saat ini untuk {symbol}: {current_price}")
    message = (
        f"⚠️ [<b>{nickName}</b>]\n"
        f"⛔️ Position closed\n\n"
        f"Position: {symbol} {estimated_position} {leverage}X\n"
        f"💵 Current Price: {current_price} USDT\n\n"
        f"🕒 Last Update:\n"
        f"{updatetime} (UTC+7)\n"
        f"🔗 <a href='{profile_url}'>VIEW PROFILE ON BINANCE</a>"
    )
    logger.debug(f"Pesan yang akan dikirim: {message}")
    success = await telegram_send_message(session, message)
    if success:
        logger.info(f"Pesan posisi ditutup untuk {symbol} berhasil dikirim.")
    else:
        logger.error(f"Gagal mengirim pesan posisi ditutup untuk {symbol}.")

async def send_current_positions(session: aiohttp.ClientSession, position_result, encrypted_uid):
    nickName = USER_NICKNAMES.get(encrypted_uid, encrypted_uid)
    logger.debug(f"Mengirim pesan posisi saat ini untuk encryptedUid: {encrypted_uid}, nickName: {nickName}")
    if position_result.empty:
        message = f"⚠️ [<b>{nickName}</b>]\n💎 <b>No positions found</b>"
        logger.debug("Tidak ada posisi ditemukan untuk dikirim.")
    else:
        message = f"⚠️ [<b>{nickName}</b>]\n💎 Current positions:\n\n"
        for symbol, row in position_result.iterrows():
            pnl_emoji = "🟢" if row['unrealized_pnl'] >= 0 else "🔴"
            message += (
                f"🔄 Position: {symbol} {row['estimatedPosition']} {row['leverage']}X\n\n"
                f"💵 Base currency - USDT\n"
                f"------------------------------\n"
                f"🎯 Entry Price: {row['entry_price']}\n"
                f"💰 Est. Entry Size: {row['position_value']}\n"
                f"{pnl_emoji} PnL: {row['unrealized_pnl']}\n\n"
            )
        message += f"🕒 Last Update:\n{row['updateTime']} (UTC+7)\n"
        message += f"🔗 <a href='{ACCOUNT_INFO_URL_TEMPLATE.format(encrypted_uid)}'>VIEW PROFILE ON BINANCE</a>"
    logger.debug(f"Pesan yang akan dikirim: {message}")
    success = await telegram_send_message(session, message)
    if success:
        logger.info(f"Pesan posisi saat ini untuk {encrypted_uid} berhasil dikirim.")
    else:
        logger.error(f"Gagal mengirim pesan posisi saat ini untuk {encrypted_uid}.")

async def monitor_positions():
    async with aiohttp.ClientSession() as session:
        logger.info("Memulai pemantauan posisi Binance Leaderboard")
        await fetch_nicknames(session)
        
        while True:
            try:
                start_time = time.time()
                logger.debug("Memulai iterasi pemantauan posisi")
                
                with user_addresses_lock:
                    current_addresses = TARGETED_USER_ADDRESSES.copy()
                logger.debug(f"Daftar encryptedUid yang dipantau: {current_addresses}")

                for address in current_addresses:
                    if address not in is_first_runs:
                        is_first_runs[address] = True
                        logger.debug(f"Menandai {address} sebagai iterasi pertama")

                tasks = []
                for encrypted_uid in current_addresses:
                    logger.debug(f"Mengambil data posisi untuk {encrypted_uid}")
                    position_info = await get_other_position(session, encrypted_uid)

                    if isinstance(position_info, str):
                        logger.error(f"Error untuk encryptedUid {encrypted_uid}: {position_info}")
                        await telegram_send_message(session, f"Error untuk encryptedUid {encrypted_uid}: {position_info}", telegram_chat_id)
                        continue

                    position_result = modify_data(position_info)
                    logger.debug(f"Hasil pemrosesan posisi untuk {encrypted_uid}: {position_result}")

                    new_symbols = position_result.index.difference(previous_symbols.get(encrypted_uid, pd.Index([])))
                    if not is_first_runs[encrypted_uid] and not new_symbols.empty:
                        logger.debug(f"Posisi baru terdeteksi untuk {encrypted_uid}: {new_symbols}")
                        for symbol in new_symbols:
                            tasks.append(send_new_position_message(session, symbol, position_result.loc[symbol], encrypted_uid))

                    closed_symbols = previous_symbols.get(encrypted_uid, pd.Index([])).difference(position_result.index)
                    if not is_first_runs[encrypted_uid] and not closed_symbols.empty:
                        logger.debug(f"Posisi tertutup terdeteksi untuk {encrypted_uid}: {closed_symbols}")
                        for symbol in closed_symbols:
                            if symbol in previous_position_results.get(encrypted_uid, pd.DataFrame()).index:
                                tasks.append(send_closed_position_message(session, symbol, previous_position_results[encrypted_uid].loc[symbol], encrypted_uid))

                    if is_first_runs[encrypted_uid]:
                        logger.debug(f"Mengirim posisi saat ini untuk iterasi pertama {encrypted_uid}")
                        tasks.append(send_current_positions(session, position_result, encrypted_uid))

                    previous_position_results[encrypted_uid] = position_result.copy()
                    previous_symbols[encrypted_uid] = position_result.index.copy()
                    is_first_runs[encrypted_uid] = False

                if tasks:
                    logger.debug(f"Menjalankan {len(tasks)} tugas pengiriman pesan paralel")
                    await asyncio.gather(*tasks)

                ping_time = (time.time() - start_time) * 1000
                current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                logger.info(f"✅ Bot is still running | Time: {current_time} | Ping: {ping_time:.2f}ms")
                
                await asyncio.sleep(60)
            
            except Exception as e:
                logger.error(f"Global error occurred: {e}", exc_info=True)
                error_message = f"Global error occurred:\n{e}\n\nRetrying after 60s"
                await telegram_send_message(session, error_message, telegram_chat_id)
                await asyncio.sleep(60)

async def main():
    logger.info("Memulai eksekusi utama bot Binance Leaderboard Tracker")
    await asyncio.gather(
        telegram_polling(),
        monitor_positions()
    )
    logger.info("Eksekusi utama selesai")

if __name__ == "__main__":
    logger.info("Menjalankan bot Binance Leaderboard Tracker")
    asyncio.run(main())