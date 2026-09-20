import requests, hashlib

class BaseScraper:
    def __init__(self):

        #Isso é para o site não recusar o acesso e dizer que é um robô
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://br.jooble.org/",
            "Sec-Ch-Ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Upgrade-Insecure-Requests": "1"
        }

    def gerar_hash(self, url, titulo):
        texto_unico_hash = f"{url.strip()}-{titulo.strip().lower()}"

        return hashlib.sha256(texto_unico_hash.encode("utf-8")).hexdigest()
        #Transforma em bytes, calcula o SHA-256 e retorna como string hexadecimal

    def buscar_vagas(self):
        raise NotImplementedError("Cada scrapper precisa implementar o método de buscar vagas.")