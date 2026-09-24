import json
import urllib.parse
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from .base import BaseScraper
from src.filters import FiltroVagas

class GupyScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.fonte = "Gupy"
        self.url_base = "https://portal.gupy.io/job-search"

    def buscar_vagas(self, termo="Java", local="Brasil"):
        vagas = []
        
        # Limpa termos de nível do parâmetro de busca para não travar a busca da Gupy
        termo_limpo = termo.lower().replace("estágio", "").replace("estagio", "").replace("júnior", "").replace("junior", "").strip()
        termo_encoded = urllib.parse.quote(termo_limpo if termo_limpo else termo)
        
        url = f"{self.url_base}?jobName={termo_encoded}&workplaceType=remote"

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
                page.wait_for_selector("script#__NEXT_DATA__", state="attached", timeout=20000)
                conteudo_html = page.content()

            except Exception as e:
                print(f"[{self.fonte}] Erro ao carregar portal via Playwright: {e}")
                conteudo_html = ""

            finally:
                browser.close()

        if not conteudo_html:
            return []

        soup = BeautifulSoup(conteudo_html, "html.parser")
        script_next = soup.find("script", id="__NEXT_DATA__")

        vagas_brutas = []
        if script_next and script_next.string:
            try:
                dados_json = json.loads(script_next.string)
                page_props = dados_json.get("props", {}).get("pageProps", {})

                # Busca o array de vagas nas diferentes estruturas possíveis do Next.js
                if "jobData" in page_props and isinstance(page_props["jobData"], dict):
                    vagas_brutas = page_props["jobData"].get("data", [])
                elif "jobs" in page_props and isinstance(page_props["jobs"], dict):
                    vagas_brutas = page_props["jobs"].get("data", [])
                elif "data" in page_props and isinstance(page_props["data"], list):
                    vagas_brutas = page_props["data"]
                    
            except Exception as e:
                print(f"[{self.fonte}] Erro ao processar JSON __NEXT_DATA__: {e}")

        for item in vagas_brutas:
            if not isinstance(item, dict):
                continue

            titulo = item.get("name", "").strip()
            
            link = item.get("jobUrl", "").strip()
            if not link and item.get("id"):
                link = f"https://portal.gupy.io/job/{item.get('id')}"

            empresa = item.get("companyName", "Empresa não informada").strip()
            tipo_trabalho = item.get("workplaceType", "").lower()
            
            # Define a localização e garante o termo 'remoto' para o filtro
            is_remoto = tipo_trabalho == "remote" or "remoto" in tipo_trabalho
            localizacao = "Remoto" if is_remoto else item.get("city", "Brasil")

            descricao_curta = item.get("description", "")
            
            # Montando o texto incluindo a palavra 'remoto' explicitamente se for o caso
            texto_modalidade = "remoto home office" if is_remoto else ""
            texto_card_completo = f"{titulo} {empresa} {localizacao} {texto_modalidade} {descricao_curta}"

            # Validação via FiltroVagas
            if not FiltroVagas.validar_vaga(titulo=titulo, localizacao=localizacao, conteudo_card=texto_card_completo):
                continue

            link_limpo = link.split("?")[0]
            hash_calculado = self.gerar_hash(link_limpo, titulo)

            vagas.append({
                "hash_vaga": hash_calculado,
                "titulo": titulo,
                "empresa": empresa,
                "localizacao": localizacao,
                "url": link_limpo,
                "fonte": self.fonte
            })

        return vagas


if __name__ == "__main__":
    bot_gupy = GupyScraper()
    # Teste com 'Estágio' ou 'Júnior' para validar a filtragem
    resultado = bot_gupy.buscar_vagas(termo="Estágio", local="Brasil")

    print(f"\n[Gupy] Total de vagas validadas encontradas: {len(resultado)}")
    print("-" * 50)

    for vaga in resultado[:5]:
        print(f"Título: {vaga['titulo']}")
        print(f"Empresa: {vaga['empresa']}")
        print(f"Local: {vaga['localizacao']}")
        print(f"URL: {vaga['url']}")
        print(f"Hash: {vaga['hash_vaga']}")
        print("-" * 50)


        