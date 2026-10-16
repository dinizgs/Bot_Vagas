import time
from pathlib import Path

# Importação dos módulos internos
from src.database import GerenciadorBanco
from src.notifier import TelegramNotifier

# Importação dos scrapers das plataformas
from src.scrapers.catho import CathoScraper
from src.scrapers.gupy import GupyScraper
from src.scrapers.jooble import JoobleScraper
from src.scrapers.linkedin import LinkedinScraper
from src.scrapers.remotar import RemotarScraper

def executar_bot():
    tempo_inicio = time.time()
    print("🚀 Iniciando varredura de vagas")

    db = GerenciadorBanco()
    notifier = TelegramNotifier()

    scrapers = [
        GupyScraper(),
    ]

    total_coletadas = 0
    total_salvas = 0

    for scraper in scrapers:
        nome_fonte = scraper.__class__.__name__.replace("Scraper", "")
        print(f"\n🔍 Buscando vagas em: {nome_fonte}...")

        try:
            vagas_encontradas = scraper.buscar_vagas()
            total_coletadas+=len(vagas_encontradas)

            print(f"↳ {len(vagas_encontradas)} vagas encontradas em {nome_fonte}.")

            #Processamento de cada encontrada
            for vaga in vagas_encontradas:
                if not isinstance(vaga, dict):
                    continue

                is_nova_vaga = db.salvar_vagas(vaga)

                if is_nova_vaga:
                    total_salvas+=1
                    notifier.enviar_notificacao_vaga(vaga)
                    time.sleep(1)

        except Exception as e:
            print(f"Erro ao processar scraper {nome_fonte}: {e}")

    tempo_fim = time.time()
    tempo_total = tempo_fim - tempo_inicio

    print("\n" + "=" * 40)
    print(f"✅ Varredura concluída em {tempo_total:.2f} segundos.")
    print(f"📊 Total de vagas analisadas: {total_coletadas}")
    print(f"💾 Novas vagas registradas e notificadas: {total_salvas}")
    print("=" * 40)

    notifier.enviar_resumo_busca(
        total_coletadas=total_coletadas,
        total_salvas=total_salvas,
        tempo_total=tempo_total
    )

if __name__ == "__main__":
    executar_bot()
        