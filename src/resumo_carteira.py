import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import yfinance as yf
import feedparser
from datetime import datetime, timezone
import logging
import os
import sys
import traceback

# =========================
# CONFIGURAR LOGGING
# =========================

log_file = os.path.join(os.path.dirname(__file__), 'resumo_carteira.log')

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

logger.info("=" * 60)
logger.info("INICIANDO RESUMO_CARTEIRA.PY")
logger.info(f"Hora: {datetime.now()}")
logger.info(f"Python: {sys.executable}")
logger.info(f"Diretório: {os.getcwd()}")
logger.info("=" * 60)

# =========================
# CONFIG
# =========================

NOME_PLANILHA = "NOME_DA_PLANILHA"
ABA_BASE      = "BASE_PLANILHA"
ABA_RELATORIO = "RELATORIO_PLANILHA"

# Limites do radar (ajustáveis)
LIMITE_VARIACAO_DIA  = 3.0
LIMITE_VENDA_PARCIAL = 35.0
LIMITE_RECOMPRA      = 8.0
LIMITE_DESCONTO_TETO = 15.0

# Limites de risco
LIMITE_VOLATILIDADE  = 40.0   # % ao ano — acima disso é considerado alto risco
LIMITE_DRAWDOWN      = -25.0  # % — abaixo disso é considerado drawdown severo

# Tipos que não entram no DY médio
TIPOS_SEM_DY = {"BDR", "ETF"}

# =========================
# PALAVRAS RELEVANTES (ANTI-SPAM)
# =========================

PALAVRAS_RELEVANTES_EN = [
    "dividend", "earnings", "profit", "acquisition", "merger",
    "rating", "upgrade", "downgrade", "interest", "china",
    "oil", "credit", "inflation", "revenue", "guidance"
]

PALAVRAS_RELEVANTES_PT = [
    "dividendo", "lucro", "resultado", "aquisição", "fusão",
    "rating", "rebaixamento", "elevação", "juros", "inflação",
    "receita", "guidance", "balanço", "prejuízo", "crescimento",
    "queda", "alta", "baixa", "venda", "compra"
]

# =========================
# FUNÇÃO BUSCAR NOTÍCIAS YFINANCE
# =========================

def buscar_noticias_yf(ativo):
    try:
        ticker   = yf.Ticker(f"{ativo}.SA")
        noticias = ticker.news
        relevantes = []

        for n in noticias:
            content   = n.get("content", {})
            titulo    = content.get("title", "")
            pub_date  = content.get("pubDate", None)
            click_url = content.get("clickThroughUrl", {})
            link      = click_url.get("url", "") if click_url else ""

            if not pub_date:
                continue

            data_noticia = datetime.strptime(pub_date, "%Y-%m-%dT%H:%M:%SZ")
            data_noticia = data_noticia.replace(tzinfo=timezone.utc)
            agora = datetime.now(timezone.utc)
            horas = (agora - data_noticia).total_seconds() / 3600

            if horas > 24:
                continue

            if any(p in titulo.lower() for p in PALAVRAS_RELEVANTES_EN):
                relevantes.append({"titulo": titulo, "link": link})

        return relevantes[:2]

    except Exception as e:
        logger.warning(f"Erro ao buscar notícias yfinance para {ativo}: {e}")
        return []

# =========================
# FUNÇÃO BUSCAR NOTÍCIAS GOOGLE NEWS
# =========================

def buscar_noticias_google(ativo):
    try:
        url  = f"https://news.google.com/rss/search?q={ativo}+acao+bolsa&hl=pt-BR&gl=BR&ceid=BR:pt-419"
        feed = feedparser.parse(url)
        relevantes = []
        agora = datetime.now(timezone.utc)

        for entry in feed.entries:
            titulo    = entry.get("title", "")
            link      = entry.get("link", "")
            published = entry.get("published_parsed", None)

            if published is None:
                continue

            data_noticia = datetime(*published[:6], tzinfo=timezone.utc)
            horas = (agora - data_noticia).total_seconds() / 3600

            if horas > 24:
                continue

            if any(p in titulo.lower() for p in PALAVRAS_RELEVANTES_PT):
                relevantes.append({"titulo": titulo, "link": link})

        return relevantes[:2]

    except Exception as e:
        logger.warning(f"Erro ao buscar notícias Google para {ativo}: {e}")
        return []

# =========================
# MAIN FUNCTION
# =========================

def main():
    try:
        logger.info("Iniciando processamento...")

        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]

        creds    = Credentials.from_service_account_file("credenciais.json", scopes=scope)
        client   = gspread.authorize(creds)
        planilha = client.open(NOME_PLANILHA)
        aba_base = planilha.worksheet(ABA_BASE)

        logger.info("✅ Conexão Google Sheets OK")

        dados = aba_base.get_all_records()
        df    = pd.DataFrame(dados)

        df = df[df["ATIVO"].astype(str).str.strip() != ""]
        df = df[~df["ATIVO"].astype(str).str.upper().isin(["ATIVO", "N/A", "NONE"])]
        df = df.reset_index(drop=True)

        logger.info(f"✅ Dados carregados: {len(df)} ativos")

        # Normalização numérica
        colunas_numericas = [
            "PESO_REAL_PCT", "PATRIMONIO_ALVO_PCT", "DIF_ALVO_PCT",
            "SCORE_OPORTUNIDADE", "VARIACAO_DIA_PCT", "RETORNO_PCT",
            "TETO_CALCULADO", "DESCONTO_TETO_PCT", "DY_12M", "PL",
            "VOLATILIDADE", "DRAWDOWN_MAX"
        ]

        for col in colunas_numericas:
            if col in df.columns:
                df[col] = (
                    df[col]
                    .astype(str)
                    .str.replace(",", ".", regex=False)
                    .pipe(pd.to_numeric, errors="coerce")
                )

        logger.info("✅ Normalização OK")

        # =========================
        # MÉTRICAS
        # =========================

        total_ativos = len(df)

        acima  = df[df["STATUS_ALOCACAO"] == "ACIMA_DO_ALVO"]
        dentro = df[df["STATUS_ALOCACAO"] == "DENTRO_DO_ALVO"]
        abaixo = df[df["STATUS_ALOCACAO"] == "ABAIXO_DO_ALVO"]

        top_acima  = acima.sort_values("DIF_ALVO_PCT", ascending=False).head(3)
        top_abaixo = abaixo.sort_values("DIF_ALVO_PCT").head(3)

        setor_dominante = (
            df.groupby("SETOR")["PESO_REAL_PCT"]
            .sum()
            .sort_values(ascending=False)
            .idxmax()
        )

        peso_setor = (
            df.groupby("SETOR")["PESO_REAL_PCT"]
            .sum()
            .max()
        )

        top_oportunidades = df.sort_values(
            by="SCORE_OPORTUNIDADE", ascending=False
        ).head(3)

        # DY médio ponderado
        dy_geral       = 0.0
        dy_pagadores   = 0.0
        peso_total     = df["PESO_REAL_PCT"].sum()
        peso_pagadores = 0.0

        for _, row in df.iterrows():
            tipo  = str(row.get("TIPO", "")).upper()
            dy    = pd.to_numeric(row.get("DY_12M", None), errors="coerce")
            peso  = pd.to_numeric(row.get("PESO_REAL_PCT", 0), errors="coerce")

            if pd.isna(peso): peso = 0

            if pd.notna(dy) and tipo not in TIPOS_SEM_DY:
                dy_geral += (peso / peso_total) * dy

            if pd.notna(dy) and dy > 0 and tipo not in TIPOS_SEM_DY:
                peso_pagadores += peso
                dy_pagadores   += peso * dy

        dy_pagadores_medio = (dy_pagadores / peso_pagadores) if peso_pagadores > 0 else 0

        # Top descontos
        if "DESCONTO_TETO_PCT" in df.columns:
            top_desconto = (
                df[df["DESCONTO_TETO_PCT"] > 0]
                .sort_values("DESCONTO_TETO_PCT", ascending=False)
                .head(3)
            )
        else:
            top_desconto = pd.DataFrame()

        # =========================
        # RADAR DE RISCO
        # =========================

        risco_itens = []

        for _, row in df.iterrows():
            ativo = row["ATIVO"]
            vol   = pd.to_numeric(row.get("VOLATILIDADE", None), errors="coerce")
            dd    = pd.to_numeric(row.get("DRAWDOWN_MAX", None), errors="coerce")

            alertas_risco = []

            if pd.notna(vol) and vol >= LIMITE_VOLATILIDADE:
                alertas_risco.append(f"⚡ Volatilidade: {vol:.1f}%/ano")

            if pd.notna(dd) and dd <= LIMITE_DRAWDOWN:
                alertas_risco.append(f"📉 Drawdown máx: {dd:.1f}%")

            if alertas_risco:
                risco_itens.append(f"• {ativo} — " + " | ".join(alertas_risco))

        if risco_itens:
            bloco_risco = "\n".join(risco_itens)
        else:
            bloco_risco = "✅ Nenhum ativo com risco elevado detectado."

        logger.info("✅ Métricas calculadas")

        # =========================
        # RADAR DE NOTÍCIAS
        # =========================

        noticias_por_ativo = {}

        for ativo in df["ATIVO"].tolist():
            noticias_en = buscar_noticias_yf(ativo)
            noticias_pt = buscar_noticias_google(ativo)
            if noticias_en or noticias_pt:
                noticias_por_ativo[ativo] = {
                    "en": noticias_en,
                    "pt": noticias_pt
                }

        noticias_texto = []
        for ativo, fontes in noticias_por_ativo.items():
            for n in fontes["en"]:
                noticias_texto.append(f"🌎 {ativo}\n{n['titulo']}\n{n['link']}")
            for n in fontes["pt"]:
                noticias_texto.append(f"🇧🇷 {ativo}\n{n['titulo']}\n{n['link']}")

        bloco_noticias = (
            "\n\n".join(noticias_texto)
            if noticias_texto
            else "Nenhuma notícia relevante nas últimas 24h."
        )

        # =========================
        # RADAR DA CARTEIRA
        # =========================

        radar_itens = []

        for _, row in df.iterrows():
            ativo    = row["ATIVO"]
            variacao = pd.to_numeric(row.get("VARIACAO_DIA_PCT", None), errors="coerce")
            retorno  = pd.to_numeric(row.get("RETORNO_PCT", None), errors="coerce")
            desconto = pd.to_numeric(row.get("DESCONTO_TETO_PCT", None), errors="coerce")
            teto     = pd.to_numeric(row.get("TETO_CALCULADO", None), errors="coerce")

            alertas_ativo = []

            if pd.notna(variacao) and variacao <= -LIMITE_RECOMPRA:
                alertas_ativo.append(f"📉 Correção de {abs(variacao):.1f}% — oportunidade de recompra?")
            elif pd.notna(variacao) and abs(variacao) >= LIMITE_VARIACAO_DIA:
                if variacao > 0:
                    alertas_ativo.append(f"📈 Alta de {variacao:.1f}% no dia")
                else:
                    alertas_ativo.append(f"📉 Queda de {abs(variacao):.1f}% no dia")

            if pd.notna(retorno) and retorno >= LIMITE_VENDA_PARCIAL:
                alertas_ativo.append(f"🏆 Retorno total +{retorno:.1f}% — estudar venda parcial (10–15%)")

            if pd.notna(desconto) and pd.notna(teto) and desconto >= LIMITE_DESCONTO_TETO:
                alertas_ativo.append(f"🎯 {desconto:.1f}% abaixo do teto (R$ {teto:.2f})")

            if ativo in noticias_por_ativo:
                alertas_ativo.append("📰 Notícia relevante detectada")

            if alertas_ativo:
                radar_itens.append(f"*{ativo}*\n" + "\n".join(alertas_ativo))

        bloco_radar = (
            "\n\n".join(radar_itens)
            if radar_itens
            else "✅ Nenhum evento relevante detectado hoje."
        )

        # =========================
        # BLOCO OPORTUNIDADES
        # =========================

        linhas_oportunidade = []
        for _, row in top_oportunidades.iterrows():
            ativo    = row["ATIVO"]
            score    = int(row["SCORE_OPORTUNIDADE"])
            desconto = pd.to_numeric(row.get("DESCONTO_TETO_PCT", None), errors="coerce")
            dy       = pd.to_numeric(row.get("DY_12M", None), errors="coerce")
            tipo     = str(row.get("TIPO", "")).upper()

            linha = f"• {ativo} ⭐ {score}/100"
            if pd.notna(desconto) and desconto > 0:
                linha += f" | 🎯 {desconto:.1f}% abaixo do teto"
            if pd.notna(dy) and dy > 0 and tipo not in TIPOS_SEM_DY:
                linha += f" | 💰 DY {dy:.2f}%"
            linhas_oportunidade.append(linha)

        bloco_oportunidades = "\n".join(linhas_oportunidade)

        # =========================
        # BLOCO MAIORES DESCONTOS
        # =========================

        if not top_desconto.empty:
            linhas_desconto = []
            for _, row in top_desconto.iterrows():
                ativo    = row["ATIVO"]
                desconto = row["DESCONTO_TETO_PCT"]
                teto     = pd.to_numeric(row.get("TETO_CALCULADO", None), errors="coerce")
                teto_str = f"R$ {teto:.2f}" if pd.notna(teto) else "—"
                linhas_desconto.append(f"• {ativo} → {desconto:.1f}% abaixo do teto ({teto_str})")
            bloco_desconto = "\n".join(linhas_desconto)
        else:
            bloco_desconto = "Nenhum ativo abaixo do teto no momento."

        # =========================
        # RELATÓRIO UNIFICADO
        # =========================

        relatorio = f"""
🚨 RADAR DA CARTEIRA
{bloco_radar}

⚠️ RADAR DE RISCO
{bloco_risco}

📊 RESUMO DA CARTEIRA
Total de ativos: {total_ativos}

💰 DY Médio da Carteira
📈 Geral (todos os ativos): {dy_geral:.2f}%
💵 Apenas pagadores (ACAO/FII): {dy_pagadores_medio:.2f}%

⚖️ Distribuição da carteira
⬆️ Acima do alvo: {len(acima)}
✅ Dentro do alvo: {len(dentro)}
⬇️ Abaixo do alvo: {len(abaixo)}

📈 Ativos com participação acima do alvo
{chr(10).join([f"• {row['ATIVO']} (+{row['DIF_ALVO_PCT']:.2f}%)" for _, row in top_acima.iterrows()])}

📉 Ativos com participação abaixo do alvo
{chr(10).join([f"• {row['ATIVO']} ({row['DIF_ALVO_PCT']:.2f}%)" for _, row in top_abaixo.iterrows()])}

🏭 Setor dominante
{setor_dominante} ({peso_setor:.2f}% da carteira)

🎯 Melhores oportunidades de aporte
{bloco_oportunidades}

📉 Maiores descontos vs teto calculado
{bloco_desconto}

📰 Radar de Notícias
{bloco_noticias}

📅 Relatório gerado automaticamente
"""

        logger.info("✅ Relatório formatado")

        # Salvar no Sheets
        try:
            aba_relatorio = planilha.worksheet(ABA_RELATORIO)
        except:
            aba_relatorio = planilha.add_worksheet(title=ABA_RELATORIO, rows=20, cols=2)

        aba_relatorio.clear()
        aba_relatorio.update([["RELATORIO"], [relatorio]])

        logger.info("✅ Relatório salvo no Google Sheets")

        # Envio Telegram
        try:
            from telegram_sender import enviar_mensagem
            enviar_mensagem(relatorio)
            logger.info("✅ MENSAGEM ENVIADA AO TELEGRAM COM SUCESSO!")
        except ImportError:
            logger.error("❌ Erro: não conseguiu importar telegram_sender.py")
            raise
        except Exception as e:
            logger.error(f"❌ Erro ao enviar para Telegram: {str(e)}")
            logger.error(traceback.format_exc())
            raise

        logger.info("=" * 60)
        logger.info("SUCESSO! Relatório completo gerado e enviado.")
        logger.info("=" * 60)
        return True

    except Exception as e:
        logger.error("=" * 60)
        logger.error("ERRO GERAL NA EXECUÇÃO!")
        logger.error("=" * 60)
        logger.error(f"Erro: {str(e)}")
        logger.error(traceback.format_exc())
        logger.error("=" * 60)
        return False

if __name__ == "__main__":
    sucesso = main()
    sys.exit(0 if sucesso else 1)
