# src/filters.py

class FiltroVagas:
    # Palavras-chave obrigatórias no título ou conteúdo para nível de entrada
    TERMOS_NIVEL_ENTRADA = [
        "estagio", "estágio", "estagiario", "estagiária", "trainee",
        "junior", "júnior", "jr", "inicial", "entry level", "assistant", "assistente"
    ]

    # Palavras-chave de tecnologia / desenvolvimento
    TERMOS_TECNOLOGIA = [
        "desenvolvedor", "desenvolvedora", "developer", "dev", "software",
        "programador", "programadora", "ti", "tecnologia", "web", "frontend",
        "backend", "fullstack", "full-stack", "java", "python", "c#", "dotnet",
        ".net", "php", "react", "node", "angular", "vue", "data", "dados",
        "sistemas", "computacao", "computação", "engenharia de software"
    ]

    # Palavras estritamente proibidas no TÍTULO (níveis seniores)
    TERMOS_PROIBIDOS_TITULO = [
        "pleno", "pl", "senior", "sênior", "sr", "lead", "tech lead",
        "especialista", "coordenador", "gerente", "head", "principal", "expert"
    ]

    # Indicadores de vaga remota
    TERMOS_REMOTO = [
        "remoto", "remote", "home office", "home-office", "teletrabalho", "100% remoto"
    ]

    @classmethod
    def validar_vaga(cls, titulo: str, localizacao: str, conteudo_card: str = "") -> bool:
        titulo_lower = titulo.lower()
        local_lower = localizacao.lower()
        conteudo_lower = conteudo_card.lower()

        #SOMENTE REMOTAS
        eh_remoto = (
            any(termo in local_lower for termo in cls.TERMOS_REMOTO) or
            any(termo in titulo_lower for termo in cls.TERMOS_REMOTO) or
            "remoto" in conteudo_lower
        )
        if not eh_remoto:
            return False

        # Bloqueio de vagas de nível Pleno/Sênior no TÍTULO
        if any(termo in titulo_lower for termo in cls.TERMOS_PROIBIDOS_TITULO):
            return False

        #Validação de Nível de Entrada (Estágio / Júnior / Jr)
        tem_nivel_entrada = any(termo in titulo_lower or termo in conteudo_lower for termo in cls.TERMOS_NIVEL_ENTRADA)
        if not tem_nivel_entrada:
            return False

        #Validação de Área (Desenvolvimento / TI / Engenharia)
        tem_tecnologia = any(termo in titulo_lower or termo in conteudo_lower for termo in cls.TERMOS_TECNOLOGIA)
        if not tem_tecnologia:
            return False

        return True