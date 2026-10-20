import re
import time
import random
from collections import Counter
from urllib.parse import urlencode, quote
import requests
from .base import BaseScraper
from src.filters import FiltroVagas


class GupyScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.fonte = "Gupy"
        self.url_api = "https://portal.gupy.io/api/job-search/jobs"

        # Quantas vagas pedir por página e quantas páginas ler por termo
        self.limite_por_pagina = 100
        self.max_paginas = 5

        # Filtro de remoto na própria API (nome do parâmetro NÃO confirmado, veja a nota abaixo).
        # Se a API der erro por causa dele, troque por {}. O filtro local continua valendo.
        self.filtro_remoto_na_api = {"workplaceType": "remote"}

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Referer": "https://portal.gupy.io/job-search"
        }

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

        # Se não houver, extrai do subdomínio da URL
        try:
            match = re.search(r"https?://([^.]+)\.gupy\.io", link)
            if match:
                subdominio = match.group(1).lower()
                if subdominio not in ["portal", "confidencial"]:
                    return subdominio.replace("-", " ").replace("_", " ").title()
        except Exception:
            pass

        return "Empresa não informada"

    def _buscar_pagina(self, termo, offset):
        params = {"jobName": termo, "limit": self.limite_por_pagina, "offset": offset}
        params.update(self.filtro_remoto_na_api)
        url = f"{self.url_api}?{urlencode(params, quote_via=quote)}"

        try:
            resposta = requests.get(url, headers=self.headers, timeout=30)
        except Exception as e:
            print(f"[{self.fonte}] Erro de conexão em '{termo}' (offset {offset}): {e}")
            return []

        if resposta.status_code != 200:
            print(f"[{self.fonte}] HTTP {resposta.status_code} em '{termo}' (offset {offset}): {resposta.text[:150]}")
            return []

        try:
            dados = resposta.json()
        except Exception:
            print(f"[{self.fonte}] Resposta não é JSON em '{termo}' (offset {offset})")
            return []

        if isinstance(dados, dict) and isinstance(dados.get("data"), list):
            return dados["data"]
        return []

    def buscar_vagas(self, termo=None, local="Brasil"):
        vagas = []

        # Contador de motivos de descarte e exemplos de títulos
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
            "pessoa desenvolvedora junior",
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
            "pessoa analista de dados",
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

        for t in termos_busca:
            total_termo = 0

            for pagina in range(self.max_paginas):
                offset = pagina * self.limite_por_pagina
                lista = self._buscar_pagina(t, offset)
                total_termo += len(lista)
                vagas_brutas.extend(lista)

                # Se veio menos que o limite, era a última página
                if len(lista) < self.limite_por_pagina:
                    break
                time.sleep(random.uniform(0.4, 0.9))

            print(f"[{self.fonte}] '{t}': {total_termo} vagas")
            time.sleep(random.uniform(0.5, 1.0))

        print(f"[{self.fonte}] Total de vagas brutas capturadas: {len(vagas_brutas)}")

        hashes_vistos = set()
        total_remotas_brutas = 0

        for item in vagas_brutas:
            if not isinstance(item, dict):
                continue

            titulo = (item.get("name") or "").strip()
            if not titulo:
                motivos["sem_titulo"] += 1
                continue

            link = (item.get("jobUrl") or "").strip()
            if not link and item.get("id"):
                link = f"https://portal.gupy.io/job/{item.get('id')}"

            # Empresas inativas geram links quebrados (ex.: terras&15719&inactive.gupy.io)
            if "inactive" in link:
                motivos["empresa_inativa"] += 1
                continue

            empresa = self.extrair_empresa_dinamica(item, link)

            # Modalidade de trabalho, direto do campo da API
            tipo_trabalho = str(item.get("workplaceType") or "").lower()
            if "remote" in tipo_trabalho or "remoto" in tipo_trabalho:
                localizacao = "Remoto"
                total_remotas_brutas += 1
            elif tipo_trabalho:
                localizacao = "Presencial/Híbrido"
            else:
                # Sem o campo: só considera remota se o título disser
                localizacao = "Remoto" if "remoto" in titulo.lower() else "Não informado"

            if localizacao == "Presencial/Híbrido":
                motivos["nao_remoto"] += 1
                if len(exemplos.setdefault("nao_remoto", [])) < 5:
                    exemplos["nao_remoto"].append(titulo)
                continue

            descricao_curta = item.get("description") or ""
            texto_card_completo = f"{titulo} {empresa} {localizacao} {descricao_curta}"

            link_limpo = link.split("?")[0]
            hash_calculado = self.gerar_hash(link_limpo, titulo)

            if hash_calculado in hashes_vistos:
                motivos["duplicada"] += 1
                continue

            # Validação centralizada via FiltroVagas, com o motivo do descarte
            aprovada, motivo = FiltroVagas.avaliar(titulo=titulo, localizacao=localizacao, conteudo_card=texto_card_completo)
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

        print(f"[{self.fonte}] Remotas entre as brutas: {total_remotas_brutas}")
        print(f"[{self.fonte}] Motivos de descarte: {dict(motivos)}")
        for motivo, titulos in exemplos.items():
            print(f"   {motivo}: {titulos}")

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

        