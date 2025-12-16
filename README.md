# 🚀 Personal Dashboard

Um painel de controle pessoal e interativo desenvolvido com **Django** para monitoramento de hardware em tempo real, controle do Spotify e visualização de dados financeiros e climáticos.

O projeto possui uma estética **Cyberpunk / Automotive** com tema escuro e elementos em vidro (Glassmorphism).

![Status](https://img.shields.io/badge/Status-Em_Desenvolvimento-yellow)
![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Django](https://img.shields.io/badge/Django-4.0+-green)

## 📸 Funcionalidades

### 🖥️ Monitoramento de Hardware (Em Tempo Real)
- **CPU:** Uso (%), Frequência atual e Temperatura.
- **GPU (NVIDIA):** Suporte nativo via `pynvml` e fallback via `nvidia-smi`. Monitora Carga, Memória (VRAM) e Temperatura.
- **RAM:** Uso total, disponível e percentual.
- **Armazenamento:** Monitoramento de partições (SSD/HDD).
- **Rede:** Ping, Velocidade de Download/Upload e Nome da Rede (SSID).

### 🎵 Integração com Spotify
- Exibição da música atual, artista e capa do álbum.
- **Controles Completos:** Play/Pause, Próxima, Anterior, Shuffle e Like/Unlike.
- Barra de progresso sincronizada com a duração da música.
- Autenticação via **OAuth2**.

### 🌐 Dados Externos & Utilitários
- **Clima:** Temperatura atual baseada na geolocalização (Open-Meteo API).
- **Finanças:** Cotação do Dólar (USD/BRL) e Criptomoedas (Bitcoin, Ethereum, Solana, etc.) via CoinGecko.
- **Bloco de Notas:** Sistema rápido para adicionar e remover lembretes.

---

## 🛠️ Tecnologias Utilizadas

- **Backend:** Python, Django
- **Frontend:** HTML5, CSS3, Bootstrap 5 (Layout Responsivo)
- **APIs & Bibliotecas:**
  - `psutil` (Hardware Stats)
  - `pynvml` & `nvidia-smi` (NVIDIA GPU Stats)
  - `spotipy` (Spotify API)
  - `requests` (APIs REST externas)
  - `pyautogui` (Controle de Volume do Sistema)

---

Desenvolvido por Pedro Fugita