# src/config.py
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "vagas.db"
LOCK_FILE = DATA_DIR / "bot.lock"
LOG_FILE = LOGS_DIR / "execucao.log"

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Regras gerais
LIMITE_NOTIFICACOES = 1
DIAS_LINKEDIN_RECORRENTE = 2
LOCK_EXPIRA_EM_SEGUNDOS = 3 * 3600

# Parâmetros dos Scrapers
HTTP_TIMEOUT = 30
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

DELAY_MIN = 0.5
DELAY_MAX = 1.2

# Gupy
GUPY_LIMITE_POR_PAGINA = 100
GUPY_MAX_PAGINAS = 5

# LinkedIn
LINKEDIN_MAX_PAGINAS = 3
LINKEDIN_MAX_DETALHES = 400
LINKEDIN_JANELA_INICIAL = "r2592000"

# Remotar
REMOTAR_MAX_ROLAGENS = 15