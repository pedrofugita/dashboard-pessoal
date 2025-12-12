from django.shortcuts import render
import requests

def buscar_dados_completos():
    dados = {
        'cryptos': [],
        'dolar': 0,
        'erro': None
    }
    
    try:
        # 1. Busca Criptos em USD
        url_crypto = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=6&page=1&sparkline=true"
        response_crypto = requests.get(url_crypto)
        lista_criptos = response_crypto.json()

        # 2. Busca Dólar (USD -> BRL)
        url_dolar = "https://economia.awesomeapi.com.br/last/USD-BRL"
        response_dolar = requests.get(url_dolar)
        valor_dolar = float(response_dolar.json()['USDBRL']['bid'])
        
        # 3. MÁGICA: Adicionamos o preço em Reais dentro de cada cripto
        # Assim o HTML não precisa fazer conta
        for moeda in lista_criptos:
            moeda['preco_brl'] = moeda['current_price'] * valor_dolar
            
        dados['cryptos'] = lista_criptos
        dados['dolar'] = valor_dolar
        
    except Exception as e:
        dados['erro'] = "Erro ao buscar dados."
    
    return dados

def home(request):
    info = buscar_dados_completos()
    return render(request, 'dashboard/home.html', info)

def atualizar_valores(request):
    info = buscar_dados_completos()
    return render(request, 'dashboard/cards.html', info)