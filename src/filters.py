# src/filters.py

class FiltroVagas:
    # Palavras-chave obrigatórias no título ou conteúdo para nível de entrada
    TERMOS_NIVEL_ENTRADA = [
        "estagio", "estágio", "estagiario", "estagiária", "trainee",
        "junior", "júnior", "jr", "inicial", "entry level", "assistant", "assistente"
    ]

    # Palavras-chave de tecnologia / desenvolvimento
    TERMOS_TECNOLOGIA = [
        # Geral & Engenharia
        "desenvolvedor", "desenvolvedora", "developer", "dev", "software",
        "programador", "programadora", "ti", "tecnologia", "sistemas", 
        "computacao", "computação", "engenharia de software", "engineer",

        # Web & Mobile
        "web", "frontend", "front-end", "backend", "back-end", 
        "fullstack", "full-stack", "mobile", "android", "ios",

        # Linguagens & Frameworks
        "java", "python", "c#", "dotnet", ".net", "php", "javascript", 
        "typescript", "react", "node", "angular", "vue", "golang", "ruby",

        # Dados, IA & Analytics
        "data", "dados", "analista de dados", "engenharia de dados", 
        "data analyst", "data engineer", "data scientist", "ia", "ai", 
        "inteligencia artificial", "artificial intelligence", "bi", "analytics",

        # Qualidade, Testes & DevOps
        "qa", "quality assurance", "tester", "testes", 
        "devops", "cloud", "infraestrutura", "suporte"
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