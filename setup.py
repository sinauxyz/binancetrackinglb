import json
import configparser
import logging

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

def setup():
    """
    Menyiapkan konfigurasi awal untuk bot Binance Leaderboard Tracker.
    """
    logger.info("Memulai proses setup konfigurasi bot")
    
    # Setup Telegram
    config = configparser.ConfigParser()
    config['telegram'] = {}
    
    while True:
        bottoken = input("Masukkan token bot Telegram: ").strip()
        logger.debug(f"Token bot yang dimasukkan: {bottoken}")
        if bottoken and ":" in bottoken:
            break
        print("Token bot harus mengandung ':' dan tidak boleh kosong.")
        logger.warning("Input token bot tidak valid")

    while True:
        chatid = input("Masukkan chat ID Telegram: ").strip()
        logger.debug(f"Chat ID yang dimasukkan: {chatid}")
        if chatid and chatid.lstrip('-').isdigit():
            break
        print("Chat ID harus berupa angka (bisa negatif) dan tidak boleh kosong.")
        logger.warning("Input chat ID tidak valid")

    print("\nMasukkan daftar admin (chat ID) yang diizinkan untuk perintah, pisahkan dengan koma:")
    while True:
        admins_input = input("Daftar admin (contoh: -123456789,123456): ").strip()
        logger.debug(f"Daftar admin yang dimasukkan: {admins_input}")
        try:
            admins = [int(admin.strip()) for admin in admins_input.split(',')]
            if admins:
                break
            print("Daftar admin tidak boleh kosong.")
        except ValueError:
            print("Setiap ID harus berupa angka (bisa negatif).")
        logger.warning("Input daftar admin tidak valid")

    config['telegram']['bottoken'] = bottoken
    config['telegram']['chatid'] = chatid
    config['telegram']['admins'] = ','.join(map(str, admins))
    logger.debug(f"Konfigurasi Telegram: {dict(config['telegram'])}")

    try:
        with open('config.ini', 'w') as configfile:
            config.write(configfile)
        logger.info("File config.ini telah dibuat")
    except IOError as e:
        logger.error(f"Gagal menulis config.ini: {e}", exc_info=True)
        raise

    # Setup encryptedUid
    user_addresses = []
    print("\nMasukkan encryptedUid pengguna (tekan Enter setelah setiap UID, kosongkan untuk selesai):")
    while True:
        uid = input("Encrypted UID: ").strip()
        logger.debug(f"Encrypted UID yang dimasukkan: {uid}")
        if not uid:
            break
        if len(uid) > 0:
            user_addresses.append(uid)
        else:
            print("Encrypted UID tidak boleh kosong.")
            logger.warning(f"Encrypted UID tidak valid: {uid}")
    
    try:
        with open('user_addresses.json', 'w') as f:
            json.dump(user_addresses, f, indent=2)
        logger.info(f"File user_addresses.json telah dibuat dengan {len(user_addresses)} UID")
        logger.debug(f"Isi user_addresses.json: {user_addresses}")
    except IOError as e:
        logger.error(f"Gagal menulis user_addresses.json: {e}", exc_info=True)
        raise

    print("\nSetup selesai! File config.ini dan user_addresses.json telah dibuat.")
    logger.info("Proses setup selesai")

if __name__ == "__main__":
    logger.info("Menjalankan setup.py")
    setup()