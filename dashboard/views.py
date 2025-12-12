from django.shortcuts import render
import requests
import psutil
import pynvml # <--- Esta é a biblioteca nova da NVIDIA
from datetime import datetime

def buscar_dados_completos():
    dados = {
        'cryptos': [],
        'dolar': 0,
        'clima': None,
        'sistema': {
            'cpu': 0,
            'ram_percent': 0,
            'ram_total': 0,
            'ram_used': 0,
            'discos': [],
            'gpu': None
        },
        'erro': None
    }
    
    try:
        # --- 1. HARDWARE BÁSICO ---
        dados['sistema']['cpu'] = psutil.cpu_percent(interval=None)
        
        # RAM
        mem = psutil.virtual_memory()
        dados['sistema']['ram_percent'] = mem.percent
        dados['sistema']['ram_total'] = round(mem.total / (1024**3), 1)
        dados['sistema']['ram_used'] = round(mem.used / (1024**3), 1)
        
        # DISCOS
        particoes = psutil.disk_partitions()
        for p in particoes:
            try:
                if 'cdrom' in p.opts or p.fstype == '':
                    continue
                uso = psutil.disk_usage(p.mountpoint)
                dados['sistema']['discos'].append({
                    'letra': p.device,
                    'percent': uso.percent,
                    'total': round(uso.total / (1024**3), 0),
                    'tipo': 'SSD/Sistema' if 'C' in p.device else 'HDD/Dados'
                })
            except:
                pass

        # --- 2. PLACA DE VÍDEO (NVIDIA) ---
        try:
            pynvml.nvmlInit() # Inicia a biblioteca
            handle = pynvml.nvmlDeviceGetHandleByIndex(0) # Pega a primeira placa (GPU 0)
            
            # Nome da Placa
            nome = pynvml.nvmlDeviceGetName(handle)
            # Em versões novas do Python, isso pode vir como bytes, então convertemos
            if isinstance(nome, bytes):
                nome = nome.decode('utf-8')

            # Uso e Memória
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)

            dados['sistema']['gpu'] = {
                'nome': nome,
                'load': util.gpu, # Porcentagem de uso
                'temp': temp,
                'mem_total': round(mem_info.total / (1024**3), 1), # GB
                'mem_used': round(mem_info.used / (1024**3), 1)    # GB
            }
            pynvml.nvmlShutdown() # Fecha a conexão
            
        except Exception as e:
            # Se não tiver NVIDIA ou der erro, fica None e não quebra o site
            dados['sistema']['gpu'] = None 

        # --- 3. DADOS DE REDE (CRIPTO/DOLAR/CLIMA) ---
        url_crypto = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=6&page=1&sparkline=true"
        response_crypto = requests.get(url_crypto)
        lista_criptos = response_crypto.json()

        url_dolar = "https://economia.awesomeapi.com.br/last/USD-BRL"
        response_dolar = requests.get(url_dolar)
        valor_dolar = float(response_dolar.json()['USDBRL']['bid'])
        
        for moeda in lista_criptos:
            moeda['preco_brl'] = moeda['current_price'] * valor_dolar
            
        dados['cryptos'] = lista_criptos
        dados['dolar'] = valor_dolar

        lat = "-23.5505" # SP
        lng = "-46.6333"
        url_clima = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lng}&current=temperature_2m,weather_code&timezone=America%2FSao_Paulo"
        response_clima = requests.get(url_clima)
        clima_json = response_clima.json()
        dados['clima'] = {'temp': clima_json['current']['temperature_2m'], 'codigo': clima_json['current']['weather_code']}
        
    except Exception as e:
        dados['erro'] = f"Status: {str(e)}"
    
    return dados

def home(request):
    info = buscar_dados_completos()
    return render(request, 'dashboard/home.html', info)

def atualizar_valores(request):
    info = buscar_dados_completos()
    return render(request, 'dashboard/cards.html', info)