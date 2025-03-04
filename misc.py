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

logger.info("Modul misc.py dimuat")
# Tidak ada fungsi spesifik diperlukan untuk Binance saat ini
# Header sudah ditentukan di binance.py