import json
import re
from playwright.sync_api import sync_playwright
from .base import BaseScraper
from src.filters import FiltroVagas


class GupyScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.fonte = "Gupy"
        self.url_base = "https://portal.gupy.io/job-search"

    def extrair_empresa_dinamica(self, item, link):
        candidatos = [
            item.get("careerPageName"),
            item.get("companyName")
        ]
        
        for cand in candidatos:
            if cand and str(cand).strip() and str(cand).lower() not in ["none", "null", "empresa não informada"]:
                if "sanguelaranja" in str(cand).lower():
                    return "FCamara"
                return str(cand).strip()

        # 2. Se não houver, extrai dinamicamente do subdomínio da URL
        try:
            match = re.search(r"https?://([^.]+)\.gupy\.io", link)
            if match:
                subdominio = match.group(1).lower()
                if subdominio not in ["portal", "confidencial"]:
                    return subdominio.replace("-", " ").replace("_", " ").title()
        except Exception:
            pass

        return "Empresa não informada"

    def buscar_vagas(self, termo=None, local="Brasil"):
        vagas = []

        termos_busca = [
            "desenvolvedor junior",
            "estagio desenvolvimento",
            "estagio ti",
            "desenvolvedor java",
            "desenvolvedor python"
        ] if not termo else [termo]

        vagas_brutas_todas = []

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-setuid-sandbox"
                ]
            )

            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800}
            )

            page = context.new_page()

            # Listener de rede para interceptar respostas JSON da API de busca
            def interceptar_resposta(response):
                nonlocal vagas_brutas_todas
                url_resp = response.url.lower()
                if "job" in url_resp and response.status == 200:
                    try:
                        dados = response.json()
                        if isinstance(dados, dict) and "data" in dados and len(dados["data"]) > 0:
                            vagas_brutas_todas.extend(dados["data"])
                    except Exception:
                        pass

            page.on("response", interceptar_resposta)

            try:
                for t in termos_busca:
                    # Força a atualização da página para garantir que o React dispare uma nova requisição XHR
                    page.goto(self.url_base, wait_until="domcontentloaded", timeout=60000)
                    page.wait_for_timeout(1500)

                    input_busca = page.locator('input[placeholder*="Busque por uma vaga"], input[type="text"]').first
                    if input_busca.is_visible():
                        input_busca.click()
                        page.keyboard.press("Control+A")
                        page.keyboard.press("Backspace")
                        page.keyboard.type(t, delay=30)

                        botao_buscar = page.locator('button:has-text("Buscar vagas")').first
                        if botao_buscar.is_visible():
                            botao_buscar.click()
                        else:
                            page.keyboard.press("Enter")

                        page.wait_for_timeout(3000)

            except Exception as e:
                print(f"[{self.fonte}] Erro no Playwright: {e}")
            finally:
                browser.close()

        print(f"[{self.fonte}] Total de vagas brutas capturadas: {len(vagas_brutas_todas)}")

        hashes_vistos = set()

        for item in vagas_brutas_todas:
            if not isinstance(item, dict):
                continue

            titulo = item.get("name", "").strip()
            if not titulo:
                continue

            link = item.get("jobUrl", "").strip()
            if not link and item.get("id"):
                link = f"https://portal.gupy.io/job/{item.get('id')}"

            # Extração dinâmica do nome da empresa
            empresa = self.extrair_empresa_dinamica(item, link)

            # Identificação do modelo de trabalho
            tipo_trabalho = str(item.get("workplaceType", "")).lower()
            is_remoto = "remote" in tipo_trabalho or "remoto" in tipo_trabalho
            localizacao = "Remoto" if is_remoto else "Presencial/Híbrido"

            descricao_curta = item.get("description", "")
            texto_card_completo = f"{titulo} {empresa} {localizacao} {descricao_curta}"

            # Filtro de somente remotas
            if not is_remoto and "remoto" not in titulo.lower() and "remoto" not in descricao_curta.lower():
                continue

            link_limpo = link.split("?")[0]
            hash_calculado = self.gerar_hash(link_limpo, titulo)

            if hash_calculado in hashes_vistos:
                continue

            # Validação centralizada via FiltroVagas
            if not FiltroVagas.validar_vaga(titulo=titulo, localizacao=localizacao, conteudo_card=texto_card_completo):
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

        return vagas


if __name__ == "__main__":
    bot_gupy = GupyScraper()
    resultado = bot_gupy.buscar_vagas()

    print(f"\n[Gupy] Total de vagas validadas final: {len(resultado)}")
    print("-" * 50)

    for vaga in resultado:
        print(f"Título: {vaga['titulo']}")
        print(f"Empresa: {vaga['empresa']}")
        print(f"Local: {vaga['localizacao']}")
        print(f"URL: {vaga['url']}")
        print("-" * 50)

        