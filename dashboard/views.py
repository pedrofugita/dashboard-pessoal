from django.shortcuts import render
import requests
from datetime import datetime

def buscar_dados_completos():
    dados = {
        'cryptos': [],
        'dolar': 0,
        'clima': None, # Novo campo
        'erro': None
    }
    
    try:
        # 1. Criptos (USD)
        url_crypto = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=6&page=1&sparkline=true"
        response_crypto = requests.get(url_crypto)
        lista_criptos = response_crypto.json()

        # 2. Dólar
        url_dolar = "https://economia.awesomeapi.com.br/last/USD-BRL"
        response_dolar = requests.get(url_dolar)
        valor_dolar = float(response_dolar.json()['USDBRL']['bid'])
        
        # Conversão USD -> BRL
        for moeda in lista_criptos:
            moeda['preco_brl'] = moeda['current_price'] * valor_dolar
            
        dados['cryptos'] = lista_criptos
        dados['dolar'] = valor_dolar

        # 3. Clima (Open-Meteo API)
        lat = "-22.89"
        lng = "-48.44"
        url_clima = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lng}&current=temperature_2m,weather_code&timezone=America%2FSao_Paulo"
        
        response_clima = requests.get(url_clima)
        clima_json = response_clima.json()
        
        dados['clima'] = {
            'temp': clima_json['current']['temperature_2m'],
            'codigo': clima_json['current']['weather_code']
        }
        
    except Exception as e:
        dados['erro'] = "Erro ao buscar dados."
    
    return dados

def home(request):
    info = buscar_dados_completos()
    return render(request, 'dashboard/home.html', info)

def atualizar_valores(request):
    info = buscar_dados_completos()
    # Retorna apenas os cards para o HTMX
    return render(request, 'dashboard/cards.html', info)