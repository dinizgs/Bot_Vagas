import time
import random
from urllib.parse import quote
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from .base import BaseScraper
from src.filters import FiltroVagas


class LinkedinScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.fonte = "LinkedIn"
        self.url_base = "https://br.linkedin.com/jobs/search/"

    def _obter_user_agent(self):
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ]
        return random.choice(user_agents)

    def buscar_vagas(self, termo=None, local="Brasil"):
        vagas = []
        
        termos_busca = [
            "estagio ti",
            "estagio tecnologia",
            "estagio desenvolvimento",
            "ti junior",
            "desenvolvedor junior",
            "desenvolvedor backend junior",
            "desenvolvedor frontend junior",
            "desenvolvedor fullstack junior",
            "desenvolvedor mobile junior",
            "desenvolvedor java junior",
            "desenvolvedor python junior",
            "desenvolvedor react junior",
            "desenvolvedor node junior",
            "estagio dados",
            "estagio engenharia de dados",
            "analista de dados junior",
            "engenheiro de dados junior",
            "cientista de dados junior",
            "ia junior",
            "artificial intelligence intern",
            "qa junior",
            "estagio qa",
            "analista de testes junior",
            "devops junior",
            "suporte ti junior",
            "analista de sistemas junior"
        ] if not termo else [termo]

        vagas_brutas = []

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
                termo_encoded = quote(t)
                local_encoded = quote(local)
                url = f"{self.url_base}?keywords={termo_encoded}&location={local_encoded}&geoId=106057199&f_WT=2"

                print(f"[{self.fonte}] Acessando busca: {t}")

                # Tentativa de acesso com tolerância a AuthWall
                sucesso = False
                for tentativa in range(2):
                    try:
                        page.goto(url, wait_until="domcontentloaded", timeout=30000)

                        # Verifica se caiu na AuthWall/Login imediatamente sem esperar timeout
                        if "authwall" in page.url or "login" in page.url or "signup" in page.url:
                            print(f"[{self.fonte}] AuthWall detectada no termo '{t}' (tentativa {tentativa + 1}). Renovando sessão...")
                            page.close()
                            context.close()
                            
                            # Abre novo contexto com User-Agent renovado
                            context = browser.new_context(
                                user_agent=self._obter_user_agent(),
                                viewport={"width": 1280, "height": 800}
                            )
                            page = context.new_page()
                            time.sleep(3)
                            continue

                        # Tenta localizar a lista de resultados
                        page.wait_for_selector(
                            "div.base-card, li.base-search-card, ul.jobs-search__results-list",
                            timeout=8000
                        )
                        sucesso = True
                        break

                    except Exception as e:
                        if tentativa == 1:
                            print(f"[{self.fonte}] Erro ao carregar '{t}' após retentativa: {e}")

                if not sucesso:
                    continue

                # Scroll gradual
                for _ in range(3):
                    page.evaluate("window.scrollBy(0, 800);")
                    time.sleep(0.8)

                conteudo_html = page.content()
                soup = BeautifulSoup(conteudo_html, "html.parser")

                CLASSES_CARDS = ["base-card", "base-search-card", "job-search-card"]
                cards = soup.find_all(["div", "li"], class_=CLASSES_CARDS)

                if not cards:
                    cards = [a.parent for a in soup.find_all("a") if "/jobs/view" in a.get("href", "")]

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

                    texto_card_completo = " ".join(elementos_texto)

                    vagas_brutas.append({
                        "titulo": titulo,
                        "empresa": empresa,
                        "localizacao": localizacao,
                        "url": link_limpo,
                        "texto_card": texto_card_completo
                    })

                # Pausa estratégica e dinâmica entre requisições
                time.sleep(random.uniform(2.0, 3.5))

            browser.close()

        print(f"[{self.fonte}] Total de vagas brutas capturadas: {len(vagas_brutas)}")

        hashes_vistos = set()

        for item in vagas_brutas:
            titulo = item["titulo"]
            link_limpo = item["url"]
            empresa = item["empresa"]
            localizacao = item["localizacao"]
            texto_card_completo = item["texto_card"]

            hash_gerado = self.gerar_hash(link_limpo, titulo)

            if hash_gerado in hashes_vistos:
                continue

            if not FiltroVagas.validar_vaga(titulo=titulo, localizacao=localizacao, conteudo_card=texto_card_completo):
                continue

            hashes_vistos.add(hash_gerado)

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
    resultado = bot_linkedin.buscar_vagas()

    print(f"\n[LinkedIn] Total de vagas validadas final: {len(resultado)}")
    print("-" * 50)

    for vaga in resultado[:10]:
        print(f"Título: {vaga['titulo']}")
        print(f"Empresa: {vaga['empresa']}")
        print(f"Local: {vaga['localizacao']}")
        print(f"URL: {vaga['url']}")
        print(f"Hash: {vaga['hash_vaga']}")
        print("-" * 50)
        