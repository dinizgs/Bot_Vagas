import os
import time
import argparse
import logging

# Importação das configurações centralizadas
from src.config import (
    LOG_FILE,
    LOCK_FILE,
    LOCK_EXPIRA_EM_SEGUNDOS,
    LIMITE_NOTIFICACOES,
    DIAS_LINKEDIN_RECORRENTE,
)

# Configuração de logs na path (logs/execucao.log)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8")
    ]
)

from contextlib import contextmanager

# Importação dos módulos internos
from src.database import GerenciadorBanco
from src.notifier import TelegramNotifier

# Importação dos scrapers das plataformas
from src.scrapers.gupy import GupyScraper
from src.scrapers.linkedin import LinkedinScraper
from src.scrapers.remotar import RemotarScraper

SCRAPERS = {
    "gupy": GupyScraper,
    "linkedin": LinkedinScraper,
    "remotar": RemotarScraper,
}


@contextmanager
def trava_execucao():
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)

    if LOCK_FILE.exists():
        tempo_vida = time.time() - LOCK_FILE.stat().st_mtime
        if tempo_vida < LOCK_EXPIRA_EM_SEGUNDOS:
            logging.warning("Já existe uma execução em andamento do bot! (data/bot.lock)")
            yield False
            return

    LOCK_FILE.write_text(str(os.getpid()))
    try:
        yield True
    finally:
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()


def coletar_fonte(db, nome_fonte, scraper):
    inicio = time.time()
    logging.info(f"Buscando vagas em: {nome_fonte}...")

    # Otimização da janela do LinkedIn para execuções recorrentes
    if nome_fonte == "LinkedIn" and hasattr(scraper, "janela") and db.contar_vagas(nome_fonte) > 0:
        scraper.janela = f"r{DIAS_LINKEDIN_RECORRENTE * 86400}"
        logging.info(f"Janela do LinkedIn reduzida para {DIAS_LINKEDIN_RECORRENTE} dias.")

    try:
        vagas_brutas = scraper.buscar_vagas()

        vagas = []
        for vaga in vagas_brutas:
            if isinstance(vaga, dict):
                vagas.append(vaga)

        salvas = db.salvar_vagas(vagas)
        duracao = time.time() - inicio

        status = "ok" if vagas else "aviso"
        mensagem = f"{duracao:.0f}s" if vagas else f"sem vagas ({duracao:.0f}s)"
        db.registrar_log(nome_fonte, len(vagas), salvas, status, mensagem)

        logging.info(f"{len(vagas)} vagas encontradas em {nome_fonte}, {salvas} novas.")
        return len(vagas), salvas

    except Exception as e:
        logging.error(f"Erro ao processar scraper {nome_fonte}: {e}")
        db.registrar_log(nome_fonte, 0, 0, "erro", str(e))
        return 0, 0


def notificar_uma_vaga_pendente(db, notifier):
    pendentes = db.buscar_vagas_nao_notificadas(limite=LIMITE_NOTIFICACOES)

    if not pendentes:
        logging.info("Nenhuma vaga pendente na fila para notificar.")
        return 0

    vaga = pendentes[0]
    logging.info(f"Enviando vaga da fila: [{vaga.get('fonte')}] {vaga.get('titulo')}")

    try:
        resultado = notifier.enviar_notificacao_vaga(vaga)
        if resultado is not False:
            db.marcar_como_notificada(vaga["id_vaga"])
            logging.info("Vaga enviada com sucesso ao Telegram!")
            return 1
        else:
            logging.warning("Telegram recusou o envio da vaga. Permanecerá pendente.")

    except Exception as e:
        logging.error(f"Falha ao notificar vaga '{vaga.get('titulo')}': {e}")

    return 0


def executar_bot(nomes_fontes):
    tempo_inicio = time.time()
    logging.info("🚀 Iniciando varredura e ciclo de notificação")

    db = GerenciadorBanco()
    total_coletadas, total_salvas = 0, 0

    # Coleta novas vagas em todas as fontes configuradas
    for nome in nomes_fontes:
        scraper = SCRAPERS[nome]()
        coletadas, salvas = coletar_fonte(db, scraper.fonte, scraper)
        total_coletadas += coletadas
        total_salvas += salvas

    # Processamento das notificações unitárias
    notifier = TelegramNotifier()
    enviadas = notificar_uma_vaga_pendente(db, notifier)

    tempo_total = time.time() - tempo_inicio

    logging.info("=" * 40)
    logging.info(f"Execução concluída em {tempo_total:.2f} segundos.")
    logging.info(f"Analisadas nesta rodada: {total_coletadas}")
    logging.info(f"Novas salvas no banco: {total_salvas}")
    logging.info(f"Notificada nesta rodada: {enviadas}")
    logging.info("=" * 40)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bot de Vagas Tech Remotas (Envio Cadenciado)")
    parser.add_argument(
        "--fonte", nargs="+", choices=list(SCRAPERS.keys()), default=list(SCRAPERS.keys()),
        help="Roda só as fontes indicadas (padrão: todas)"
    )

    args = parser.parse_args()

    with trava_execucao() as ativo:
        if ativo:
            executar_bot(args.fonte)
