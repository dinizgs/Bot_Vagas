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

> **Nota:** A execução completa leva cerca de 20 a 30 minutos devido aos tempos de espera (*delays* anti-bloqueio) e varreduras profundas, portanto os disparos e notificações finalizam ao longo desse intervalo.

---

## ⚡ Principais Funcionalidades

- **Scraping Multi-Plataforma:** Coleta automatizada em três fontes principais:
  - **Gupy:** Captura via chamadas diretas à API pública.
  - **Remotar:** Scraping estruturado focado exclusivamente em vagas remotas.
  - **LinkedIn:** Automação via navegador headless (Playwright) para busca e extração de vagas recentes.
- **Filtragem Inteligente & Anti-Sênior:** Algoritmo que descarta de forma rigorosa:
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
                                │
                                ▼
                  [ Git Auto-Commit (vagas.db) ]
```

---

## 🔮 Futuras Implementações & Roadmap

Propostas de melhorias e novas funcionalidades para evoluir a arquitetura e a precisão do bot:

- [ ] **Interface Web / Dashboard:** Desenvolvimento de um painel simples (Streamlit ou FastAPI + React) para visualização e busca rápida das vagas armazenadas no banco de dados.
- [ ] **Filtro Avançado com Inteligência Artificial:** Integração com LLMs (como OpenAI ou Gemini API) para análise do texto descritivo das vagas, garantindo uma classificação ainda mais precisa das competências exigidas e evitando *false positives*.
- [ ] **Análise de Match com Currículo:** Leitura do PDF do currículo do usuário para calcular uma pontuação de aderência (*match score*) para cada vaga e destacá-la na notificação.
- [ ] **Expansão de Plataformas:** Adição de novos scrapers para portais como Catho, Indeed, Glassdoor e Programathor.
- [ ] **Notificações Personalizadas por Categorias:** Opção de filtrar ou categorizar notificações no Telegram através de tópicos (ex: canal separado para Backend, Frontend, Dados ou Estágio).
- [ ] **Rotação de Proxies no LinkedIn:** Implementação de uma camada de rotação de IP/Proxies no scraper do LinkedIn para contornar o limite de requisições (HTTP 429) e expandir o volume de captura diária.
