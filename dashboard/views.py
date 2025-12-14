from django.shortcuts import render
from django.http import HttpResponse
import requests
import psutil
import pynvml
import subprocess
import re
import time
import os
from dotenv import load_dotenv
import pyautogui
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from .models import Anotacao

load_dotenv() # <--- Isso lê o arquivo .env
SPOTIPY_CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID')
SPOTIPY_CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET')
SPOTIPY_REDIRECT_URI = os.getenv('SPOTIPY_REDIRECT_URI')

# Configuração de Autenticação
scope = "user-read-playback-state user-modify-playback-state"

# Cria o objeto de autenticação globalmente
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=SPOTIPY_CLIENT_ID,
    client_secret=SPOTIPY_CLIENT_SECRET,
    redirect_uri=SPOTIPY_REDIRECT_URI,
    scope=scope
))

def buscar_dados_completos():
    dados = {
        'cryptos': [], 'dolar': 0, 'clima': None,
        'sistema': {
            'cpu': 0, 'ram_percent': 0, 'ram_total': 0, 'ram_used': 0,
            'discos': [], 'gpu': None,
            'rede': {'ping': 0, 'nome': '...', 'download_mbps': 0, 'upload_mbps': 0, 'percent_down': 0, 'percent_up': 0}
        },
        'spotify': None, # <--- NOVO CAMPO
        'erro': None
    }
    
    try:
        # --- 1. SPOTIFY API ---
        try:
            current = sp.current_playback()
            if current and current.get('item'):
                track = current['item']
                dados['spotify'] = {
                    'tocando': current['is_playing'],
                    'nome': track['name'],
                    'artista': track['artists'][0]['name'],
                    'capa': track['album']['images'][0]['url'], # Imagem grande
                    'link': track['external_urls']['spotify'],
                    # Progresso em porcentagem
                    'progresso_ms': current['progress_ms'],
                    'duracao_ms': track['duration_ms'],
                    'percent': (current['progress_ms'] / track['duration_ms']) * 100
                }
            else:
                # Se nada estiver tocando ou Spotify fechado
                dados['spotify'] = None
        except Exception as e:
            print(f"Erro Spotify: {e}")
            dados['spotify'] = None

        # --- 2. HARDWARE (MANTIDO) ---
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
                    'total': round(uso.total / (1024**3), 0), 'tipo': 'SSD/Sistema' if 'C' in p.device else 'HDD/Dados'
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
            dados['sistema']['gpu'] = {'nome': nome, 'load': util.gpu, 'temp': temp, 'mem_total': round(mem_info.total / (1024**3), 1), 'mem_used': round(mem_info.used / (1024**3), 1)}
            pynvml.nvmlShutdown()
        except: dados['sistema']['gpu'] = None

        # --- 3. REDE (MANTIDO) ---
        stats = psutil.net_if_stats()
        nome_rede = "Desconectado"; tipo_conexao = "wifi"
        if 'Ethernet' in stats and stats['Ethernet'].isup: nome_rede = "Rede Cabeada (100Mbps)"; tipo_conexao = "ethernet"
        elif 'Wi-Fi' in stats and stats['Wi-Fi'].isup:
            tipo_conexao = "wifi"
            try:
                wifi_cmd = subprocess.run(['netsh', 'wlan', 'show', 'interfaces'], capture_output=True, text=True, encoding='cp850')
                ssid_match = re.search(r'SSID\s*:\s*(.*)', wifi_cmd.stdout)
                nome_rede = ssid_match.group(1).strip() if ssid_match else "Wi-Fi"
            except: nome_rede = "Wi-Fi"
        dados['sistema']['rede']['nome'] = nome_rede; dados['sistema']['rede']['tipo'] = tipo_conexao

        io_1 = psutil.net_io_counters(); time.sleep(0.5); io_2 = psutil.net_io_counters()
        mbps_down = ((io_2.bytes_recv - io_1.bytes_recv) * 2 * 8) / 1_000_000
        mbps_up = ((io_2.bytes_sent - io_1.bytes_sent) * 2 * 8) / 1_000_000
        dados['sistema']['rede']['download_mbps'] = round(mbps_down, 1)
        dados['sistema']['rede']['upload_mbps'] = round(mbps_up, 1)
        dados['sistema']['rede']['percent_down'] = round((mbps_down/100)*100 if (mbps_down/100)*100 <= 100 else 100, 1)
        dados['sistema']['rede']['percent_up'] = round((mbps_up/100)*100 if (mbps_up/100)*100 <= 100 else 100, 1)

        try:
            ping_cmd = subprocess.run(['ping', '-n', '1', '-w', '1000', '8.8.8.8'], capture_output=True, text=True)
            if "tempo=" in ping_cmd.stdout: ping_ms = int(re.search(r'tempo=(\d+)', ping_cmd.stdout).group(1))
            elif "time=" in ping_cmd.stdout: ping_ms = int(re.search(r'time=(\d+)', ping_cmd.stdout).group(1))
            else: ping_ms = 999
        except: ping_ms = 0
        dados['sistema']['rede']['ping'] = ping_ms

        # --- 4. DADOS EXTERNOS ---
        url_crypto = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=6&page=1&sparkline=true"
        response_crypto = requests.get(url_crypto)
        dados['cryptos'] = response_crypto.json()
        
        url_dolar = "https://economia.awesomeapi.com.br/last/USD-BRL"
        response_dolar = requests.get(url_dolar)
        valor_dolar = float(response_dolar.json()['USDBRL']['bid'])
        for moeda in dados['cryptos']: moeda['preco_brl'] = moeda['current_price'] * valor_dolar
        dados['dolar'] = valor_dolar

        lat = os.getenv('MY_LAT')
        lng = os.getenv('MY_LNG')
        url_clima = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lng}&current=temperature_2m,weather_code&timezone=America%2FSao_Paulo"
        clima_json = requests.get(url_clima).json()
        dados['clima'] = {'temp': clima_json['current']['temperature_2m'], 'codigo': clima_json['current']['weather_code']}
        
    except Exception as e:
        dados['erro'] = f"Erro: {str(e)}"
    
    return dados

# --- ENDPOINTS ---
def home(request):
    info = buscar_dados_completos()
    
    notas = Anotacao.objects.order_by('-criado_em')
    info['notas'] = notas 
    
    return render(request, 'dashboard/home.html', info)

def atualizar_valores(request):
    info = buscar_dados_completos()
    return render(request, 'dashboard/cards.html', info)

def executar_acao(request, comando):
    # Mantemos sua função de controle via OS/PyAutoGUI aqui
    try:
        if comando == 'calc': subprocess.Popen('calc.exe')
        elif comando == 'vol_up': pyautogui.press('volumeup'); pyautogui.press('volumeup')
        elif comando == 'vol_down': pyautogui.press('volumedown'); pyautogui.press('volumedown')
        elif comando == 'play': pyautogui.press('playpause')
        elif comando == 'next': pyautogui.press('nexttrack')
        elif comando == 'prev': pyautogui.press('prevtrack')
        # ... seus outros comandos ...
    except: pass
    return HttpResponse(status=204)

# --- FUNÇÕES DO LOG DE BORDO ---
def adicionar_nota(request):
    if request.method == "POST":
        texto_nota = request.POST.get('texto')
        if texto_nota:
            Anotacao.objects.create(texto=texto_nota)
    
    # Retorna apenas a lista atualizada (HTML parcial)
    notas = Anotacao.objects.order_by('-criado_em')
    return render(request, 'dashboard/partials/lista_notas.html', {'notas': notas})

def deletar_nota(request, nota_id):
    try:
        nota = Anotacao.objects.get(id=nota_id)
        nota.delete()
    except:
        pass
    
    # Retorna apenas a lista atualizada
    notas = Anotacao.objects.order_by('-criado_em')
    return render(request, 'dashboard/partials/lista_notas.html', {'notas': notas})