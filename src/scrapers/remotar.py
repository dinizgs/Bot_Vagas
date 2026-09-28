import time
import urllib.parse
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from .base import BaseScraper
from src.filters import FiltroVagas

class RemotarScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.fonte = "Remotar"
        self.url_base = "https://remotar.com.br/"

    def buscar_vagas(self,termo="Estágio", local="Brasil"):
        vagas = []

        termo_limpo = termo.lower().replace("estágio", "").replace("estagio", "").replace("júnior", "").replace("junior", "").strip()
        termo_encoded = urllib.parse.quote(termo_limpo if termo_limpo else termo)

        url = f"{self.url_base}?q={termo_encoded}"

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

                page.wait_for_selector("a[href*='/job/'], a[href*='/vaga/'], article", timeout=15000)

                for _ in range(3):
                    page.evaluate("window.scrollBy(0, 600);")
                    time.sleep(1)

                conteudo_html = page.content()

            except Exception as e:
                print("[{self.fonte}] Erro ao carregar página via Playwright: {e}")
                conteudo_html = ""

            finally:
                browser.close()

        if not conteudo_html:
            return []

        soup = BeautifulSoup(conteudo_html, 'html.parser')

        todos_os_links = soup.find_all("a",href=True)
        links_vagas = []

        for tag in todos_os_links:
            url_link = tag["href"]

            if "/job" in url_link or "/vaga" in url_link:
                links_vagas.append(tag)

        cards_processados = set()

        for a_tag in links_vagas:
            link = a_tag.get("href", "").strip()

            if not link or link in cards_processados:
                continue

            cards_processados.add(link)

            link_limpo = link.split("?")[0]
            if not link_limpo.startswith("http"):
                link_limpo = f"https://remotar.com.br{link_limpo}"

            #Titulo da vaga
            tag_titulo = a_tag.find(["h2","h3","h4","span"])
            titulo = tag_titulo.text.strip() if tag_titulo else ""

            if not titulo or len(titulo) < 3:
                continue

            card_container = a_tag.find_parent("div") or a_tag
            texto_card_completo = card_container.get_text(separator=" ").strip()

            tag_empresa = None
            spans = card_container.find_all("span")
            for span in spans:
                classes = span.get("class", [])
                nome_classe = " ".join(classes) if isinstance(classes, list) else str(classes)
                if "company" in nome_classe.lower():
                    tag_empresa = span
                    break

            empresa = tag_empresa.text.strip() if tag_empresa else "Empresa não informada"

            localizacao = "Remoto"
            texto_card_com_modalidade = f"{texto_card_completo} remoto home office"

            # Aplicação do Filtro
            if not FiltroVagas.validar_vaga(titulo=titulo, localizacao=localizacao, conteudo_card=texto_card_com_modalidade):
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
    bot_remotar = RemotarScraper()
    resultado = bot_remotar.buscar_vagas(termo="Estágio", local="Remoto")

    print(f"\n[Remotar] Total de vagas validadas encontradas: {len(resultado)}")
    print("-" * 50)

    for vaga in resultado[:5]:
        print(f"Título: {vaga['titulo']}")
        print(f"Empresa: {vaga['empresa']}")
        print(f"Local: {vaga['localizacao']}")
        print(f"URL: {vaga['url']}")
        print(f"Hash: {vaga['hash_vaga']}")
        print("-" * 50)



        