import requests
import logging
import os
from datetime import datetime
import urllib3
import socket

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

log_file = os.path.join(os.path.dirname(__file__), 'telegram_debug.log')

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

TOKEN = "SEU_TOKEN_TELEGRAM_BOT/YOUR_TELEGRAM_BOT_TOKEN"
CHAT_ID = "SEU_CHAT_ID/YOUR_CHAT_ID"

def testar_dns():
    """Testa se consegue resolver DNS do Telegram"""
    logger.info("=" * 60)
    logger.info("TESTANDO RESOLUCAO DNS")
    logger.info("=" * 60)
    
    try:
        ip = socket.gethostbyname('api.telegram.org')
        logger.info(f"DNS OK! IP do Telegram: {ip}")
        return True
    except Exception as e:
        logger.error(f"Erro ao resolver DNS: {e}")
        return False

def testar_conexao_basica():
    """Testa conexão TCP básica"""
    logger.info("=" * 60)
    logger.info("TESTANDO CONEXAO TCP")
    logger.info("=" * 60)
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        resultado = sock.connect_ex(('api.telegram.org', 443))
        sock.close()
        
        if resultado == 0:
            logger.info("Conexao TCP OK!")
            return True
        else:
            logger.error(f"Nao conseguiu conectar na porta 443: {resultado}")
            return False
    except Exception as e:
        logger.error(f"Erro na conexao TCP: {e}")
        return False

def testar_com_session():
    """Testa usando requests.Session com configuracoes customizadas"""
    logger.info("=" * 60)
    logger.info("TESTANDO COM SESSION CUSTOMIZADA")
    logger.info("=" * 60)
    
    try:
        session = requests.Session()
        session.headers.update({'User-Agent': 'Mozilla/5.0'})
        
        url = f"https://api.telegram.org/bot{TOKEN}/getMe"
        
        response = session.get(
            url, 
            timeout=10, 
            verify=False,
            allow_redirects=True
        )
        
        logger.info(f"Status: {response.status_code}")
        logger.info(f"Response: {response.text}")
        
        if response.status_code == 200:
            logger.info("Sucesso com Session!")
            return True
        else:
            logger.error(f"Falha: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"Erro: {str(e)}")
        return False

def testar_com_adapter():
    """Testa usando adapter customizado"""
    logger.info("=" * 60)
    logger.info("TESTANDO COM ADAPTER CUSTOMIZADO")
    logger.info("=" * 60)
    
    try:
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        session = requests.Session()
        
        retry = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=(500, 502, 504),
        )
        
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('https://', adapter)
        
        url = f"https://api.telegram.org/bot{TOKEN}/getMe"
        
        response = session.get(url, timeout=10, verify=False)
        
        logger.info(f"Status: {response.status_code}")
        logger.info(f"Response: {response.text}")
        
        if response.status_code == 200:
            logger.info("Sucesso com Adapter!")
            return True
        else:
            logger.error(f"Falha: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"Erro: {str(e)}")
        return False

def enviar_mensagem_session(texto):
    """Envia mensagem usando Session"""
    logger.info("=" * 60)
    logger.info("ENVIANDO MENSAGEM COM SESSION")
    logger.info("=" * 60)
    
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    
    payload = {
        "chat_id": CHAT_ID,
        "text": texto
    }
    
    logger.info(f"URL: {url}")
    logger.info(f"Chat ID: {CHAT_ID}")
    logger.info(f"Mensagem: {texto}")
    
    try:
        session = requests.Session()
        session.headers.update({'User-Agent': 'Mozilla/5.0'})
        
        response = session.post(
            url, 
            json=payload, 
            timeout=15, 
            verify=False
        )
        
        logger.info(f"Status Code: {response.status_code}")
        logger.debug(f"Response: {response.text}")
        
        if response.status_code == 200:
            logger.info("MENSAGEM ENVIADA COM SUCESSO!")
            return True
        else:
            logger.error(f"Falha ao enviar: {response.status_code}")
            logger.error(f"Detalhes: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Erro ao enviar: {str(e)}")
        return False

def main():
    logger.info("\n\n")
    logger.info("BOT TELEGRAM - TESTE AVANCADO")
    logger.info(f"Hora: {datetime.now()}")
    logger.info("\n")
    
    # Teste 1: DNS
    if not testar_dns():
        logger.error("Problema crítico: DNS não funciona!")
        return False
    
    # Teste 2: TCP
    if not testar_conexao_basica():
        logger.error("Problema crítico: Conexão TCP não funciona!")
        return False
    
    # Teste 3: Session customizada
    if testar_com_session():
        logger.info("\n>>> SUCESSO COM SESSION! <<<\n")
        
        # Tenta enviar mensagem
        mensagem = f"Bot OK! {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
        resultado = enviar_mensagem_session(mensagem)
        
        if resultado:
            logger.info("\nSUCESSO TOTAL!")
            return True
    
    # Teste 4: Com Adapter
    if testar_com_adapter():
        logger.info("\n>>> SUCESSO COM ADAPTER! <<<\n")
        
        # Tenta enviar mensagem
        mensagem = f"Bot OK! {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
        resultado = enviar_mensagem_session(mensagem)
        
        if resultado:
            logger.info("\nSUCESSO TOTAL!")
            return True
    
    logger.error("\nTodos os testes falharam!")
    return False

if __name__ == "__main__":
    main()