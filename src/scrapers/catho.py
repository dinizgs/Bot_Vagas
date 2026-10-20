import time
import random
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

        self.TERMOS_INFRA_FISICA = [
            "redes", "hardware", "cabeamento", "helpdesk", "help desk",
            "service desk", "suporte técnico", "suporte tecnico",
            "manutenção", "manutencao", "telecom", "infraestrutura"
        ]

    def _obter_user_agent(self):
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        ]
        return random.choice(user_agents)

    def _eh_foco_desenvolvimento(self, texto):
        texto_lower = texto.lower()
        if any(infra in texto_lower for infra in self.TERMOS_INFRA_FISICA):
            if not any(code in texto_lower for code in ["desenvolvimento", "programador", "software", "código", "codigo", "script"]):
                return False
        return True

    def buscar_vagas(self, termo=None, local="remoto"):
        vagas = []

        # Termos na parte de desenvolvimento e afins
        termos_busca = [
            "estagio desenvolvimento",
            "estagio engenharia de software",
            "estagio programação",
            "desenvolvedor junior",
            "desenvolvedor backend junior",
            "desenvolvedor frontend junior",
            "desenvolvedor fullstack junior",
            "desenvolvedor java junior",
            "desenvolvedor python junior",
            "desenvolvedor react junior",
            "desenvolvedor node junior",
            "estagio dados",
            "estagio engenharia de dados",
            "analista de dados junior",
            "cientista de dados junior",
            "estagio qa",
            "qa junior",
            "analista de testes junior",
            "devops junior"
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
                termo_encoded = urllib.parse.quote(t.lower())
                url = f"{self.url_base}{termo_encoded}/?where_busca=1&traducao_busca=1&trabalho_remoto=1"

                print(f"[{self.fonte}] Acessando busca: {t}")

                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=30000)

                    try:
                        page.wait_for_selector("article, [data-gtm-extract='job-card']", timeout=8000)
                    except Exception:
                        pass

                    for _ in range(3):
                        page.evaluate("window.scrollBy(0, 800);")
                        time.sleep(0.5)

                    conteudo_html = page.content()
                    soup = BeautifulSoup(conteudo_html, "html.parser")

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

                        texto_card_completo = card.get_text(separator=" ").strip()

                        if not self._eh_foco_desenvolvimento(texto_card_completo):
                            continue

                        tag_titulo = card.find(["h2", "h3"]) or tag_link
                        titulo = tag_titulo.text.strip() if tag_titulo else ""

                        if not titulo:
                            continue

                        # Extração do nome real da empresa
                        tag_empresa = card.find(attrs={"data-gtm-extract": "company-name"}) or card.find(
                            ["p", "span"], class_=lambda c: c and "company" in str(c).lower()
                        )
                        empresa = tag_empresa.text.strip() if tag_empresa else "Empresa Confidencial"

                        vagas_brutas.append({
                            "titulo": titulo,
                            "empresa": empresa,
                            "url": link_limpo,
                            "texto_card": texto_card_completo
                        })

                except Exception as e:
                    print(f"[{self.fonte}] Erro ao buscar termo '{t}': {e}")

                time.sleep(random.uniform(1.5, 2.5))

            browser.close()

        print(f"[{self.fonte}] Total de vagas brutas capturadas: {len(vagas_brutas)}")

        hashes_vistos = set()

        for item in vagas_brutas:
            titulo = item["titulo"]
            link_limpo = item["url"]
            empresa = item["empresa"]
            texto_card = item["texto_card"]
            texto_lower = texto_card.lower()

            #Inspeciona se o texto do card declara expressamente regime remoto
            if any(termo in texto_lower for termo in ["remoto", "home office", "home-office", "trabalho remoto", "teletrabalho"]):
                localizacao = "Remoto"
            else:
                localizacao = "Presencial / Híbrido"

            hash_gerado = self.gerar_hash(link_limpo, titulo)

            if hash_gerado in hashes_vistos:
                continue

            # Validação FiltroVagas
            if not FiltroVagas.validar_vaga(titulo=titulo, localizacao=localizacao, conteudo_card=texto_card):
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
    bot_catho = CathoScraper()
    resultado = bot_catho.buscar_vagas()

    print(f"\n[Catho] Total de vagas validadas (Apenas Remotas & Dev/Dados): {len(resultado)}")
    print("-" * 50)

    for vaga in resultado[:10]:
        print(f"Título: {vaga['titulo']}")
        print(f"Empresa: {vaga['empresa']}")
        print(f"Local: {vaga['localizacao']}")
        print(f"URL: {vaga['url']}")
        print(f"Hash: {vaga['hash_vaga']}")
        print("-" * 50)