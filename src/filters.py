import re
import unicodedata


def normalizar(texto):
    # Remove acentos e deixa tudo minúsculo
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.lower()


def compilar(termos):
    # Monta uma regex que casa o termo como palavra inteira
    # (assim "ia" não casa dentro de "midia", nem "pl" dentro de "aplicativo")
    partes = sorted({re.escape(normalizar(t)) for t in termos}, key=len, reverse=True)
    return re.compile(r"(?<!\w)(?:" + "|".join(partes) + r")(?!\w)")


class FiltroVagas:
    # Nível de entrada
    TERMOS_NIVEL_ENTRADA = [
        "estagio", "estagiario", "estagiaria", "trainee", "intern", "internship",
        "junior", "jr", "inicial", "entry level", "associate", "assistant", "assistente",
        "iniciante",
    ]

    # Termos FORTES de desenvolvimento
    TERMOS_TECNOLOGIA_FORTES = [
        "desenvolvedor", "desenvolvedora", "desenvolvimento", "developer", "dev", "software",
        "programador", "programadora", "programacao", "engineer", "engenheiro de software",
        "engenharia de software", "backend", "back-end", "back end", "frontend", "front-end",
        "front end", "fullstack", "full-stack", "full stack", "mobile", "android", "ios",
        "java", "python", "c#", "dotnet", ".net", "asp.net", "php", "javascript", "typescript",
        "react", "node", "angular", "vue", "golang", "ruby", "kotlin", "devops", "qa", "q.a",
        "ti", "t.i", "it", "tech", "business intelligence",
    ]

    # Todos os termos de tecnologia
    TERMOS_TECNOLOGIA = TERMOS_TECNOLOGIA_FORTES + [
        "ti", "tecnologia", "tecnologia da informacao", "sistemas", "sistema", "informatica",
        "firmware", "computacao", "web",
        "dados", "analista de dados", "engenharia de dados", "engenheiro de dados",
        "cientista de dados", "data", "machine learning", "ml", "ia", "ai",
        "inteligencia artificial", "artificial intelligence", "bi", "analytics",
        "quality assurance", "tester", "testes", "cloud", "infraestrutura",
        "seguranca da informacao", "ciberseguranca", "soc", "sre",
        "sap", "erp", "servicenow", "salesforce", "rpa", "monitoracao",
        # Suporte: só as formas explícitas de TI
        "suporte tecnico", "suporte ti", "help desk", "helpdesk", "service desk",
        "suporte n1", "suporte n2", "suporte n3"
    ]

    # Proibidos no título (níveis seniores)
    TERMOS_PROIBIDOS_TITULO = [
        "pleno", "pl", "senior", "sr", "lead", "tech lead",
        "especialista", "coordenador", "gerente", "head", "principal", "expert",
        "mid-level", "mid level", "mid", "middle"
    ]

    # Áreas que não são TI. Derrubam a vaga se o título NÃO tiver termo forte de desenvolvimento
    TERMOS_FORA_DE_TI = [
        "negocios", "comercial", "vendas", "sales", "bdr", "sdr", "customer success",
        "marketing", "growth", "seo",
        "recursos humanos", "rh", "recrutamento", "selecao",
        "contabil", "contabilidade", "contador", "fiscal", "tributaria", "tributario",
        "financeiro", "financeira", "controladoria", "atuarial",
        "juridico", "direito", "administrativo", "logistica",
        "atendimento", "geoprocessamento", "academico",
        "riscos", "controles internos", "compliance", "privacidade", "lgpd", "dpo",
        "banco de talentos"
    ]

    # Indicadores de vaga remota e de vaga não remota
    TERMOS_REMOTO = [
        "remoto", "remote", "home office", "home-office", "teletrabalho", "100% remoto"
    ]
    TERMOS_NAO_REMOTO = ["presencial", "hibrido", "hybrid", "on-site", "onsite"]

    # Regexes prontas (compiladas uma vez, quando a classe é carregada)
    REGEX_NIVEL = compilar(TERMOS_NIVEL_ENTRADA)
    REGEX_TECNOLOGIA_FORTE = compilar(TERMOS_TECNOLOGIA_FORTES)
    REGEX_TECNOLOGIA = compilar(TERMOS_TECNOLOGIA)
    REGEX_PROIBIDOS = compilar(TERMOS_PROIBIDOS_TITULO)
    REGEX_FORA_DE_TI = compilar(TERMOS_FORA_DE_TI)
    REGEX_REMOTO = compilar(TERMOS_REMOTO)
    REGEX_NAO_REMOTO = compilar(TERMOS_NAO_REMOTO)

    @classmethod
    def avaliar(cls, titulo, localizacao, conteudo_card=""):
        """Retorna (aprovada, motivo). O motivo ajuda a entender por que uma vaga caiu."""
        titulo = normalizar(titulo)
        local = normalizar(localizacao)
        conteudo = normalizar(conteudo_card)

        # 1. Somente remotas
        if cls.REGEX_NAO_REMOTO.search(local):
            return False, "nao_remoto"

        eh_remoto = (
            cls.REGEX_REMOTO.search(local)
            or cls.REGEX_REMOTO.search(titulo)
            or (cls.REGEX_REMOTO.search(conteudo) and not cls.REGEX_NAO_REMOTO.search(conteudo))
        )
        if not eh_remoto:
            return False, "nao_remoto"

        # 2. Bloqueia pleno/sênior no título
        if cls.REGEX_PROIBIDOS.search(titulo):
            return False, "nivel_senior"

        # 3. Área fora de TI
        if cls.REGEX_FORA_DE_TI.search(titulo) and not cls.REGEX_TECNOLOGIA_FORTE.search(titulo):
            return False, "fora_de_ti"

        # 4. Nível de entrada (título ou card)
        if not (cls.REGEX_NIVEL.search(titulo) or cls.REGEX_NIVEL.search(conteudo)):
            return False, "sem_nivel_entrada"

        if not cls.REGEX_TECNOLOGIA.search(titulo):
            return False, "sem_tecnologia"

        return True, "ok"

    @classmethod
    def validar_vaga(cls, titulo, localizacao, conteudo_card=""):
        aprovada, motivo = cls.avaliar(titulo, localizacao, conteudo_card)
        return aprovada

    @classmethod
    def avaliar_titulo(cls, titulo):
        titulo = normalizar(titulo)

        if cls.REGEX_PROIBIDOS.search(titulo):
            return False, "nivel_senior"
        if cls.REGEX_FORA_DE_TI.search(titulo) and not cls.REGEX_TECNOLOGIA_FORTE.search(titulo):
            return False, "fora_de_ti"
        if not cls.REGEX_TECNOLOGIA.search(titulo):
            return False, "sem_tecnologia"
        return True, "ok"