import re
import sqlite3
from contextlib import closing
from pathlib import Path
from src.filters import normalizar


PALAVRAS_IGNORADAS_EMPRESA = ["grupo", "jobs", "vagas", "vaga", "carreiras", "empresa"]
REGEX_ESTAGIO = re.compile(r"(?<!\w)(estagio|estagiario|estagiaria|intern|internship)(?!\w)")


def chave_vaga(titulo, empresa):
    # Identifica a mesma vaga publicada em fontes diferentes: título igual + mesma 1ª palavra da empresa.
    # Sem empresa conhecida, não deduplica (devolve None) para não juntar vagas diferentes.
    empresa_norm = normalizar(empresa)
    if "nao informad" in empresa_norm or "confidencial" in empresa_norm:
        return None

    palavras = [p for p in empresa_norm.split() if p not in PALAVRAS_IGNORADAS_EMPRESA]
    if not palavras:
        return None

    titulo_norm = " ".join(normalizar(titulo).split())
    return f"{titulo_norm}|{palavras[0]}"


def classificar_tipo(titulo):
    titulo_norm = normalizar(titulo)
    if REGEX_ESTAGIO.search(titulo_norm):
        return "Estágio"
    if "trainee" in titulo_norm:
        return "Trainee"
    return "Júnior"


class GerenciadorBanco:
    def __init__(self, caminho_banco="data/vagas.db"):
        self.caminho_banco = caminho_banco
        Path(self.caminho_banco).parent.mkdir(parents=True, exist_ok=True)
        self.criar_tabelas()
        self.migrar_chave_dedup()

    def obter_conexao(self):
        conexao = sqlite3.connect(self.caminho_banco)
        conexao.row_factory = sqlite3.Row
        conexao.execute("PRAGMA foreign_keys = ON;")
        return conexao

    def criar_tabelas(self):
        query_sql = """
        CREATE TABLE IF NOT EXISTS vagas (
            id_vaga INTEGER PRIMARY KEY AUTOINCREMENT,
            hash_vaga TEXT NOT NULL UNIQUE,
            url TEXT NOT NULL UNIQUE,
            fonte TEXT NOT NULL,
            titulo TEXT NOT NULL,
            empresa TEXT DEFAULT 'Não informada',
            localizacao TEXT DEFAULT 'Não informado',
            descricao TEXT,
            modalidade TEXT DEFAULT 'Indefinido',
            tipo_vaga TEXT DEFAULT 'Outro',
            salario_texto TEXT DEFAULT 'Não informado',
            publicacao DATETIME,
            coletado_bot DATETIME DEFAULT CURRENT_TIMESTAMP,
            notificada BOOLEAN DEFAULT 0,
            ativa BOOLEAN DEFAULT 1,
            chave_dedup TEXT
        );

        CREATE TABLE IF NOT EXISTS notificacoes (
            id_notificacao INTEGER PRIMARY KEY AUTOINCREMENT,
            fk_id_vaga INTEGER NOT NULL,
            chat_id INTEGER NOT NULL,
            mensagem_id INTEGER,
            status VARCHAR NOT NULL,
            enviado DATETIME DEFAULT CURRENT_TIMESTAMP,
            mensagem_erro TEXT,
            FOREIGN KEY (fk_id_vaga) REFERENCES vagas(id_vaga) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS logs_coleta (
            id_log INTEGER PRIMARY KEY AUTOINCREMENT,
            fonte VARCHAR NOT NULL,
            vagas_encontradas INTEGER DEFAULT 0,
            vagas_salvas INTEGER DEFAULT 0,
            status VARCHAR NOT NULL,
            detalhes TEXT,
            executado_em DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """

        with closing(self.obter_conexao()) as conexao:
            with conexao:
                conexao.executescript(query_sql)

    def migrar_chave_dedup(self):
        # Para bancos criados antes desta versão: adiciona a coluna e preenche as vagas existentes
        with closing(self.obter_conexao()) as conexao:
            with conexao:
                colunas = [c["name"] for c in conexao.execute("PRAGMA table_info(vagas)").fetchall()]

                if "chave_dedup" not in colunas:
                    conexao.execute("ALTER TABLE vagas ADD COLUMN chave_dedup TEXT")

                    vistas = set()
                    linhas = conexao.execute(
                        "SELECT id_vaga, titulo, empresa FROM vagas ORDER BY id_vaga"
                    ).fetchall()

                    for linha in linhas:
                        chave = chave_vaga(linha["titulo"], linha["empresa"])
                        if chave and chave not in vistas:
                            vistas.add(chave)
                            conexao.execute(
                                "UPDATE vagas SET chave_dedup = ? WHERE id_vaga = ?",
                                (chave, linha["id_vaga"])
                            )

                conexao.execute(
                    "CREATE UNIQUE INDEX IF NOT EXISTS idx_vagas_chave_dedup ON vagas(chave_dedup)"
                )

    def salvar_vagas(self, vagas_input):
        if not vagas_input:
            return 0

        # Aceita tanto um dicionario isolado quanto uma lista de dicionarios
        if isinstance(vagas_input, dict):
            lista_vagas = [vagas_input]
        elif isinstance(vagas_input, list):
            lista_vagas = [v for v in vagas_input if isinstance(v, dict)]
        else:
            return 0

        if not lista_vagas:
            return 0

        query = """
        INSERT OR IGNORE INTO vagas(
            hash_vaga, url, fonte, titulo, empresa, localizacao,
            descricao, modalidade, tipo_vaga, salario_texto, chave_dedup
        ) VALUES (
            :hash_vaga, :url, :fonte, :titulo, :empresa, :localizacao,
            :descricao, :modalidade, :tipo_vaga, :salario_texto, :chave_dedup
        )
        """

        # Preenche chaves opcionais caso o scraper não as tenha enviado
        for vaga in lista_vagas:
            vaga.setdefault("hash_vaga", vaga.get("hash", ""))
            vaga.setdefault("empresa", "Não informada")
            vaga.setdefault("localizacao", "Não informado")
            vaga.setdefault("descricao", None)
            vaga.setdefault("modalidade", "Remoto")  # o filtro só deixa passar vagas remotas
            vaga.setdefault("tipo_vaga", classificar_tipo(vaga.get("titulo", "")))
            vaga.setdefault("salario_texto", "Não informado")
            vaga["chave_dedup"] = chave_vaga(vaga.get("titulo", ""), vaga["empresa"])

        with closing(self.obter_conexao()) as conexao:
            with conexao:
                cursor = conexao.executemany(query, lista_vagas)
                return cursor.rowcount

    def contar_vagas(self, fonte=None):
        with closing(self.obter_conexao()) as conexao:
            if fonte:
                linha = conexao.execute("SELECT COUNT(*) AS total FROM vagas WHERE fonte = ?", (fonte,)).fetchone()
            else:
                linha = conexao.execute("SELECT COUNT(*) AS total FROM vagas").fetchone()
            return linha["total"]

    def buscar_vagas_nao_notificadas(self, limite=10):
        query = """
        SELECT * FROM vagas
        WHERE notificada = 0 AND ativa = 1
        ORDER BY coletado_bot ASC
        LIMIT ?
        """

        with closing(self.obter_conexao()) as conexao:
            linhas = conexao.execute(query, (limite,)).fetchall()
            return [dict(linha) for linha in linhas]

    def marcar_como_notificada(self, id_vaga):
        with closing(self.obter_conexao()) as conexao:
            with conexao:
                conexao.execute("UPDATE vagas SET notificada = 1 WHERE id_vaga = ?", (id_vaga,))

    def marcar_todas_como_notificadas(self):
        with closing(self.obter_conexao()) as conexao:
            with conexao:
                cursor = conexao.execute("UPDATE vagas SET notificada = 1 WHERE notificada = 0")
                return cursor.rowcount

    def registrar_log(self, fonte, encontradas, salvas, status, detalhes=None):
        query = """
        INSERT INTO logs_coleta (fonte, vagas_encontradas, vagas_salvas, status, detalhes)
        VALUES (?, ?, ?, ?, ?)
        """

        with closing(self.obter_conexao()) as conexao:
            with conexao:
                conexao.execute(query, (fonte, encontradas, salvas, status, detalhes))


if __name__ == "__main__":
    db = GerenciadorBanco()
    db.criar_tabelas()
    print("Banco de Dados criado com sucesso!")
