from django.shortcuts import render, redirect
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
from django.conf import settings
from .models import Anotacao

load_dotenv()

# === CONFIGURAÇÃO DE AUTENTICAÇÃO ===
# O objeto sp_oauth gerencia a "burocracia" do token
sp_oauth = SpotifyOAuth(
    client_id=settings.SPOTIPY_CLIENT_ID,
    client_secret=settings.SPOTIPY_CLIENT_SECRET,
    redirect_uri=settings.SPOTIPY_REDIRECT_URI,
    scope=settings.SPOTIFY_SCOPE, # Lendo do settings.py atualizado
    cache_path='.cache'
)

# === FUNÇÃO AUXILIAR: CRIA O CLIENTE ===
def get_spotify_client(request):
    """
    Tenta obter o cliente (sp) autenticado.
    Retorna None se o usuário não estiver logado.
    """
    token_info = sp_oauth.get_cached_token()
    
    # Se não achar no cache, tenta pegar da URL (callback de login)
    if not token_info:
        code = request.GET.get('code')
        if code:
            token_info = sp_oauth.get_access_token(code)
            
    if token_info:
        return spotipy.Spotify(auth=token_info['access_token'])
    return None

# === FUNÇÃO AUXILIAR: FORMATAR TEMPO ===
def formatar_tempo(ms):
    """Transforma milissegundos (230000) em texto (3:50)"""
    if not ms: return "0:00"
    segundos = int((ms / 1000) % 60)
    minutos = int((ms / (1000 * 60)) % 60)
    return f"{minutos}:{segundos:02d}"

# === BUSCA DE DADOS (Agora recebe 'sp' como argumento) ===
def buscar_dados_completos(sp=None):
    dados = {
        'cryptos': [], 'dolar': 0, 'clima': None,
        'sistema': {
            'cpu': 0, 'ram_percent': 0, 'ram_total': 0, 'ram_used': 0,
            'discos': [], 'gpu': None,
            'rede': {'ping': 0, 'nome': '...', 'download_mbps': 0, 'upload_mbps': 0, 'percent_down': 0, 'percent_up': 0}
        },
        'spotify': None,
        'erro': None
    }
    
    try:
        # --- 1. SPOTIFY API ---
        if sp:
            try:
                current = sp.current_playback()
                if current and current.get('item'):
                    track = current['item']
                    track_id = track['id']
                    
                    # Verifica se deu Like (API Extra)
                    is_liked = False
                    try:
                        # Retorna lista de booleans [True] ou [False]
                        is_liked = sp.current_user_saved_tracks_contains(tracks=[track_id])[0]
                    except: pass

                    dados['spotify'] = {
                        'tocando': current['is_playing'],
                        'nome': track['name'],
                        'artista': track['artists'][0]['name'],
                        'capa': track['album']['images'][0]['url'],
                        'link_externo': track['external_urls']['spotify'], # <--- Para o botão "Abrir"
                        
                        # Tempos
                        'progresso_ms': current['progress_ms'],
                        'duracao_ms': track['duration_ms'],
                        'tempo_atual': formatar_tempo(current['progress_ms']),
                        'tempo_total': formatar_tempo(track['duration_ms']),
                        'percent': (current['progress_ms'] / track['duration_ms']) * 100,
                        
                        # Controles
                        'is_liked': is_liked,
                        'shuffle_state': current['shuffle_state']
                    }
            except Exception as e:
                print(f"Erro leitura Spotify: {e}")
                dados['spotify'] = None

        # --- 2. HARDWARE (MANTIDO IGUAL) ---
        dados['sistema']['cpu'] = psutil.cpu_percent(interval=None)
        
        # Temperatura CPU (Tentativa WMI para Windows)
        try:
            import wmi
            import pythoncom
            pythoncom.CoInitialize()
            w = wmi.WMI(namespace="root\\wmi")
            temp = w.MSAcpi_ThermalZoneTemperature()[0].CurrentTemperature
            dados['sistema']['cpu_temp'] = round((temp / 10.0) - 273.15, 1)
        except:
            dados['sistema']['cpu_temp'] = "--"

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
                    'letra': p.device.replace('\\', ''), 
                    'percent': uso.percent,
                    'total': round(uso.total / (1024**3), 0), 
                    'tipo': 'SSD/Sys' if 'C' in p.device else 'HDD/Data'
                })
            except: pass

        # GPU
        try:
            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            nome = pynvml.nvmlDeviceGetName(handle)
            # Correção para string em Python 3
            if not isinstance(nome, str): nome = nome.decode('utf-8') 
            
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
            
            # Tenta pegar consumo de energia (Watts)
            try: power = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000
            except: power = 0
            try: power_limit = pynvml.nvmlDeviceGetEnforcedPowerLimit(handle) / 1000
            except: power_limit = 0
            try: fan = pynvml.nvmlDeviceGetFanSpeed(handle)
            except: fan = 0

            dados['sistema']['gpu'] = {
                'nome': nome, 
                'load': util.gpu, 
                'temp': temp, 
                'mem_total': round(mem_info.total / (1024**3), 1), 
                'mem_used': round(mem_info.used / (1024**3), 1),
                'power_draw': power,
                'power_limit': power_limit,
                'fan_speed': fan
            }
            pynvml.nvmlShutdown()
        except: dados['sistema']['gpu'] = None

        # --- 3. REDE (MANTIDO) ---
        stats = psutil.net_if_stats()
        nome_rede = "Desconectado"; tipo_conexao = "wifi"
        if 'Ethernet' in stats and stats['Ethernet'].isup: 
            nome_rede = "Rede Cabeada"; tipo_conexao = "ethernet"
        elif 'Wi-Fi' in stats and stats['Wi-Fi'].isup:
            try:
                wifi_cmd = subprocess.run(['netsh', 'wlan', 'show', 'interfaces'], capture_output=True, text=True, encoding='cp850')
                ssid_match = re.search(r'SSID\s*:\s*(.*)', wifi_cmd.stdout)
                nome_rede = ssid_match.group(1).strip() if ssid_match else "Wi-Fi"
            except: nome_rede = "Wi-Fi"
        dados['sistema']['rede']['nome'] = nome_rede

        io_1 = psutil.net_io_counters(); time.sleep(0.1); io_2 = psutil.net_io_counters() # Reduzi sleep para 0.1 p/ nao travar
        mbps_down = ((io_2.bytes_recv - io_1.bytes_recv) * 8 * 10) / 1_000_000 # *10 pois sleep é 0.1
        mbps_up = ((io_2.bytes_sent - io_1.bytes_sent) * 8 * 10) / 1_000_000
        
        dados['sistema']['rede']['download_mbps'] = round(mbps_down, 1)
        dados['sistema']['rede']['upload_mbps'] = round(mbps_up, 1)

        # Ping
        try:
            # -w 500 para ser mais rápido
            ping_cmd = subprocess.run(['ping', '-n', '1', '-w', '500', '8.8.8.8'], capture_output=True, text=True)
            if "tempo=" in ping_cmd.stdout: ping_ms = int(re.search(r'tempo=(\d+)', ping_cmd.stdout).group(1))
            elif "time=" in ping_cmd.stdout: ping_ms = int(re.search(r'time=(\d+)', ping_cmd.stdout).group(1))
            else: ping_ms = 0
        except: ping_ms = 0
        dados['sistema']['rede']['ping'] = ping_ms

        # --- 4. DADOS EXTERNOS ---
        # (Se a API cair, usamos try catch para não quebrar o painel inteiro)
        try:
            url_crypto = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=bitcoin,ethereum,solana,ripple,cardano,polkadot"
            response_crypto = requests.get(url_crypto, timeout=2) # Timeout para não travar
            dados['cryptos'] = response_crypto.json()
            
            url_dolar = "https://economia.awesomeapi.com.br/last/USD-BRL"
            response_dolar = requests.get(url_dolar, timeout=2)
            valor_dolar = float(response_dolar.json()['USDBRL']['bid'])
            dados['dolar'] = valor_dolar
            
            # Converte para BRL
            if isinstance(dados['cryptos'], list):
                for moeda in dados['cryptos']: 
                    moeda['preco_brl'] = moeda['current_price'] * valor_dolar
        except: pass # Ignora erro de API externa

        # Clima
        try:
            lat = os.getenv('MY_LAT', '-23.55')
            lng = os.getenv('MY_LNG', '-46.63')
            url_clima = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lng}&current=temperature_2m,weather_code&timezone=America%2FSao_Paulo"
            clima_json = requests.get(url_clima, timeout=2).json()
            dados['clima'] = {'temp': clima_json['current']['temperature_2m'], 'codigo': clima_json['current']['weather_code']}
        except: pass
        
    except Exception as e:
        dados['erro'] = f"Erro Geral: {str(e)}"
    
    return dados

# --- ENDPOINTS (VIEWS) ---

def home(request):
    sp = get_spotify_client(request) # Cria cliente
    info = buscar_dados_completos(sp) # Passa cliente
    
    notas = Anotacao.objects.order_by('-criado_em')
    info['notas'] = notas 
    
    return render(request, 'dashboard/home.html', info)

def atualizar_valores(request):
    sp = get_spotify_client(request) # Cria cliente
    info = buscar_dados_completos(sp) # Passa cliente
    return render(request, 'dashboard/cards.html', info)

# --- COMANDOS DO SPOTIFY (VIA API) ---
def comando_spotify(request, comando):
    sp = get_spotify_client(request)
    if not sp: return HttpResponse(status=204)

    try:
        if comando == 'next': sp.next_track()
        elif comando == 'prev': sp.previous_track()
        elif comando == 'play':
            current = sp.current_playback()
            if current and current['is_playing']: sp.pause_playback()
            else: sp.start_playback()
            
        elif comando == 'shuffle':
            current = sp.current_playback()
            novo_estado = not current['shuffle_state']
            sp.shuffle(novo_estado)
            
        elif comando == 'like':
            current = sp.current_playback()
            if current and current.get('item'):
                track_id = current['item']['id']
                ja_curtiu = sp.current_user_saved_tracks_contains(tracks=[track_id])[0]
                if ja_curtiu:
                    sp.current_user_saved_tracks_delete(tracks=[track_id])
                else:
                    sp.current_user_saved_tracks_add(tracks=[track_id])
                    
        # Controles de Volume (Mantivemos PyAutoGUI para controlar o PC todo, não só o Spotify)
        elif comando == 'vol_up': 
            pyautogui.press('volumeup'); pyautogui.press('volumeup')
        elif comando == 'vol_down': 
            pyautogui.press('volumedown'); pyautogui.press('volumedown')

    except Exception as e:
        print(f"Erro comando: {e}")

    return HttpResponse(status=204)

def login_spotify(request):
    # Gera o link oficial de login do Spotify com as permissões novas
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

def callback(request):
    code = request.GET.get('code')
    if code:
        sp_oauth.get_access_token(code)
    return redirect('home')

# --- NOTAS ---
def adicionar_nota(request):
    if request.method == "POST":
        texto_nota = request.POST.get('texto')
        if texto_nota:
            Anotacao.objects.create(texto=texto_nota)
    notas = Anotacao.objects.order_by('-criado_em')
    return render(request, 'dashboard/partials/lista_notas.html', {'notas': notas})

def deletar_nota(request, nota_id):
    try:
        nota = Anotacao.objects.get(id=nota_id)
        nota.delete()
    except: pass
    notas = Anotacao.objects.order_by('-criado_em')
    return render(request, 'dashboard/partials/lista_notas.html', {'notas': notas})