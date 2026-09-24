import time
from bs4 import BeautifulSoup
from urllib.parse import quote
from playwright.sync_api import sync_playwright
from .base import BaseScraper

class LinkedinScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.fonte = "LinkedIn"
        self.url_base = "https://br.linkedin.com/jobs/search/"

    def buscar_vagas(self, termo="Java (Estágio OR Junior OR Jr)", local="Brasil"):
        vagas = []
        termo_encoded = quote(termo)
        local_encoded = quote(local)

        url = f"{self.url_base}?keywords={termo_encoded}&location={local_encoded}&geoId=106057199&f_WT=2"

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

                page.wait_for_selector("div.base-card, li.base-search-card, ul.jobs-search__results-list", timeout=15000)

                # Rola a página para carregar mais vagas dinamicamente
                for _ in range(4):
                    page.evaluate("window.scrollBy(0, 1000);")
                    time.sleep(1)

                conteudo_html = page.content()

            except Exception as e:
                print(f"Erro ao carregar a página no LinkedIn via Playwright: {e}")
                conteudo_html = ""

            finally:
                browser.close()

        if not conteudo_html:
            return []

        soup = BeautifulSoup(conteudo_html, "html.parser")

        CLASSES_CARDS = [
            "base-card",
            "base-search-card",
            "job-search-card"
        ]

        cards = soup.find_all(["div", "li"], class_=CLASSES_CARDS)
        
        if not cards:
            cards = [a.parent for a in soup.find_all("a") if "/jobs/view" in a.get("href", "")]

        # Lista de filtros
        TERMOS_INTERNACIONAIS = ["summer", "internship", "intern (", "united states", "global", "north america"]
        
        TERMOS_NIVEL_ENTRADA = [
            "estágio", "estagio", "estagiário", "estagiario", 
            "júnior", "junior", "jr", "desenvolvedor i", "developer i", 
            "trainee", "associate", "analista de sistemas", "assistente"
        ]

        TERMOS_EXCLUIR_NIVEL = ["sênior", "senior", "pleno", "lead", "coordenador", "gerente", "head", "principal", "sr"]

        for card in cards:
            links_vaga = [
                a.get("href", "") for a in card.find_all("a") 
                if "/jobs/view" in a.get("href", "")
            ]

            if not links_vaga:
                continue

            valor_link = links_vaga[0].strip()
            link_limpo = valor_link.split("?")[0]

            elementos_texto = [
                elem.text.strip()
                for elem in card.find_all(["p", "span", "h3", "h4", "a"])
                if elem.text and elem.text.strip()
            ]

            if not elementos_texto:
                continue

            valor_titulo = elementos_texto[0]
            titulo = valor_titulo.split("(Vaga")[0].split("...")[0].strip()
            titulo_lower = titulo.lower()

            # 1. Elimina vagas internacionais
            if any(termo_int in titulo_lower for termo_int in TERMOS_INTERNACIONAIS):
                continue

            # 2. Elimina níveis mais altos (Sênior, Pleno, Lead, etc.)
            if any(nivel_alto in titulo_lower for nivel_alto in TERMOS_EXCLUIR_NIVEL):
                continue

            # 3. Garante que é vaga de entrada (Estágio, Júnior, Jr, Trainee, etc.)
            if not any(nivel in titulo_lower for nivel in TERMOS_NIVEL_ENTRADA):
                continue

            texto_card_completo = " ".join(elementos_texto).lower()
            if "presencial" in texto_card_completo or "híbrido" in texto_card_completo or "hibrido" in texto_card_completo:
                continue

            empresa = "Empresa não informada"
            localizacao = ""

            for texto in elementos_texto[1:]:
                if texto in ["...", "Vaga verificada"] or "candidatos" in texto.lower() or "candidatar-se" in texto.lower():
                    continue

                if any(loc in texto for loc in [",", "Remoto", "Brasil", "CE", "RJ", "SP", "MG", "PR", "BA", "RS", "SC"]):
                    if not localizacao:
                        localizacao = texto

                elif empresa == "Empresa não informada" and texto != valor_titulo and texto != titulo:
                    empresa = texto

            if not localizacao:
                localizacao = "Remoto"

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
    bot_linkedin = LinkedinScraper()
    
    # Teste de busca por vagas Java de Estágio ou Júnior
    resultado = bot_linkedin.buscar_vagas(termo="Java (Estágio OR Junior OR Jr)", local="Brasil")

    print(f"\n[LinkedIn] Total de vagas encontradas: {len(resultado)}")
    print("-" * 50)

    for vaga in resultado:
        print(f"Título: {vaga['titulo']}")
        print(f"Empresa: {vaga['empresa']}")
        print(f"Local: {vaga['localizacao']}")
        print(f"URL: {vaga['url']}")
        print(f"Hash: {vaga['hash_vaga']}")
        print("-" * 50)

        