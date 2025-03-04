import threading
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

logger.info("Inisialisasi variabel global di shared.py")
# Variabel global untuk caching encryptedUid dan nickname
TARGETED_USER_ADDRESSES = []
user_addresses_lock = threading.Lock()
USER_NICKNAMES = {}  # Ditambahkan ke shared.py untuk menghindari circular import
logger.debug(f"TARGETED_USER_ADDRESSES awal: {TARGETED_USER_ADDRESSES}")
logger.debug(f"USER_NICKNAMES awal: {USER_NICKNAMES}")
logger.debug("Lock threading untuk user_addresses_lock telah dibuat")