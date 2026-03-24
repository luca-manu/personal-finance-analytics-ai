import warnings
warnings.filterwarnings("ignore")
import os
import sys
sys.stderr = open(os.devnull, 'w')
import pandas as pd
import yfinance as yf
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date, timedelta
import logging

# =========================
# LOGGING
# =========================

log_file = "main.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)

logger.info("=" * 60)
logger.info("INICIANDO MAIN.PY")
logger.info(f"Hora: {datetime.now()}")
logger.info("=" * 60)

# =========================
# CONFIG
# =========================

NOME_PLANILHA = "NOME_DA_PLANILHA"
ABA_CARTEIRA  = "CARTEIRA_PLANILHA"
ABA_SAIDA     = "BASE_PLANILHA"
ABA_FORWARD   = "TESTE_PLANILHA"

USAR_IA = False

# =========================
# DY ALVO POR TIPO DE ATIVO
# TETO = dividendo_anual / DY_ALVO
# =========================

DY_ALVO = {
    "FII":  0.09,   # 9%  — benchmark ajustado para Selic em queda
    "ACAO": 0.07,   # 7%  — margem competitiva vs Selic projetada 12%
}

DY_ALVO_PADRAO = 0.05

# Tipos que NÃO usam DY no score nem no teto — avaliados pela média 52 semanas
TIPOS_SEM_DY = {"BDR", "ETF"}

# =========================
# LIMITE SETORIAL
# Se um setor ultrapassar esse % da carteira,
# os ativos desse setor recebem penalização no score
# =========================

LIMITE_SETOR_PCT   = 35.0   # % máximo por setor
PENALIZACAO_SETOR  = 5.0    # pontos descontados do score

# =========================
# CONEXÃO GOOGLE SHEETS
# =========================

logger.info("Conectando ao Google Sheets...")

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

# Configuração:
# Para executar este projeto, é necessário configurar acesso ao Google Sheets
# via credenciais de serviço (credenciais.json).

creds    = Credentials.from_service_account_file("credenciais.json", scopes=scope)
client   = gspread.authorize(creds)
planilha = client.open(NOME_PLANILHA)

aba_carteira = planilha.worksheet(ABA_CARTEIRA)
dados        = aba_carteira.get_all_records()
df           = pd.DataFrame(dados)

# Filtrar linhas inválidas
df = df[df["ATIVO"].astype(str).str.strip() != ""]
df = df[~df["ATIVO"].astype(str).str.upper().isin(["ATIVO", "N/A", "NONE"])]
df = df.reset_index(drop=True)

logger.info(f"✅ {len(df)} ativos carregados")

# =========================
# CONVERSÃO NUMÉRICA ROBUSTA
# =========================

for col in ["QUANTIDADE", "PRECO_MEDIO", "PATRIMONIO_ALVO_PCT"]:
    df[col] = (
        df[col]
        .astype(str)
        .str.replace(",", ".")
        .str.replace("%", "")
    )
    df[col] = pd.to_numeric(df[col], errors="coerce")

# Corrige PRECO_MEDIO que veio multiplicado por 100 pelo Sheets
df["PRECO_MEDIO"] = df["PRECO_MEDIO"].apply(
    lambda x: round(x / 100, 2) if pd.notna(x) and x > 100 else x
)

# Garante colunas fundamentalistas
for col in ["DY_12M", "PL"]:
    if col in df.columns:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace(",", ".")
            .str.replace("%", "")
        )
        df[col] = pd.to_numeric(df[col], errors="coerce")
    else:
        df[col] = None

# Corrige DY_12M multiplicado por 100 pelo Sheets
df["DY_12M"] = df["DY_12M"].apply(
    lambda x: round(x / 100, 4) if pd.notna(x) and x > 100 else x
)

if "FREQ_DIVIDENDO" not in df.columns:
    df["FREQ_DIVIDENDO"] = "nenhum"

logger.info("✅ Conversão numérica OK")

# =========================
# STATUS INVEST — ATUALIZA DY E PL AUTOMATICAMENTE
# =========================

logger.info("Buscando indicadores no Status Invest...")

try:
    from status_invest import atualizar_indicadores
    df = atualizar_indicadores(df)
    logger.info("✅ Status Invest OK")
except Exception as e:
    logger.warning(f"⚠️ Status Invest falhou — usando dados da planilha: {e}")

# =========================
# DADOS DE MERCADO (yFinance)
# =========================

logger.info("Buscando preços no yFinance...")

def pegar_dados_ativo(ativo):
    try:
        ticker = yf.Ticker(f"{ativo}.SA")
        hist   = ticker.history(period="1y")

        if hist.empty or len(hist) < 2:
            return None, None, None, None, None

        preco_hoje  = round(hist["Close"].iloc[-1], 2)
        preco_ontem = round(hist["Close"].iloc[-2], 2)
        variacao    = round(((preco_hoje - preco_ontem) / preco_ontem) * 100, 2)
        media_52s   = round(hist["Close"].mean(), 2)

        # Volatilidade anualizada — desvio padrão dos retornos diários * √252
        retornos_diarios = hist["Close"].pct_change().dropna()
        volatilidade     = round(retornos_diarios.std() * (252 ** 0.5) * 100, 2)

        # Drawdown máximo — maior queda do pico ao fundo
        pico      = hist["Close"].cummax()
        drawdown  = ((hist["Close"] - pico) / pico * 100).min()
        drawdown  = round(drawdown, 2)

        return preco_hoje, variacao, media_52s, volatilidade, drawdown

    except:
        return None, None, None, None, None

precos       = []
variacoes    = []
medias_52s   = []
volatilidades = []
drawdowns    = []

for ativo in df["ATIVO"]:
    preco, variacao, media, vol, dd = pegar_dados_ativo(ativo)
    precos.append(preco)
    variacoes.append(variacao)
    medias_52s.append(media)
    volatilidades.append(vol)
    drawdowns.append(dd)

df["PRECO_HOJE"]       = precos
df["VARIACAO_DIA_PCT"] = variacoes
df["MEDIA_52S"]        = medias_52s
df["VOLATILIDADE"]     = volatilidades
df["DRAWDOWN_MAX"]     = drawdowns

logger.info("✅ Preços atualizados")

# =========================
# CÁLCULOS
# =========================

df["INVESTIMENTO_INICIAL"] = df["QUANTIDADE"] * df["PRECO_MEDIO"]
df["VALOR_ATUAL"]          = df["QUANTIDADE"] * df["PRECO_HOJE"]

df["RETORNO_PCT"] = (
    (df["VALOR_ATUAL"] - df["INVESTIMENTO_INICIAL"])
    / df["INVESTIMENTO_INICIAL"]
) * 100

patrimonio_total = df["VALOR_ATUAL"].sum()

# Proteção contra divisão por zero — mercado fechado ou sem preços
if patrimonio_total == 0 or pd.isna(patrimonio_total):
    logger.warning("⚠️ Patrimônio total zerado — mercado fechado ou sem preços disponíveis")
    print("\n⚠️ Mercado fechado ou sem preços disponíveis. Tente novamente quando o mercado abrir.")
    import sys
    sys.exit(0)

df["PESO_REAL_PCT"] = (df["VALOR_ATUAL"] / patrimonio_total) * 100
df["DIF_ALVO_PCT"]  = df["PESO_REAL_PCT"] - df["PATRIMONIO_ALVO_PCT"]

for col in ["RETORNO_PCT", "DIF_ALVO_PCT", "VARIACAO_DIA_PCT"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# =========================
# STATUS ALOCAÇÃO
# =========================

def status_alocacao(dif):
    if dif > 1:
        return "ACIMA_DO_ALVO"
    elif dif < -1:
        return "ABAIXO_DO_ALVO"
    else:
        return "DENTRO_DO_ALVO"

df["STATUS_ALOCACAO"] = df["DIF_ALVO_PCT"].apply(status_alocacao)

# =========================
# PESO POR SETOR
# Calcula concentração de cada setor para penalização no score
# =========================

peso_por_setor = (
    df.groupby("SETOR")["PESO_REAL_PCT"]
    .sum()
    .to_dict()
)

setores_concentrados = {
    setor for setor, peso in peso_por_setor.items()
    if peso > LIMITE_SETOR_PCT
}

if setores_concentrados:
    for setor in setores_concentrados:
        logger.info(f"⚠️ Setor concentrado: {setor} ({peso_por_setor[setor]:.1f}%) — penalização de -{PENALIZACAO_SETOR} pts no score")

# =========================
# CÁLCULO DO TETO
# =========================

def calcular_teto(row):
    tipo       = str(row.get("TIPO", "ACAO")).upper()
    dy_12m     = row.get("DY_12M", None)
    preco_hoje = row.get("PRECO_HOJE", None)
    freq       = str(row.get("FREQ_DIVIDENDO", "nenhum")).lower()
    media_52s  = row.get("MEDIA_52S", None)

    if tipo in TIPOS_SEM_DY:
        return media_52s if pd.notna(media_52s) else None

    tem_dividendo = freq not in ["nenhum", "none", "", "nan"]

    if tem_dividendo and pd.notna(dy_12m) and pd.notna(preco_hoje) and preco_hoje > 0:
        dy_alvo         = DY_ALVO.get(tipo, DY_ALVO_PADRAO)
        dividendo_anual = (dy_12m / 100) * preco_hoje
        teto            = dividendo_anual / dy_alvo
        return round(teto, 2)

    if pd.notna(media_52s):
        return media_52s

    return None

df["TETO_CALCULADO"] = df.apply(calcular_teto, axis=1)

# =========================
# DESCONTO VS TETO
# =========================

def calcular_desconto_teto(row):
    teto  = row.get("TETO_CALCULADO", None)
    preco = row.get("PRECO_HOJE", None)
    if pd.notna(teto) and pd.notna(preco) and teto > 0:
        return round(((teto - preco) / teto) * 100, 2)
    return 0.0

df["DESCONTO_TETO_PCT"] = df.apply(calcular_desconto_teto, axis=1)

# =========================
# SCORE DE OPORTUNIDADE (0–100)
# Com penalização setorial
# =========================

def calcular_score(row):
    tipo     = str(row.get("TIPO", "ACAO")).upper()
    setor    = str(row.get("SETOR", "")).strip()
    dy_12m   = row.get("DY_12M", None)
    variacao = row.get("VARIACAO_DIA_PCT", 0)
    dif_alvo = row.get("DIF_ALVO_PCT", 0)
    retorno  = row.get("RETORNO_PCT", 0)
    desconto = row.get("DESCONTO_TETO_PCT", 0)

    if pd.isna(variacao): variacao = 0
    if pd.isna(dif_alvo): dif_alvo = 0
    if pd.isna(retorno):  retorno  = 0
    if pd.isna(desconto): desconto = 0

    desconto_c = max(-30, min(desconto, 30))
    f_desconto = ((desconto_c + 30) / 60) * 40

    if tipo in TIPOS_SEM_DY:
        f_dy = 0
        f_desconto = ((desconto_c + 30) / 60) * 65
    else:
        dy_alvo_tipo = DY_ALVO.get(tipo, DY_ALVO_PADRAO) * 100
        if pd.notna(dy_12m) and dy_12m > 0:
            ratio_dy = min(dy_12m / dy_alvo_tipo, 2.0)
            f_dy = (ratio_dy / 2.0) * 25
        else:
            f_dy = 0

    dif_c      = max(-20, min(dif_alvo, 20))
    f_alvo     = ((-dif_c + 20) / 40) * 20

    variacao_c = max(-10, min(variacao, 10))
    f_variacao = ((-variacao_c + 10) / 20) * 10

    retorno_c = max(-50, min(retorno, 100))
    f_retorno = ((100 - retorno_c) / 150) * 5
    f_retorno = max(0, min(f_retorno, 5))

    score = f_desconto + f_dy + f_alvo + f_variacao + f_retorno

    # Penalização setorial — setor concentrado acima do limite
    if setor in setores_concentrados:
        score -= PENALIZACAO_SETOR

    return round(max(0, min(score, 100)), 1)

df["SCORE_OPORTUNIDADE"] = df.apply(calcular_score, axis=1)

# =========================
# CAMPOS FUTUROS IA
# =========================

df["SCORE_DIA"]         = 0
df["CLASSIFICACAO_DIA"] = 0

# =========================
# ALERTAS DE MERCADO
# =========================

alertas = []

for _, row in df.iterrows():
    ativo    = row["ATIVO"]
    variacao = row["VARIACAO_DIA_PCT"]
    retorno  = row["RETORNO_PCT"]
    desconto = row["DESCONTO_TETO_PCT"]
    setor    = str(row.get("SETOR", "")).strip()

    if pd.notna(variacao) and variacao <= -8:
        alertas.append(f"🚨 {ativo} caiu {variacao:.2f}% hoje")

    if pd.notna(variacao) and variacao >= 8:
        alertas.append(f"🚀 {ativo} subiu {variacao:.2f}% hoje")

    if pd.notna(retorno) and retorno >= 30:
        alertas.append(f"🏆 {ativo} atingiu {retorno:.2f}% de lucro total")

    if pd.notna(desconto) and desconto >= 15:
        alertas.append(f"🎯 {ativo} está {desconto:.1f}% abaixo do teto calculado")

    # Alertas de risco
    vol = row.get("VOLATILIDADE", None)
    dd  = row.get("DRAWDOWN_MAX", None)
    if pd.notna(vol) and vol >= 40:
        alertas.append(f"⚡ {ativo} volatilidade alta: {vol:.1f}% ao ano")

# Alerta de concentração setorial
for setor in setores_concentrados:
    alertas.append(f"⚠️ Setor {setor} concentrado em {peso_por_setor[setor]:.1f}% — acima do limite de {LIMITE_SETOR_PCT}%")

if alertas:
    print("\nALERTAS DE MERCADO\n")
    for alerta in alertas:
        print(alerta)
        logger.info(alerta)
else:
    print("\nNenhum alerta relevante hoje.")

# =========================
# ORGANIZAÇÃO FINAL
# =========================

ordem = [
    "ATIVO", "TIPO", "SETOR", "QUANTIDADE", "PRECO_HOJE",
    "VALOR_ATUAL", "PESO_REAL_PCT", "PATRIMONIO_ALVO_PCT",
    "DIF_ALVO_PCT", "STATUS_ALOCACAO", "SCORE_OPORTUNIDADE",
    "VARIACAO_DIA_PCT", "RETORNO_PCT", "TETO_CALCULADO",
    "DESCONTO_TETO_PCT", "DY_12M", "PL", "FREQ_DIVIDENDO",
    "VOLATILIDADE", "DRAWDOWN_MAX",
    "SCORE_DIA", "CLASSIFICACAO_DIA"
]

ordem = [c for c in ordem if c in df.columns]
df    = df[ordem]

# =========================
# HISTÓRICO DA CARTEIRA
# =========================

patrimonio_total = df["VALOR_ATUAL"].sum()
aba_historico    = planilha.worksheet("HISTORICO_CARTEIRA")
nova_linha       = [str(date.today()), round(patrimonio_total, 2)]
aba_historico.append_row(nova_linha)
print("Histórico da carteira atualizado.")
logger.info(f"✅ Patrimônio total: R$ {patrimonio_total:.2f}")

# =========================
# SALVAR NO GOOGLE SHEETS
# =========================

try:
    aba_saida = planilha.worksheet(ABA_SAIDA)
except:
    aba_saida = planilha.add_worksheet(title=ABA_SAIDA, rows=100, cols=25)

aba_saida.clear()

df_salvar = df.copy()

for col in df_salvar.select_dtypes(include="float").columns:
    df_salvar[col] = df_salvar[col].apply(
        lambda x: str(round(x, 2)) if pd.notna(x) else ""
    )

df_salvar = df_salvar.fillna("")
aba_saida.update([df_salvar.columns.values.tolist()] + df_salvar.values.tolist())

print("Base consolidada atualizada no Google Sheets.")
logger.info("✅ BASE_CONSOLIDADA atualizada")

# =========================
# FORWARD TESTING
# Salva top 3 scores do dia e atualiza preços de 7, 30 e 90 dias
# =========================

logger.info("Atualizando Forward Testing...")

try:
    aba_forward = planilha.worksheet(ABA_FORWARD)

    def pegar_ibov():
        try:
            ibov = yf.Ticker("^BVSP")
            hist = ibov.history(period="2d")
            return round(hist["Close"].iloc[-1], 2)
        except:
            return None

    ibov_hoje = pegar_ibov()

    top3     = df.sort_values("SCORE_OPORTUNIDADE", ascending=False).head(3).reset_index(drop=True)
    hoje_str = str(date.today())

    novas_linhas = []
    for rank, (_, row) in enumerate(top3.iterrows(), start=1):
        nova_linha = [
            hoje_str,
            row["ATIVO"],
            row["SCORE_OPORTUNIDADE"],
            rank,
            row["PRECO_HOJE"],
            "", "", "",
            "", "", "",
            ibov_hoje if ibov_hoje else "",
            "", "", "",
            "", "", ""
        ]
        novas_linhas.append(nova_linha)

    dados_forward = aba_forward.get_all_values()
    if not dados_forward or dados_forward[0][0] != "DATA":
        cabecalho = [
            "DATA", "ATIVO", "SCORE", "RANK", "PRECO_ENTRADA",
            "PRECO_7D", "PRECO_30D", "PRECO_90D",
            "RETORNO_7D", "RETORNO_30D", "RETORNO_90D",
            "IBOV_ENTRADA", "IBOV_7D", "IBOV_30D", "IBOV_90D",
            "ALPHA_7D", "ALPHA_30D", "ALPHA_90D"
        ]
        aba_forward.append_row(cabecalho)
        dados_forward = aba_forward.get_all_values()

    datas_existentes = [row[0] for row in dados_forward[1:] if row]
    if hoje_str in datas_existentes:
        logger.info("✅ Forward Testing — já registrado hoje, pulando")
        print("Forward Testing — já registrado hoje, pulando.")
    else:
        for linha in novas_linhas:
            aba_forward.append_row(linha)
        logger.info(f"✅ Forward Testing — top 3 salvo: {[r['ATIVO'] for _, r in top3.iterrows()]}")
        print(f"Forward Testing — top 3 salvo: {[r['ATIVO'] for _, r in top3.iterrows()]}")

    dados_forward = aba_forward.get_all_records()
    df_forward    = pd.DataFrame(dados_forward)

    if not df_forward.empty:
        hoje      = date.today()
        preco_map = dict(zip(df["ATIVO"], df["PRECO_HOJE"]))

        for idx, row in df_forward.iterrows():
            try:
                data_entrada  = datetime.strptime(str(row["DATA"]), "%Y-%m-%d").date()
                ativo         = row["ATIVO"]
                preco_atual   = preco_map.get(ativo, None)

                if preco_atual is None:
                    continue

                preco_entrada = float(str(row["PRECO_ENTRADA"]).replace(",", ".")) if row["PRECO_ENTRADA"] else None
                dias          = (hoje - data_entrada).days
                sheet_row     = idx + 2

                def retorno(entrada, atual):
                    if entrada and entrada > 0:
                        return round(((atual - entrada) / entrada) * 100, 2)
                    return ""

                if dias >= 7 and not row.get("PRECO_7D"):
                    aba_forward.update_cell(sheet_row, 6, preco_atual)
                    aba_forward.update_cell(sheet_row, 9, retorno(preco_entrada, preco_atual))
                    if ibov_hoje:
                        aba_forward.update_cell(sheet_row, 13, ibov_hoje)

                if dias >= 30 and not row.get("PRECO_30D"):
                    aba_forward.update_cell(sheet_row, 7, preco_atual)
                    aba_forward.update_cell(sheet_row, 10, retorno(preco_entrada, preco_atual))
                    if ibov_hoje:
                        aba_forward.update_cell(sheet_row, 14, ibov_hoje)

                if dias >= 90 and not row.get("PRECO_90D"):
                    aba_forward.update_cell(sheet_row, 8, preco_atual)
                    aba_forward.update_cell(sheet_row, 11, retorno(preco_entrada, preco_atual))
                    if ibov_hoje:
                        aba_forward.update_cell(sheet_row, 15, ibov_hoje)

            except Exception as e:
                logger.warning(f"⚠️ Erro ao atualizar forward row {idx}: {e}")
                continue

    logger.info("✅ Forward Testing atualizado")

except Exception as e:
    logger.warning(f"⚠️ Forward Testing falhou — não crítico: {e}")

logger.info("=" * 60)
logger.info("MAIN.PY CONCLUÍDO COM SUCESSO")
logger.info("=" * 60)
