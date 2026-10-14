import os
from html import escape
from pathlib import Path
import requests
from dotenv import load_dotenv

RAIZ_PROJETO = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=RAIZ_PROJETO / ".env")

class TelegramNotifier:
    def __init__(self):
        token_raw = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()

        if token_raw.lower().startswith("bot"):
            self.token = token_raw[3:]
        else:
            self.token = token_raw

        if self.token:
            self.url_base = f"https://api.telegram.org/bot{self.token}/sendMessage"
        else:
            self.url_base = None

    def esta_configurado(self):
        if not self.token or not self.chat_id:
            print("[Notifier] Credenciais (TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID) ausentes.")
            return False
        return True

    def disparar_mensagem(self, texto_html):
        payload = {
            "chat_id": self.chat_id,
            "text": texto_html,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }

        try:
            resposta = requests.post(self.url_base, json=payload, timeout=10)

            if resposta.status_code == 200:
                return True

            print(f"[Notifier] Falha na API ({resposta.status_code}): {resposta.text}")
            return False

        except requests.RequestException as erro:
            print(f"[Notifier] Erro de conexão com o Telegram: {erro}")
            return False

    def enviar_notificacao_vaga(self, vaga):
        if not self.esta_configurado():
            return False

        # Trata caracteres especiais de HTML para prevenir erros de parsing
        titulo = escape(vaga.get("titulo", "Sem título"))
        empresa = escape(vaga.get("empresa", "Não informada"))
        localizacao = escape(vaga.get("localizacao", "Brasil"))
        fonte = escape(vaga.get("fonte", "Desconhecida"))
        url = vaga.get("url", "#")

        # Modelo da mensagem em formato HTML
        mensagem_html = (
            "🚨 <b>NOVA VAGA ENCONTRADA!</b>\n\n"
            f"📌 <b>Título:</b> {titulo}\n"
            f"🏢 <b>Empresa:</b> {empresa}\n"
            f"📍 <b>Local:</b> {localizacao}\n"
            f"🌐 <b>Fonte:</b> {fonte}\n\n"
            f'🔗 <a href="{url}">Candidatar-se na vaga</a>'
        )

        sucesso = self.disparar_mensagem(mensagem_html)

        if sucesso:
            print(f"[Notifier] Notificação enviada: {vaga.get('titulo')}")

        return sucesso

    def enviar_resumo_busca(self, total_coletadas, total_salvas, tempo_total):
        if not self.esta_configurado():
            return False

        mensagem_html = (
            "📊 <b>RELATÓRIO DE VARREDURA</b>\n\n"
            f"⏱️ <b>Tempo Total:</b> {tempo_total:.2f}s\n"
            f"📦 <b>Total Analisado:</b> {total_coletadas}\n"
            f"💾 <b>Novas Vagas Salvas:</b> {total_salvas}"
        )

        return self.disparar_mensagem(mensagem_html)


    

