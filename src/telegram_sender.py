

import requests
import urllib3
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)
logging.getLogger("requests").setLevel(logging.CRITICAL)

TOKEN = "SEU_TOKEN_BOT_TELEGRAM/YOUR_TELEGRAM_BOT_TOKEN"
CHAT_ID = "SEU_ID/YOUR_CHAT_ID"

def criar_sessao_com_retry():
    """Cria uma sessão com retry automático"""
    session = requests.Session()
    
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["POST", "GET"]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    
    return session

def enviar_mensagem(texto):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    
    payload = {
        "chat_id": CHAT_ID,
        "text": texto
    }
    
    session = criar_sessao_com_retry()
    
    try:
        # Tenta com verify=True primeiro
        response = session.post(url, json=payload, timeout=15, verify=True)
        
        if response.status_code == 200:
            return True
        else:
            # Se falhar, tenta com verify=False
            response = session.post(url, json=payload, timeout=15, verify=False)
            return response.status_code == 200
            
    except requests.exceptions.SSLError:
        # Se SSL falhar, tenta sem verificação
        try:
            response = session.post(url, json=payload, timeout=15, verify=False)
            return response.status_code == 200
        except Exception:
            return False
            
    except Exception:
        return False
