from django.shortcuts import render
import requests
import psutil
import pynvml
import subprocess
import re
import time 

def buscar_dados_completos():
    dados = {
        'cryptos': [],
        'dolar': 0,
        'clima': None,
        'sistema': {
            'cpu': 0, 'ram_percent': 0, 'ram_total': 0, 'ram_used': 0,
            'discos': [], 'gpu': None,
            'rede': {
                'ping': 0, 
                'nome': 'Desconectado', 
                'download_mbps': 0, 
                'upload_mbps': 0,
                'percent_down': 0, # Mudei o nome para ficar claro
                'percent_up': 0    # NOVO: Porcentagem do Upload
            }
        },
        'erro': None
    }
    
    try:
        # --- 1. HARDWARE ---
        dados['sistema']['cpu'] = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        dados['sistema']['ram_percent'] = mem.percent
        dados['sistema']['ram_total'] = round(mem.total / (1024**3), 1)
        dados['sistema']['ram_used'] = round(mem.used / (1024**3), 1)
        
        particoes = psutil.disk_partitions()
        for p in particoes:
            try:
                if 'cdrom' in p.opts or p.fstype == '': continue
                uso = psutil.disk_usage(p.mountpoint)
                dados['sistema']['discos'].append({
                    'letra': p.device, 'percent': uso.percent,
                    'total': round(uso.total / (1024**3), 0),
                    'tipo': 'SSD/Sistema' if 'C' in p.device else 'HDD/Dados'
                })
            except: pass

        # GPU
        try:
            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            nome = pynvml.nvmlDeviceGetName(handle)
            if isinstance(nome, bytes): nome = nome.decode('utf-8')
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
            dados['sistema']['gpu'] = {
                'nome': nome, 'load': util.gpu, 'temp': temp,
                'mem_total': round(mem_info.total / (1024**3), 1),
                'mem_used': round(mem_info.used / (1024**3), 1)
            }
            pynvml.nvmlShutdown()
        except: dados['sistema']['gpu'] = None

        # --- 2. REDE ---
        stats = psutil.net_if_stats()
        nome_rede = "Desconectado"
        tipo_conexao = "wifi"
        
        if 'Ethernet' in stats and stats['Ethernet'].isup:
            nome_rede = "Rede Cabeada (100Mbps)" 
            tipo_conexao = "ethernet"
        elif 'Wi-Fi' in stats and stats['Wi-Fi'].isup:
            tipo_conexao = "wifi"
            try:
                wifi_cmd = subprocess.run(['netsh', 'wlan', 'show', 'interfaces'], capture_output=True, text=True, encoding='cp850')
                ssid_match = re.search(r'SSID\s*:\s*(.*)', wifi_cmd.stdout)
                if ssid_match:
                    nome_rede = ssid_match.group(1).strip()
            except:
                nome_rede = "Wi-Fi"

        dados['sistema']['rede']['nome'] = nome_rede
        dados['sistema']['rede']['tipo'] = tipo_conexao

        # Velocidade
        io_1 = psutil.net_io_counters()
        time.sleep(0.5) 
        io_2 = psutil.net_io_counters()
        
        bytes_down_sec = (io_2.bytes_recv - io_1.bytes_recv) * 2
        bytes_up_sec = (io_2.bytes_sent - io_1.bytes_sent) * 2
        
        mbps_down = (bytes_down_sec * 8) / 1_000_000
        mbps_up = (bytes_up_sec * 8) / 1_000_000
        
        dados['sistema']['rede']['download_mbps'] = round(mbps_down, 1)
        dados['sistema']['rede']['upload_mbps'] = round(mbps_up, 1)
        
        # CÁLCULO DAS BARRAS (Base 100 Mbps)
        # Download
        p_down = (mbps_down / 100) * 100
        dados['sistema']['rede']['percent_down'] = round(p_down if p_down <= 100 else 100, 1)
        
        # Upload (NOVO)
        p_up = (mbps_up / 100) * 100
        dados['sistema']['rede']['percent_up'] = round(p_up if p_up <= 100 else 100, 1)

        # Ping
        try:
            ping_cmd = subprocess.run(['ping', '-n', '1', '-w', '1000', '8.8.8.8'], capture_output=True, text=True)
            if "tempo=" in ping_cmd.stdout: 
                ping_ms = int(re.search(r'tempo=(\d+)', ping_cmd.stdout).group(1))
            elif "time=" in ping_cmd.stdout:
                ping_ms = int(re.search(r'time=(\d+)', ping_cmd.stdout).group(1))
            else:
                ping_ms = 999
        except:
            ping_ms = 0
        dados['sistema']['rede']['ping'] = ping_ms

        # --- 3. DADOS EXTERNOS ---
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

        lat = "-23.5505"
        lng = "-46.6333"
        url_clima = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lng}&current=temperature_2m,weather_code&timezone=America%2FSao_Paulo"
        response_clima = requests.get(url_clima)
        clima_json = response_clima.json()
        dados['clima'] = {'temp': clima_json['current']['temperature_2m'], 'codigo': clima_json['current']['weather_code']}
        
    except Exception as e:
        dados['erro'] = f"Erro: {str(e)}"
    
    return dados

def home(request):
    info = buscar_dados_completos()
    return render(request, 'dashboard/home.html', info)

def atualizar_valores(request):
    info = buscar_dados_completos()
    return render(request, 'dashboard/cards.html', info)