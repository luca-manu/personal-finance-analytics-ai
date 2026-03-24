import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import logging
import warnings
import os

os.environ["WDM_LOG"] = "0"
warnings.filterwarnings("ignore", category=ResourceWarning)

logger = logging.getLogger(__name__)

# =========================
# TIMEOUT CONFIGURÁVEL
# =========================

TIMEOUT_ATIVO = 8    # segundos para carregar cada ativo
PAUSA_ENTRE   = 1    # segundos de pausa entre ativos
MAX_TENTATIVAS = 2   # tentativas antes de usar fallback da planilha

# =========================
# URL POR TIPO DE ATIVO
# =========================

def montar_url(ticker, tipo):
    tipo   = tipo.upper()
    ticker = ticker.lower()
    if tipo == "FII":
        return f"https://statusinvest.com.br/fundos-imobiliarios/{ticker}"
    elif tipo == "ETF":
        return f"https://statusinvest.com.br/etfs/{ticker}"
    elif tipo == "BDR":
        return f"https://statusinvest.com.br/bdrs/{ticker}"
    else:
        return f"https://statusinvest.com.br/acoes/{ticker}"

# =========================
# INICIAR CHROME (sessão única)
# =========================

def iniciar_driver():
    options = uc.ChromeOptions()
    options.add_argument("--window-position=-32000,-32000")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    driver = uc.Chrome(options=options)
    logger.info("✅ Chrome iniciado")
    return driver

# =========================
# BUSCAR INDICADORES DE UM ATIVO
# Com retry automático em caso de timeout
# =========================

def buscar_indicadores(driver, ticker, tipo="ACAO", tentativa=1):
    resultado = {"DY_12M": None, "PL": None}

    try:
        url = montar_url(ticker, tipo)
        if tentativa == 1:
            logger.info(f"Buscando {ticker} ({tipo}) — {url}")
        else:
            logger.info(f"  🔄 {ticker} — tentativa {tentativa}/{MAX_TENTATIVAS}")
            print(f"  🔄 {ticker} — tentativa {tentativa}/{MAX_TENTATIVAS}")

        driver.get(url)

        wait = WebDriverWait(driver, TIMEOUT_ATIVO)
        wait.until(EC.presence_of_element_located((
            By.XPATH,
            "//div[@title='Dividend Yield com base nos últimos 12 meses']//strong[@class='value']"
        )))

        time.sleep(1)

        # DY
        try:
            el = driver.find_element(
                By.XPATH,
                "//div[@title='Dividend Yield com base nos últimos 12 meses']//strong[@class='value']"
            )
            dy_raw = el.text.strip().replace(",", ".")
            resultado["DY_12M"] = float(dy_raw)
        except Exception:
            resultado["DY_12M"] = None

        # P/L — não existe para FIIs e ETFs
        if tipo.upper() not in ["FII", "ETF"]:
            try:
                el = driver.find_element(
                    By.XPATH,
                    "//div[@title='Dá uma ideia do quanto o mercado está disposto a pagar pelos lucros da empresa.']//div[contains(@class,'pr-xs-2')]"
                )
                pl_raw = el.text.strip().split("\n")[0].split(" ")[0].replace(",", ".")
                resultado["PL"] = float(pl_raw)
            except Exception:
                resultado["PL"] = None

        logger.info(f"  ✅ {ticker} — DY: {resultado['DY_12M']} | P/L: {resultado['PL']}")
        print(f"  ✅ {ticker} — DY: {resultado['DY_12M']} | P/L: {resultado['PL']}")

    except Exception as e:
        if tentativa < MAX_TENTATIVAS:
            logger.warning(f"  ⚠️ {ticker} timeout na tentativa {tentativa} — tentando novamente...")
            print(f"  ⚠️ {ticker} timeout — tentando novamente...")
            time.sleep(2)
            return buscar_indicadores(driver, ticker, tipo, tentativa + 1)
        else:
            logger.warning(f"  ❌ {ticker} falhou nas {MAX_TENTATIVAS} tentativas — usando dado da planilha.")
            print(f"  ❌ {ticker} falhou nas {MAX_TENTATIVAS} tentativas — usando planilha.")

    return resultado

# =========================
# BUSCAR TODOS OS ATIVOS DA CARTEIRA
# =========================

def atualizar_indicadores(df):
    logger.info("=" * 60)
    logger.info("INICIANDO BUSCA NO STATUS INVEST")
    logger.info("=" * 60)

    driver   = iniciar_driver()
    sucessos = 0
    falhas   = 0

    try:
        for idx, row in df.iterrows():
            ticker = row["ATIVO"]
            tipo   = str(row.get("TIPO", "ACAO")).upper()

            # ETFs não têm DY — pula
            if tipo == "ETF":
                logger.info(f"  ⏭️ {ticker} (ETF) — sem DY, pulando")
                print(f"  ⏭️ {ticker} (ETF) — sem DY, pulando")
                continue

            indicadores = buscar_indicadores(driver, ticker, tipo)

            if indicadores["DY_12M"] is not None:
                df.at[idx, "DY_12M"] = indicadores["DY_12M"]
                sucessos += 1
            else:
                falhas += 1

            if indicadores["PL"] is not None:
                df.at[idx, "PL"] = indicadores["PL"]

            time.sleep(PAUSA_ENTRE)

    except Exception as e:
        logger.error(f"Erro geral no Status Invest: {e}")

    finally:
        try:
            driver.quit()
        except Exception:
            pass
        try:
            import gc
            gc.collect()
        except Exception:
            pass
        logger.info("✅ Chrome encerrado")

    logger.info(f"Resultado: {sucessos} sucessos | {falhas} falhas")
    logger.info("=" * 60)
    logger.info("BUSCA STATUS INVEST CONCLUÍDA")
    logger.info("=" * 60)

    return df