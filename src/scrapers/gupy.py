import re
import time
import random
from collections import Counter
from datetime import datetime, timezone
from urllib.parse import urlencode, quote
import requests
from .base import BaseScraper
from src.filters import FiltroVagas
from src.config import (
    USER_AGENT,
    HTTP_TIMEOUT,
    GUPY_LIMITE_POR_PAGINA,
    GUPY_MAX_PAGINAS,
    DELAY_MIN,
    DELAY_MAX
)


def prazo_vencido(prazo_texto):
    if not prazo_texto:
        return False
    try:
        prazo = datetime.fromisoformat(prazo_texto.replace("Z", "+00:00"))
    except ValueError:
        return False
    return prazo < datetime.now(timezone.utc)


class GupyScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.fonte = "Gupy"
        self.url_api = "https://portal.gupy.io/api/job-search/jobs"

        # Quantas vagas pedir por página e quantas páginas ler por termo (vindas do config.py)
        self.limite_por_pagina = GUPY_LIMITE_POR_PAGINA
        self.max_paginas = GUPY_MAX_PAGINAS

        self.filtro_remoto_na_api = {"workplaceType": "remote"}

        self.headers = {
            "User-Agent": USER_AGENT,
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
            resposta = requests.get(url, headers=self.headers, timeout=HTTP_TIMEOUT)
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

        # Termos curtos e amplos (Pensando no contexto da Gupy)
        termos_busca = [
            # Nível
            "estagio", "estágio", "estagiario", "estagiária", "trainee",
            "junior", "júnior", "jr",

            # Desenvolvimento
            "desenvolvedor", "desenvolvedora", "pessoa desenvolvedora",
            "programador", "software", "dev",
            "backend", "frontend", "full stack", "fullstack", "mobile",
            "python", "java", "react", "node",

            # TI, dados e áreas próximas
            "ti", "tecnologia",
            "analista de sistemas", "dados", "ia",
            "qa", "testes", "devops", "infraestrutura", "suporte"
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
                time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

            print(f"[{self.fonte}] '{t}': {total_termo} vagas")

            # Aviso se o termo bateu no limite de páginas (pode haver mais vagas)
            if total_termo >= self.limite_por_pagina * self.max_paginas:
                print(f"[{self.fonte}] Aviso: '{t}' atingiu o limite de páginas, pode haver mais vagas")

            time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

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

            # Empresas inativas geram links quebrados
            if "inactive" in link:
                motivos["empresa_inativa"] += 1
                continue

            # Prazo de inscrição já encerrado
            if prazo_vencido(item.get("applicationDeadline")):
                motivos["vencida"] += 1
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

        