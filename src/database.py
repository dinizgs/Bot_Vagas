import sqlite3
from pathlib import Path

class GerenciadorBanco:
    def __init__(self, caminho_banco="data/vagas.db"):
        self.caminho_banco = caminho_banco
        Path(self.caminho_banco).parent.mkdir(parents=True, exist_ok=True)

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
            ativa BOOLEAN DEFAULT 1
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

        with self.obter_conexao() as conexao:
            conexao.executescript(query_sql)

    def salvar_vagas(self, lista_vagas):
        query = """
        INSERT OR IGNORE INTO vagas(
            hash_vaga, url, fonte, titulo, empresa, localizacao,
            descricao, modalidade, tipo_vaga, salario_texto
        ) VALUES (
            :hash_vaga, :url, :fonte, :titulo, :empresa, :localizacao,
            :descricao, :modalidade, :tipo_vaga, :salario_texto
        )
        """

        # Preenche chaves opcionais caso o scraper não as tenha enviado
        for vaga in lista_vagas:
            vaga.setdefault("hash_vaga", vaga.get("hash"))
            vaga.setdefault("descricao", None)
            vaga.setdefault("modalidade", "Indefinido")
            vaga.setdefault("tipo_vaga", "Outro")
            vaga.setdefault("salario_texto", "Não informado")

        with self.obter_conexao() as conexao:
            cursor = conexao.executemany(query, lista_vagas)
            conexao.commit()
            return cursor.rowcount # Retorna a quantidade de novas vagas salvas

    def buscar_vagas_nao_notificadas(self, limite=10):
        query = """
        SELECT * FROM vagas
        WHERE notificada = 0 AND ativa = 1
        ORDER BY coletado_bot ASC
        LIMIT ?
        """

        with self.obter_conexao() as conexao:
            cursor = conexao.cursor()
            return cursor.execute(query, (limite,)).fetchall()

    def marcar_como_notificada(self, id_vaga):
        query = "UPDATE vagas SET notificada = 1 WHERE id_vaga = ?"

        with self.obter_conexao() as conexao: # Correção: adicionado ()
            conexao.execute(query, (id_vaga,))
            conexao.commit()

    def registrar_log(self, fonte, encontradas, salvas, status, detalhes=None):
        query = """
        INSERT INTO logs_coleta (fonte, vagas_encontradas, vagas_salvas, status, detalhes)
        VALUES (?, ?, ?, ?, ?)
        """

        with self.obter_conexao() as conexao: 
            conexao.execute(query, (fonte, encontradas, salvas, status, detalhes))
            conexao.commit()


if __name__ == "__main__":
    db = GerenciadorBanco()
    db.criar_tabelas()
    print("Banco de Dados criado com sucesso!")
