import re
import unicodedata

def normalizar(texto):
    # Remove acentos e deixa tudo minúsculo
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.lower()


def compilar(termos):
    partes = sorted({re.escape(normalizar(t)) for t in termos}, key=len, reverse=True)
    return re.compile(r"(?<!\w)(?:" + "|".join(partes) + r")(?!\w)")


class FiltroVagas:
    # Nível de entrada
    TERMOS_NIVEL_ENTRADA = [
        "estagio", "estagiario", "estagiaria", "trainee",
        "junior", "jr", "inicial", "entry level", "assistant", "assistente"
    ]

    # Tecnologia / desenvolvimento
    TERMOS_TECNOLOGIA = [
        "desenvolvedor", "desenvolvedora", "developer", "dev", "software",
        "programador", "programadora", "ti", "tecnologia", "sistemas",
        "computacao", "engenharia de software", "engineer",
        "web", "frontend", "front-end", "backend", "back-end",
        "fullstack", "full-stack", "mobile", "android", "ios",
        "java", "python", "c#", "dotnet", ".net", "asp.net", "php", "javascript",
        "typescript", "react", "node", "angular", "vue", "golang", "ruby",
        "dados", "analista de dados", "engenharia de dados",
        "data analyst", "data engineer", "data scientist", "ia", "ai",
        "inteligencia artificial", "artificial intelligence", "bi", "analytics",
        "qa", "quality assurance", "tester", "testes",
        "devops", "cloud", "infraestrutura", "suporte"
    ]

    # Proibidos no título (níveis seniores)
    TERMOS_PROIBIDOS_TITULO = [
        "pleno", "pl", "senior", "sr", "lead", "tech lead",
        "especialista", "coordenador", "gerente", "head", "principal", "expert"
    ]

    # Indicadores de vaga remota e de vaga não remota
    TERMOS_REMOTO = [
        "remoto", "remote", "home office", "home-office", "teletrabalho", "100% remoto"
    ]
    TERMOS_NAO_REMOTO = ["presencial", "hibrido", "hybrid", "on-site", "onsite"]

    # Compiladas uma vez, quando a classe é carregada
    REGEX_NIVEL = compilar(TERMOS_NIVEL_ENTRADA)
    REGEX_TECNOLOGIA = compilar(TERMOS_TECNOLOGIA)
    REGEX_PROIBIDOS = compilar(TERMOS_PROIBIDOS_TITULO)
    REGEX_REMOTO = compilar(TERMOS_REMOTO)
    REGEX_NAO_REMOTO = compilar(TERMOS_NAO_REMOTO)

    @classmethod
    def avaliar(cls, titulo, localizacao, conteudo_card=""):
        """Retorna (aprovada, motivo). O motivo ajuda a entender por que uma vaga caiu."""
        titulo = normalizar(titulo)
        local = normalizar(localizacao)
        conteudo = normalizar(conteudo_card)

        #Somente remotas
        if cls.REGEX_NAO_REMOTO.search(local):
            return False, "nao_remoto"

        eh_remoto = (
            cls.REGEX_REMOTO.search(local)
            or cls.REGEX_REMOTO.search(titulo)
            or (cls.REGEX_REMOTO.search(conteudo) and not cls.REGEX_NAO_REMOTO.search(conteudo))
        )
        if not eh_remoto:
            return False, "nao_remoto"

        #Bloqueia pleno/sênior no título
        if cls.REGEX_PROIBIDOS.search(titulo):
            return False, "nivel_senior"

        #Nível de entrada (título ou card)
        if not (cls.REGEX_NIVEL.search(titulo) or cls.REGEX_NIVEL.search(conteudo)):
            return False, "sem_nivel_entrada"

        #Tecnologia: no título, ou pelo menos 2 termos diferentes no card
        tem_tec_no_titulo = cls.REGEX_TECNOLOGIA.search(titulo)
        termos_no_card = set(cls.REGEX_TECNOLOGIA.findall(conteudo))
        if not (tem_tec_no_titulo or len(termos_no_card) >= 2):
            return False, "sem_tecnologia"

        return True, "ok"

    @classmethod
    def validar_vaga(cls, titulo, localizacao, conteudo_card=""):
        aprovada, motivo = cls.avaliar(titulo, localizacao, conteudo_card)
        return aprovada