import time
import urllib.parse
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from .base import BaseScraper
from src.filters import FiltroVagas

class CathoScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.fonte = "Catho"
        self.url_base = "https://www.catho.com.br/vagas/"

    def buscar_vagas(self, termo="Estágio Java", local="Brasil"):
        vagas = []

        termo_encoded = urllib.parse.quote(termo.lower())
        url = f"{self.url_base}{termo_encoded}/?where_busca=1&traducao_busca=1"

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )

            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800}
            )

            page = context.new_page()

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)

                page.wait_for_selector("article, [data-gtm-extract=\"job-card\"]", timeout=15000)

                for _ in range(3):
                    page.evaluate("window.scrollBy(0, 800);")
                    time.sleep(1)

                conteudo_html = page.content()

            except Exception as e:
                print(f"[{self.fonte}] Erro ao carregar página via Playwright: {e}")
                conteudo_html = ""

            finally:
                browser.close()

        if not conteudo_html:
            return []

        soup = BeautifulSoup(conteudo_html, "html.parser")

        # Na Catho os cards das vagas ficam encapsulados dentro de tags <article>
        articles = soup.find_all("article")

        for card in articles:
            tag_link = card.find("a", href=True)
            if not tag_link:
                continue

            link = tag_link.get("href", "").strip()
            if not link or "/vagas/" not in link:
                continue

            link_limpo = link.split("?")[0]
            if not link_limpo.startswith("http"):
                link_limpo = f"https://www.catho.com.br{link_limpo}"

            # Título da vaga
            tag_titulo = card.find(["h2", "h3"]) or tag_link
            titulo = tag_titulo.text.strip() if tag_titulo else ""

            if not titulo:
                continue

            texto_card_completo = card.get_text(separator=" ").strip()

            tag_empresa = card.find(
                ["p", "span"],
                class_=lambda c: c and "company" in str(c).lower()
            )

            empresa = tag_empresa.text.strip() if tag_empresa else "Empresa não informada"
            localizacao = "Remoto" if "remoto" in texto_card_completo.lower() or "home office" in texto_card_completo.lower() else "Brasil"

            if not FiltroVagas.validar_vaga(titulo=titulo, localizacao=localizacao, conteudo_card=texto_card_completo):
                continue

            hash_gerado = self.gerar_hash(link_limpo, titulo)

            vagas.append({
                "hash_vaga": hash_gerado,
                "titulo": titulo,
                "empresa": empresa,
                "localizacao": localizacao,
                "url": link_limpo,
                "fonte": self.fonte
            })

        return vagas


if __name__ == "__main__":
    bot_catho = CathoScraper()
    resultado = bot_catho.buscar_vagas(termo="Estágio Java", local="Remoto")

    print(f"\n[Catho] Total de vagas validadas encontradas: {len(resultado)}")
    print("-" * 50)

    for vaga in resultado[:5]:
        print(f"Título: {vaga['titulo']}")
        print(f"Empresa: {vaga['empresa']}")
        print(f"Local: {vaga['localizacao']}")
        print(f"URL: {vaga['url']}")
        print(f"Hash: {vaga['hash_vaga']}")
        print("-" * 50)



