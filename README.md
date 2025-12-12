# 📊 Dashboard Pessoal: Estudo de Arquitetura Server-Driven

Este repositório documenta o desenvolvimento de um dashboard interativo focado em visualização de dados em tempo real. O projeto serve como um estudo de caso sobre **Arquitetura Server-Driven (UI Guiada pelo Servidor)**, utilizando o ecossistema Python para gerenciar tanto a lógica de negócios quanto a dinamicidade do frontend, eliminando a necessidade de Single Page Applications (SPAs) complexas.

## 🎯 Objetivos do Projeto

1.  **Consumo de APIs Externas:** Integração com serviços públicos (ex: CoinGecko) para obtenção de dados financeiros e climáticos.
2.  **Reatividade sem JavaScript Complexo:** Implementação de atualizações assíncronas usando **HTMX**.
3.  **Design Responsivo Rápido:** Utilização de **Bootstrap 5** para prototipagem ágil de interface.
4.  **Backend Robusto:** Uso do **Django** para orquestração de requisições e segurança.

## 🏗️ Decisões de Arquitetura

### 1. Backend: Django (Python)
Optou-se pelo Django devido à sua arquitetura "Baterias Inclusas".
* **Papel no projeto:** Ele atua como o orquestrador central. Em vez de apenas enviar JSON para o frontend (como faria uma API REST tradicional para React), o Django renderiza **fragmentos de HTML** prontos para serem injetados na página.

### 2. A Camada de "Tempo Real": HTMX vs WebSockets
Para este dashboard, a estratégia de atualização escolhida foi **Polling (Sondagem)** via HTMX, em vez de WebSockets (Django Channels).
* **Por que HTMX?** Permite que elementos HTML façam requisições HTTP diretamente. Isso mantém a lógica de estado no servidor (Python) e reduz drasticamente a quantidade de JavaScript escrito.
* **Por que Polling?** Como as APIs externas gratuitas possuem limites de taxa (rate limits) e não oferecem WebSockets nativos, fazer o navegador perguntar "tem dados novos?" a cada X segundos é a abordagem mais eficiente e resiliente para este cenário.

### 3. Frontend: Bootstrap 5
Foco na estrutura de Grid System para criar um layout de painel (cards, sidebars) sem a necessidade de escrever CSS personalizado extenso.

---

## 🛠️ Stack Tecnológico

| Componente | Tecnologia | Função |
| :--- | :--- | :--- |
| **Linguagem** | Python 3.10+ | Lógica principal |
| **Framework Web** | Django 5.x | Servidor web e roteamento |
| **Requisições HTTP** | Requests | Consumo de APIs externas |
| **Frontend Dinâmico** | HTMX | AJAX e manipulação de DOM |
| **Estilização** | Bootstrap 5 | UI/UX e Responsividade |