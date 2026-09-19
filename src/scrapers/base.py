import requests, hashlib

class BaseScraper:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7"
        }

    def gerar_hash(self, url, titulo):
        texto_unico_hash = f"{url.strip()}-{titulo.strip().lower()}"

        return hashlib.sha256(texto_unico_hash.encode("utf-8")).hexdigest()
        #Transforma em bytes, calcula o SHA-256 e retorna como string hexadecimal

    def buscar_vagas(self):
        raise NotImplementedError("Cada scrapper precisa implementar o método de buscar vagas.")