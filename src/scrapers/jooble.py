from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from .base import BaseScraper

class JoobleScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.fonte = "Jooble"
        self.url_base = "https://br.jooble.org/SearchResult"

    def buscar_vagas(self, termo="Estágio", local="Remoto"):
        vagas = []
        url = f"{self.url_base}?ukw={termo}&rgns={local}"

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            
            # Contexto configurado com User-Agent real
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
            page = context.new_page()

            try:
                #Carrega o DOM inicial sem travar em conexões de rede ativas
                page.goto(url, wait_until="domcontentloaded", timeout=60000)

                #Aguarda a renderização dos cards das vagas no HTML
                page.wait_for_selector('div[data-test-name="_jobCard"]', timeout=15000)

                conteudo_html = page.content()
            except Exception as e:
                print(f"Erro ao carregar a página no Jooble via Playwright: {e}")
                conteudo_html = ""
            finally:
                browser.close()

        if not conteudo_html:
            return []

        #Processamento do HTML com BeautifulSoup
        soup = BeautifulSoup(conteudo_html, "html.parser")
        cards = soup.find_all("div", attrs={"data-test-name": "_jobCard"})

        for card in cards:
            tag_link = card.find("a")
            
            if tag_link:
                titulo = tag_link.text.strip()
                link = tag_link.get("href", "")

                if link.startswith("/"):
                    link = f"https://br.jooble.org{link}"

                tag_empresa = card.find("div", class_="pxYhD4") or card.find("div", attrs={"data-test-name": "company-name"})

                if tag_empresa:
                    texto_empresa = tag_empresa.text.strip()

                    # Se o texto começar com "R$", provavelmente é o salário, não a empresa
                    if texto_empresa.startswith("R$"):
                        empresa = "Empresa não informada"
                    else:
                        empresa = texto_empresa
                else:
                    empresa = "Empresa não informada"

                tag_local = card.find("div", class_="gFo59w")
                localizacao = tag_local.text.strip() if tag_local else "Remoto"

                link_limpo = link.split('?')[0]
                hash_calculado = self.gerar_hash(link_limpo, titulo)

                vaga = {
                    "hash_vaga": hash_calculado,
                    "titulo": titulo,
                    "empresa": empresa,
                    "localizacao": localizacao,
                    "url": link, 
                    "fonte": self.fonte
                }

                vagas.append(vaga)

        return vagas


if __name__ == "__main__":
    bot_jooble = JoobleScraper()
    resultado = bot_jooble.buscar_vagas(termo="Estágio Java", local="Remoto")

    print(f"\nTotal de vagas encontradas: {len(resultado)}")
    print("-" * 50)

    for vaga in resultado[:3]:
        print(f"Título: {vaga['titulo']}")
        print(f"Empresa: {vaga['empresa']}")
        print(f"Local: {vaga['localizacao']}")
        print(f"URL: {vaga['url']}")
        print(f"Hash: {vaga['hash']}")
        print("-" * 50)