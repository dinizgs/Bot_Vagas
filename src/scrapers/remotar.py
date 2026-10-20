import time
import random
from collections import Counter  # [NOVO]
from urllib.parse import quote
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from .base import BaseScraper
from src.filters import FiltroVagas, normalizar, compilar  


class RemotarScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.fonte = "Remotar"
        self.url_base = "https://remotar.com.br"

        self.KEYWORDS_TECH = [
            "desenvolvedor", "developer", "programador", "software", "frontend", "front-end",
            "backend", "back-end", "fullstack", "full-stack", "ti", "tecnologia", "dados",
            "data", "qa", "testes", "tester", "quality assurance", "devops", "infraestrutura",
            "suporte", "sistemas", "python", "java", "react", "node", "ia", "artificial intelligence",
            "computacao", "sistemas de informacao", "engenharia de software"
        ]

        # Áreas não-tech a serem ignoradas no Remotar
        self.TERMOS_IGNORAR = [
            "comercial", "pré-vendas", "pre-vendas", "fpa", "fp&a", "controladoria",
            "contábil", "contabil", "administrativo", "marketing", "redator", "copywriter",
            "rh", "recursos humanos", "jurídico", "juridico", "vendas", "backoffice", "afiliados"
        ]

        self.EXCECOES_SUPORTE = ["suporte ti", "suporte técnico", "suporte tecnico"]

        self.REGEX_TECH = compilar(self.KEYWORDS_TECH)
        self.REGEX_IGNORAR = compilar(self.TERMOS_IGNORAR)
        self.REGEX_EXCECOES = compilar(self.EXCECOES_SUPORTE)

    def _obter_user_agent(self):
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        ]
        return random.choice(user_agents)

    def _eh_vaga_tech(self, texto):
        texto_norm = normalizar(texto)

        if self.REGEX_IGNORAR.search(texto_norm):
            if not self.REGEX_EXCECOES.search(texto_norm):
                return False
            
        return bool(self.REGEX_TECH.search(texto_norm))

    def buscar_vagas(self, termo=None, local="remoto"):
        vagas = []

        motivos = Counter()
        exemplos = {}

        termos_busca = [
            "estagio ti",
            "estagio tecnologia",
            "estagio desenvolvimento",
            "estagio engenharia de software",
            "estagio software engineering",
            "software engineer intern",
            "ti junior",
            "desenvolvedor junior",
            "engenheiro de software junior",
            "software engineer junior",
            "jr software engineer",
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
                url_busca = f"{self.url_base}/search/jobs?q={termo_encoded}"
                print(f"[{self.fonte}] Acessando busca: {t}")

                try:
                    page.goto(url_busca, wait_until="domcontentloaded", timeout=25000)
                    time.sleep(2.5)

                    for _ in range(3):
                        page.evaluate("window.scrollBy(0, 800);")
                        time.sleep(0.5)

                    conteudo_html = page.content()
                    soup = BeautifulSoup(conteudo_html, "html.parser")

                    links_vaga = soup.find_all("a", href=lambda h: h and "/job/" in h)

                    for a in links_vaga:
                        href = a.get("href", "").strip()
                        url_vaga = f"{self.url_base}{href}" if href.startswith("/") else href
                        texto_card = a.get_text(separator=" ", strip=True)

                        if not texto_card or len(texto_card) < 8:
                            continue

                        # Filtro de escopo Tech pré-validação
                        if not self._eh_vaga_tech(texto_card):
                            motivos["fora_de_ti"] += 1
                            continue

                        # Extração do Título
                        titulo_el = a.find(["h1", "h2", "h3", "h4", "strong", "p"])
                        titulo = titulo_el.get_text(strip=True) if titulo_el else texto_card.split("•")[0].strip()

                        partes_url = href.split("/")
                        if len(partes_url) >= 4:
                            empresa = partes_url[3].replace("-", " ").title()
                        else:
                            empresa = "Empresa parceira Remotar"

                        vagas_brutas.append({
                            "titulo": titulo,
                            "empresa": empresa,
                            "url": url_vaga,
                            "texto_card": texto_card
                        })

                except Exception as e:
                    print(f"[{self.fonte}] Erro ao carregar termo '{t}': {e}")

                time.sleep(random.uniform(1.5, 2.5))

            browser.close()

        print(f"[{self.fonte}] Total de vagas brutas capturadas: {len(vagas_brutas)}")

        hashes_vistos = set()

        for item in vagas_brutas:
            titulo = item["titulo"]
            link = item["url"]
            empresa = item["empresa"]
            texto_card = item["texto_card"]
            localizacao = "Remoto"

            link_limpo = link.split("?")[0]
            hash_calculado = self.gerar_hash(link_limpo, titulo)

            if hash_calculado in hashes_vistos:
                motivos["duplicada"] += 1
                continue

            #Validação centralizada do FiltroVagas com o motivo do descarte
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

        # [NOVO] Resumo do funil
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



        