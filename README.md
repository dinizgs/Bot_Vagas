# 🤖 Bot Notificador de Vagas de TI & Estágio Remoto

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white)
![Playwright](https://img.shields.io/badge/Playwright-Automation-green?style=for-the-badge&logo=playwright&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-CI%2FCD-2088FF?style=for-the-badge&logo=githubactions&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram-Bot%20API-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?style=for-the-badge&logo=sqlite&logoColor=white)

Um pipeline automatizado e autônomo que realiza a varredura contínua (*web scraping*) por oportunidades de trabalho remoto e estágio na área de Tecnologia da Informação (TI), consolida os dados de múltiplas plataformas e envia notificações em tempo real via Telegram.

---

## 📌 Visão Geral

Procurar vagas de TI em várias plataformas diariamente consome tempo e muitas vezes resulta em visualizações de oportunidades repetidas ou fora do perfil desejado.

Este projeto resolve esse problema automatizando o ciclo completo de busca, filtragem e notificação. O bot roda de forma 100% autônoma em nuvem através do **GitHub Actions**, buscando novas vagas **duas vezes ao dia (08:05 e 20:05 BRT)** nas principais plataformas do mercado.
**OBS: Como demora entre 20 minutos a 30 minutos para realizar a execução do bot, então não é exatamente no horário colocado!**

---

## ⚡ Principais Funcionalidades

- **Scraping Multi-Plataforma:** Coleta automatizada em três fontes principais:
  - **Gupy:** Captura via chamadas diretas à API pública.
  - **Remotar:** Scraping estruturado focado exclusivamente em vagas remotas.
  - **LinkedIn:** Automação via navegador headless (Playwright) para busca e extração de vagas recentes.
- **Filtragem Inteligente & Anti-Sênior:** Algoritmo que descarte de forma rigorosa:
  - Vagas presenciais ou híbridas (foco 100% remoto).
  - Cargos Pleno, Sênior, Specialist e Lead (foco em níveis de entrada: *Estágio, Trainee, Júnior, Assistente*).
  - Vagas de fora do escopo de TI (Comercial, Financeiro, RH, etc.).
- **Deduplicação por Banco de Dados:** Registro em banco **SQLite** (`data/vagas.db`) para garantir que nenhuma vaga repetida seja enviada.
- **Notificação Instantânea no Telegram:** Mensagens formatadas em HTML contendo título, empresa, localização, fonte e link direto para candidatura.
- **Relatório de Varredura:** Envio automático do resumo de desempenho da busca (tempo de execução, total analisado e novas vagas encontradas).

---

## 🛠️ Tecnologias Utilizadas

- **Linguagem:** Python 3.x
- **Scraping & Automação:**
  - `Playwright` (Navegação dinâmica e bypass de carregamentos do LinkedIn)
  - `BeautifulSoup4` & `Requests` (Parsing HTML e consumo de APIs/páginas estáticas)
- **Banco de Dados:** SQLite3
- **Notificações:** API de Bots do Telegram
- **Gerenciamento de Ambiente:** `python-dotenv`
- **CI/CD & Agendamento:** GitHub Actions (Cron Scheduler & Git Auto-Commit)

---

## 🏗️ Arquitetura e Fluxo de Execução

```text
[ GitHub Actions Cron Trigger (08:05 e 20:05 BRT) ]
                       │
                       ▼
         [ Execução do script main.py ]
                       │
       ┌───────────────┼───────────────┐
       ▼               ▼               ▼
[ Gupy Scraper ]  [ Remotar ]  [ LinkedIn Scraper ]
       │               │               │
       └───────────────┼───────────────┘
                       │
                       ▼
       [ Filtro de Requisitos & Nível ]
                       │
                       ▼
         [ Verificação SQLite (vagas.db) ]
           ├── Já existe? ──> Descarta
           └── É nova? ────> Salva no DB
                                │
                                ▼
                 [ Telegram Notifier ]
