import re
import time
import random
from collections import Counter
import requests
from bs4 import BeautifulSoup
from .base import BaseScraper
from src.filters import FiltroVagas, normalizar, compilar
from src.config import (
    USER_AGENT,
    HTTP_TIMEOUT,
    LINKEDIN_MAX_PAGINAS,
    LINKEDIN_MAX_DETALHES,
    LINKEDIN_JANELA_INICIAL,
    DELAY_MIN,
    DELAY_MAX
)


REGEX_REMOTO = compilar(["remoto", "remote", "home office", "home-office", "teletrabalho", "100% remoto"])
REGEX_NAO_REMOTO = compilar(["presencial", "hibrido", "hybrid", "on-site", "onsite"])

# Rótulos de nível de experiência do LinkedIn que indicam vaga de entrada
NIVEIS_ENTRADA_LINKEDIN = ["estagio", "pouca experiencia", "entry level", "internship"]

# Textos prováveis de vaga que já não aceita candidaturas
PADROES_ENCERRADA = [
    "no longer accepting applications", "nao aceita mais candidaturas",
    "nao estamos mais aceitando", "deixou de aceitar candidaturas"
]


def detectar_remoto(titulo, localizacao, descricao):
    t = normalizar(titulo)
    l = normalizar(localizacao)
    d = normalizar(descricao)

    if REGEX_REMOTO.search(t) or REGEX_REMOTO.search(l):
        return True
    if REGEX_NAO_REMOTO.search(t):
        return False
    # Descrição diz remoto e não menciona presencial/híbrido
    if REGEX_REMOTO.search(d) and not REGEX_NAO_REMOTO.search(d):
        return True
    return False


class LinkedinScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.fonte = "LinkedIn"
        self.url_busca = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
        self.url_detalhe = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{}"

        # Ajustes vindos do config.py
        self.max_paginas = LINKEDIN_MAX_PAGINAS        
        self.max_detalhes = LINKEDIN_MAX_DETALHES         
        self.janela = LINKEDIN_JANELA_INICIAL       
        self.bloqueado = False         

        self.sessao = requests.Session()
        self.sessao.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8"
        })

    def _get(self, url, params=None):
        for tentativa in range(3):
            try:
                resposta = self.sessao.get(url, params=params, timeout=HTTP_TIMEOUT)
            except Exception as e:
                print(f"[{self.fonte}] Erro de conexão: {e}")
                time.sleep(3)
                continue

            if resposta.status_code == 200:
                return resposta.text

            if resposta.status_code in (429, 999):
                espera = 20 * (tentativa + 1)
                print(f"[{self.fonte}] Limite de requisições (HTTP {resposta.status_code}). Aguardando {espera}s...")
                time.sleep(espera)
                continue

            return ""

        self.bloqueado = True
        print(f"[{self.fonte}] Sem acesso após 3 tentativas. Encerrando as buscas desta rodada.")
        return ""

    def _extrair_id(self, card, href):
        achou = re.search(r"(\d{6,})/?$", href)
        if achou:
            return achou.group(1)
        el = card.find(attrs={"data-entity-urn": True})
        if el:
            achou = re.search(r"(\d{6,})", el["data-entity-urn"])
            if achou:
                return achou.group(1)
        return None

    def _extrair_cards(self, html):
        soup = BeautifulSoup(html, "html.parser")
        resultado = []

        for card in soup.find_all("li"):
            link_el = card.select_one("a.base-card__full-link") or card.find(
                "a", href=lambda h: h and "/jobs/view/" in h
            )
            if not link_el:
                continue

            href = link_el.get("href", "").split("?")[0]
            id_vaga = self._extrair_id(card, href)
            if not id_vaga:
                continue

            el_titulo = card.select_one(".base-search-card__title")
            el_empresa = card.select_one(".base-search-card__subtitle")
            el_local = card.select_one(".job-search-card__location")

            titulo = el_titulo.get_text(strip=True) if el_titulo else link_el.get_text(strip=True)
            if not titulo:
                continue

            resultado.append({
                "id": id_vaga,
                "titulo": titulo,
                "empresa": el_empresa.get_text(strip=True) if el_empresa else "Empresa não informada",
                "localizacao": el_local.get_text(strip=True) if el_local else "Não informado",
                "url": href
            })

        return resultado

    def _extrair_detalhes(self, html):
        soup = BeautifulSoup(html, "html.parser")

        el_desc = soup.select_one(".show-more-less-html__markup") or soup.select_one(".description__text")
        descricao = el_desc.get_text(" ", strip=True) if el_desc else ""

        nivel = ""
        for item in soup.select("li.description__job-criteria-item"):
            cabecalho = item.select_one(".description__job-criteria-subheader")
            valor = item.select_one(".description__job-criteria-text")
            if cabecalho and valor:
                rotulo = normalizar(cabecalho.get_text(strip=True))
                if "nivel" in rotulo or "seniority" in rotulo:
                    nivel = valor.get_text(strip=True)

        return descricao, nivel

    def buscar_vagas(self, termo=None, local="Brasil"):
        vagas = []

        # Contador de motivos de descarte e exemplos de títulos
        motivos = Counter()
        exemplos = {}

        def registrar_descarte(motivo, titulo, localizacao=""):
            motivos[motivo] += 1
            if len(exemplos.setdefault(motivo, [])) < 5:
                exemplos[motivo].append(f"{titulo} | {localizacao}" if localizacao else titulo)

        # O LinkedIn ignora filtros de nível e modalidade, então o nível vai nas palavras-chave
        termos_busca = [
            "estágio ti", "estágio tecnologia", "estágio desenvolvimento", "estágio desenvolvedor",
            "estágio dados", "estágio qa", "estágio suporte ti",
            "desenvolvedor júnior", "desenvolvedor jr", "pessoa desenvolvedora júnior",
            "desenvolvedor backend júnior", "desenvolvedor frontend júnior", "desenvolvedor fullstack júnior",
            "desenvolvedor mobile júnior", "desenvolvedor java júnior", "desenvolvedor python júnior",
            "desenvolvedor react júnior", "desenvolvedor node júnior",
            "analista de sistemas júnior", "analista de dados júnior", "engenheiro de dados júnior",
            "cientista de dados júnior", "qa júnior", "analista de testes júnior",
            "devops júnior", "suporte ti júnior", "ti júnior",
            "desenvolvedor júnior remoto", "estágio ti remoto", "estágio desenvolvimento remoto"
        ] if not termo else [termo]

        # Coleta (com paginação) e remove repetidas pelo id da vaga
        candidatos = {}

        for t in termos_busca:
            if self.bloqueado:
                break

            novos = 0
            for pagina in range(self.max_paginas):
                params = {
                    "keywords": t,
                    "location": local,
                    "geoId": "106057199",
                    "f_TPR": self.janela,
                    "start": pagina * 25
                }
                html = self._get(self.url_busca, params)
                if not html:
                    break

                cards = self._extrair_cards(html)
                if not cards:
                    break

                for c in cards:
                    if c["id"] not in candidatos:
                        candidatos[c["id"]] = c
                        novos += 1

                time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

            print(f"[{self.fonte}] '{t}': {novos} vagas novas (únicas até agora: {len(candidatos)})")

        print(f"[{self.fonte}] Total de vagas brutas capturadas: {len(candidatos)}")

        # Triagem pelo título, antes de abrir a página de cada vaga
        pre_aprovados = []
        for c in candidatos.values():
            ok, motivo = FiltroVagas.avaliar_titulo(c["titulo"])
            if not ok:
                registrar_descarte(motivo, c["titulo"], c["localizacao"])
                continue
            pre_aprovados.append(c)

        # Prioriza quem já tem estágio/júnior no título e limita a quantidade de páginas abertas
        pre_aprovados.sort(key=lambda c: 0 if FiltroVagas.REGEX_NIVEL.search(normalizar(c["titulo"])) else 1)

        if len(pre_aprovados) > self.max_detalhes:
            motivos["alem_do_limite_de_detalhes"] += len(pre_aprovados) - self.max_detalhes
            pre_aprovados = pre_aprovados[:self.max_detalhes]

        print(f"[{self.fonte}] Após triagem pelo título: {len(pre_aprovados)} vagas para abrir")

        # Abre a página da vaga, lê descrição e nível, aplica o filtro completo
        hashes_vistos = set()

        for c in pre_aprovados:
            if self.bloqueado:
                break

            html = self._get(self.url_detalhe.format(c["id"]))
            time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

            if not html:
                registrar_descarte("sem_detalhe", c["titulo"], c["localizacao"])
                continue

            if any(p in normalizar(html) for p in PADROES_ENCERRADA):
                registrar_descarte("encerrada", c["titulo"], c["localizacao"])
                continue

            descricao, nivel = self._extrair_detalhes(html)

            eh_remoto = detectar_remoto(c["titulo"], c["localizacao"], descricao)
            nivel_norm = normalizar(nivel)
            nivel_entrada = any(n in nivel_norm for n in NIVEIS_ENTRADA_LINKEDIN)

            # O filtro recebe a modalidade e o nível já resolvidos
            local_para_filtro = "Remoto" if eh_remoto else c["localizacao"]
            conteudo_para_filtro = f"{c['titulo']} {'entry level' if nivel_entrada else ''}"

            aprovada, motivo = FiltroVagas.avaliar(
                titulo=c["titulo"],
                localizacao=local_para_filtro,
                conteudo_card=conteudo_para_filtro
            )
            if not aprovada:
                registrar_descarte(motivo, c["titulo"], c["localizacao"])
                continue

            link_limpo = c["url"]
            hash_calculado = self.gerar_hash(link_limpo, c["titulo"])
            if hash_calculado in hashes_vistos:
                motivos["duplicada"] += 1
                continue
            hashes_vistos.add(hash_calculado)

            cidade = c["localizacao"]
            localizacao_final = "Remoto" if cidade in ("Brasil", "Brazil", "Não informado") else f"Remoto ({cidade})"

            vagas.append({
                "hash_vaga": hash_calculado,
                "titulo": c["titulo"],
                "empresa": c["empresa"],
                "localizacao": localizacao_final,
                "url": link_limpo,
                "fonte": self.fonte
            })

        print(f"[{self.fonte}] Motivos de descarte: {dict(motivos)}")
        for motivo, titulos in exemplos.items():
            print(f"   {motivo}: {titulos}")

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