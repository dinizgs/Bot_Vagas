import re
import time
import random
from collections import Counter
from urllib.parse import quote
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from .base import BaseScraper
from src.filters import FiltroVagas
from src.config import (
    USER_AGENT,
    REMOTAR_MAX_ROLAGENS,
    DELAY_MIN,
    DELAY_MAX,
    HTTP_TIMEOUT
)


class RemotarScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.fonte = "Remotar"
        self.url_base = "https://remotar.com.br"
        self.max_rolagens = REMOTAR_MAX_ROLAGENS  # limite vindo do config.py

    def _obter_user_agent(self):
        user_agents = [
            USER_AGENT,
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        ]
        return random.choice(user_agents)

    def _carregar_tudo(self, page):
        # Rola até a quantidade de vagas parar de crescer (lista com carregamento infinito)
        anterior = -1
        estavel = 0

        for _ in range(self.max_rolagens):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.2)

            # Se existir botão de "ver mais", clica e olha
            try:
                botao = page.locator('button:has-text("Ver mais"), button:has-text("Carregar mais")').first
                if botao.count() > 0 and botao.is_visible():
                    botao.click()
                    time.sleep(1.0)
            except Exception:
                pass

            atual = page.locator('a[href*="/job/"]').count()
            if atual == anterior:
                estavel += 1
                if estavel >= 2:
                    break
            else:
                estavel = 0
            anterior = atual

    def buscar_vagas(self, termo=None, local="remoto"):
        vagas = []

        # Contador de motivos de descarte e exemplos de títulos
        motivos = Counter()
        exemplos = {}

        # Termos curtos e amplos (o filtro decide o nível e a área depois)
        termos_busca = [
            "estagio", "estágio", "junior", "júnior", "jr", "trainee",
            "desenvolvedor", "desenvolvedora", "software", "backend", "frontend", "fullstack",
            "python", "java", "react", "node",
            "dados", "qa", "ti", "tecnologia", "devops", "suporte", "analista de sistemas"
        ] if not termo else [termo]

        vagas_brutas = {}

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
            )

            context = browser.new_context(
                user_agent=self._obter_user_agent(),
                viewport={"width": 1280, "height": 800}
            )

            page = context.new_page()

            for t in termos_busca:
                url_busca = f"{self.url_base}/search/jobs?q={quote(t)}"

                try:
                    page.goto(url_busca, wait_until="domcontentloaded", timeout=HTTP_TIMEOUT * 1000)
                    time.sleep(2.5)

                    self._carregar_tudo(page)

                    soup = BeautifulSoup(page.content(), "html.parser")
                    links_vaga = soup.find_all("a", href=lambda h: h and "/job/" in h)

                    novos = 0
                    for a in links_vaga:
                        href = a.get("href", "").strip()
                        url_vaga = f"{self.url_base}{href}" if href.startswith("/") else href
                        texto_card = a.get_text(separator=" ", strip=True)

                        if not texto_card or len(texto_card) < 8:
                            continue

                        # Id da vaga na URL (Para não se repetir entre termos)
                        achou_id = re.search(r"/job/(\d+)", href)
                        chave = achou_id.group(1) if achou_id else url_vaga
                        if chave in vagas_brutas:
                            continue

                        titulo_el = a.find(["h1", "h2", "h3", "h4", "strong", "p"])
                        titulo = titulo_el.get_text(strip=True) if titulo_el else texto_card.split("•")[0].strip()

                        partes_url = href.split("/")
                        if len(partes_url) >= 4:
                            empresa = partes_url[3].replace("-", " ").title()
                        else:
                            empresa = "Empresa parceira Remotar"

                        vagas_brutas[chave] = {
                            "titulo": titulo,
                            "empresa": empresa,
                            "url": url_vaga,
                            "texto_card": texto_card
                        }
                        novos += 1

                    print(f"[{self.fonte}] '{t}': {len(links_vaga)} links, {novos} vagas novas (únicas até agora: {len(vagas_brutas)})")

                except Exception as e:
                    print(f"[{self.fonte}] Erro ao carregar termo '{t}': {e}")

                time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

            browser.close()

        print(f"[{self.fonte}] Total de vagas brutas capturadas: {len(vagas_brutas)}")

        hashes_vistos = set()

        for item in vagas_brutas.values():
            titulo = item["titulo"]
            link_limpo = item["url"].split("?")[0]
            empresa = item["empresa"]
            texto_card = item["texto_card"]
            localizacao = "Remoto"

            hash_calculado = self.gerar_hash(link_limpo, titulo)
            if hash_calculado in hashes_vistos:
                motivos["duplicada"] += 1
                continue

            aprovada, motivo = FiltroVagas.avaliar(titulo=titulo, localizacao=localizacao, conteudo_card=texto_card)
            if not aprovada:
                motivos[motivo] += 1
                if len(exemplos.setdefault(motivo, [])) < 5:
                    exemplos[motivo].append(titulo)
                continue

            hashes_vistos.add(hash_calculado)

            vagas.append({
                "hash_vaga": hash_calculado,
                "titulo": titulo,
                "empresa": empresa,
                "localizacao": localizacao,
                "url": link_limpo,
                "fonte": self.fonte
            })

        print(f"[{self.fonte}] Motivos de descarte: {dict(motivos)}")
        for motivo, titulos in exemplos.items():
            print(f"   {motivo}: {titulos}")

        return vagas


if __name__ == "__main__":
    bot = RemotarScraper()
    resultado = bot.buscar_vagas()

    print(f"\n[Remotar] Total de vagas validadas final: {len(resultado)}")
    print("-" * 50)

    for vaga in resultado[:10]:
        print(f"Título: {vaga['titulo']}")
        print(f"Empresa: {vaga['empresa']}")
        print(f"Local: {vaga['localizacao']}")
        print(f"URL: {vaga['url']}")
        print(f"Hash: {vaga['hash_vaga']}")
        print("-" * 50)


        