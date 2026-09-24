class FiltroVagas:
    TERMOS_INTERNACIONAIS = [
        "summer", "internship", "intern (", "united states", 
        "global", "north america", "usa", "canada", "europe"
    ]

    TERMOS_NIVEL_ENTRADA = [
        "estágio", "estagio", "estagiário", "estagiario", 
        "júnior", "junior", "jr", "desenvolvedor i", "developer i", 
        "trainee", "associate", "analista de sistemas", "assistente"
    ]

    TERMOS_EXCLUIR_NIVEL = [
        "sênior", "senior", "pleno", "lead", "coordenador", 
        "gerente", "head", "principal", "sr", "tech lead"
    ]

    TERMOS_REMOTOS = [
        "remoto", "home office", "teletrabalho", "anywhere", "remote"
    ]

    TERMOS_PRESENCIAIS = [
        "presencial", "híbrido", "hibrido"
    ]

    @classmethod
    def validar_vaga(cls, titulo: str, localizacao: str = "", conteudo_card: str = "") -> bool:
        """
        Retorna True se a vaga passar por todos os filtros de validação.
        """
        titulo_lower = titulo.lower()
        texto_completo = f"{titulo_lower} {localizacao.lower()} {conteudo_card.lower()}"

        # 1. Filtro Internacional
        if any(termo in titulo_lower for termo in cls.TERMOS_INTERNACIONAIS):
            return False

        # 2. Filtro de Nível (Exclusão): Descarta Sênior, Pleno, Lead
        if any(termo in titulo_lower for termo in cls.TERMOS_EXCLUIR_NIVEL):
            return False

        # 3. Filtro de Nível (Inclusão): Garante que é Estágio/Júnior
        if not any(termo in titulo_lower for termo in cls.TERMOS_NIVEL_ENTRADA):
            return False

        # 4. Filtro de Presencial/Híbrido: Descarta se contiver no título ou no card
        if any(termo in texto_completo for termo in cls.TERMOS_PRESENCIAIS):
            return False

        # 5. Trava de Trabalho Remoto: Confirma se existe algum termo que valide Home Office
        if not any(termo in texto_completo for termo in cls.TERMOS_REMOTOS):
            return False

        return True