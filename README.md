# 📌 Financial Data Analysis with Python

End-to-end financial data pipeline designed to automate data collection, analysis, and decision support for personal investment management.

---

## ❗ Problem

Managing financial data manually can lead to inconsistencies, lack of visibility, and inefficient decision-making.

This project was created to automate financial data processing and generate structured insights for better investment decisions.

---

## 🚀 Solution

This project implements an automated pipeline that:

* Collects financial data from structured sources (Google Sheets)
* Cleans and standardizes the data
* Enriches data with external indicators (Status Invest / Yahoo Finance)
* Calculates financial metrics, risk indicators, and opportunity scores
* Generates structured reports
* Sends automated notifications via Telegram

---

## 🏗️ Architecture

Google Sheets → Data Processing (Pandas) → External Data (Scraping + APIs) → Analysis → Report Generation → Telegram Notification

---

## 🎯 Objective

Consolidate financial data into a structured data flow
Automate data processing and analysis tasks
Reduce manual effort and risk of inconsistencies
Support financial decisions based on reliable data

---

## ⚙️ Technologies

Python
Pandas
Process automation
Data pipeline structuring (ETL)
Web scraping (Selenium)
API integration (Telegram, Yahoo Finance)

---

## 🔄 Data Pipeline

The project follows a structured data processing workflow:

**Data Collection**
Importing financial data from structured sources (e.g., Google Sheets)

**Data Cleaning and Standardization**
Cleaning, organizing, and normalizing data using Python (Pandas)

**Transformation**
Structuring data for analysis (categorization, aggregation, adjustments)

**Analysis**
Generating indicators, risk metrics, and financial insights

**Output**
Producing reports and structured data for consumption and notification

---

## 📊 Example Output

Below is an example of the generated report:

![Example](./images/example.png)

---

## ⚙️ How to Run

1. Clone the repository
2. Install dependencies:
   `pip install -r requirements.txt`
3. Configure credentials:

   * Google Sheets API (`credenciais.json`)
   * Telegram Bot (TOKEN and CHAT_ID)
4. Run the pipeline:
   `python main.py`

---

## 🔒 Note

This project represents a portfolio-adapted version, focused on demonstrating technical structure, data pipeline design, and data analysis practices.

Sensitive information (credentials, tokens, and personal financial data) has been removed for security reasons.


<img width="25" height="18" src="https://github.com/user-attachments/assets/c4feb76b-6179-4d5b-a171-d2d1e793b79a" /> **pt-BR | # 📌 Análise de Dados Financeiros com Python** <img width="25" height="18" src="https://github.com/user-attachments/assets/c4feb76b-6179-4d5b-a171-d2d1e793b79a" />

Pipeline completo de dados financeiros desenvolvido para automatizar a coleta, análise e apoio à tomada de decisão em investimentos pessoais.

---

## ❗ Problema

Gerenciar dados financeiros manualmente pode gerar inconsistências, falta de visibilidade e decisões ineficientes.

Este projeto foi criado para automatizar o processamento de dados financeiros e gerar insights estruturados para uma melhor tomada de decisão.

---

## 🚀 Solução

Este projeto implementa um pipeline automatizado que:

* Coleta dados financeiros a partir de fontes estruturadas (Google Sheets)
* Realiza limpeza e padronização dos dados
* Enriquece os dados com informações externas (Status Invest / Yahoo Finance)
* Calcula métricas financeiras, indicadores de risco e oportunidades
* Gera relatórios estruturados
* Envia notificações automatizadas via Telegram

---

## 🏗️ Arquitetura

Google Sheets → Processamento de Dados (Pandas) → Dados Externos (Scraping + APIs) → Análise → Geração de Relatório → Notificação via Telegram

---

## 🎯 Objetivo

Consolidar dados financeiros em um fluxo estruturado
Automatizar processos de tratamento e análise de dados
Reduzir esforço manual e risco de inconsistências
Apoiar decisões financeiras com base em dados confiáveis

---

## ⚙️ Tecnologias

Python
Pandas
Automação de processos
Estruturação de pipeline de dados (ETL)
Web scraping (Selenium)
Integração com APIs (Telegram, Yahoo Finance)

---

## 🔄 Pipeline de Dados

O projeto segue uma estrutura de processamento em etapas:

**Coleta de Dados**
Importação de dados financeiros a partir de fontes estruturadas (ex: Google Sheets)

**Tratamento e Padronização**
Limpeza, organização e normalização dos dados utilizando Python (Pandas)

**Transformação**
Estruturação das informações para análise (categorias, agregações, ajustes)

**Análise**
Geração de indicadores, métricas de risco e insights financeiros

**Saída de Dados**
Produção de relatórios e dados prontos para consumo e envio automatizado

---

## 📊 Exemplo de Saída

Abaixo está um exemplo do relatório gerado:

![Exemplo](./images/example.png)

---

## ⚙️ Como Executar

1. Clone o repositório
2. Instale as dependências:
   `pip install -r requirements.txt`
3. Configure as credenciais:

   * Google Sheets API (`credenciais.json`)
   * Bot do Telegram (TOKEN e CHAT_ID)
4. Execute o pipeline:
   `python main.py`

---

## 🔒 Observação

Este projeto representa uma versão adaptada para portfólio, com foco na demonstração da estrutura técnica, construção de pipelines de dados e práticas de análise de dados.

Informações sensíveis (credenciais, tokens e dados financeiros pessoais) foram removidas por motivos de segurança.

