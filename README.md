<div align="center">
  <img src="assets/logo.png" alt="XW-2077 Logo" width="200"/>

  # XW-2077 BOT 🤖⚡
  
  **O Bot Cyberpunk Definitivo para o seu Servidor Discord**

  [![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
  [![Discord.py](https://img.shields.io/badge/discord.py-2.5+-blue.svg)](https://github.com/Rapptz/discord.py)
  [![Wavelink](https://img.shields.io/badge/Wavelink-3.x-cyan.svg)](https://wavelink.dev/)
  [![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
</div>

---

<img src="assets/banner.png" alt="XW-2077 Banner" width="100%"/>

## 🌟 Sobre o Projeto (v2.0.0)

O **XW-2077** esta de volta recarregado!!! Agora completamente reestruturado para se tornar um bot de Discord moderno, modular e altamente interativo. Com uma estética **Cyberpunk**, ele traz as melhores tecnologias de 2026 para o seu servidor.

### 🚀 O que há de novo na v2.0.0?
- **Slash Commands (`/`)**: Todos os comandos foram migrados para Slash Commands nativos do Discord.
- **Arquitetura Modular (Cogs)**: Código organizado em 7 módulos independentes e fáceis de manter.
- **Música Premium**: Substituímos o antigo sistema de FFmpeg direto pelo poderoso **Lavalink v4 + Wavelink 3.x**. Qualidade de áudio superior, suporte a múltiplas plataformas (YouTube, Spotify, SoundCloud) e menor consumo de recursos.
- **UI Interativa**: Uso intensivo de Botões, Menus de Seleção (Dropdowns), Modais e Paginação.
- **Persistência de Dados**: Banco de dados **SQLite** integrado (via `aiosqlite`) para salvar níveis, XP, tickets e avisos (warns).
- **Novos Sistemas**: Níveis (Leveling), Tickets de Suporte, Boas-vindas (Welcome), e vários mini-jogos (Jogo da Velha, Trivia, Enquetes).
- **Estética Cyberpunk**: Todos os embeds, ícones e respostas foram estilizados com tema neon (Cyan, Magenta, Verde Neon).

---

## 🛠️ Funcionalidades Principais

O bot é dividido nas seguintes categorias (Cogs):

### 🎵 Música (`/play`, `/queue`, `/nowplaying`...)
- Player interativo com botões (`⏮️ ⏯️ ⏭️ 🔀 🔁 🔉 🔊 ⏹️ 📋`).
- Fila paginada.
- Barras de progresso e volume visuais.
- Suporte a loops (música ou fila) e shuffle.

### 🛡️ Moderação (`/ban`, `/kick`, `/mute`, `/warn`...)
- Banimentos e limpezas com botões de confirmação.
- Sistema de `timeout` nativo do Discord (Mute).
- Avisos (Warnings) salvos no banco de dados com histórico paginado.
- Lock/Unlock de canais e modo lento (`slowmode`).

### 🎮 Diversão (`/tictactoe`, `/trivia`, `/poll`, `/rps`...)
- **Jogo da Velha** com grid de botões 3x3 interativo.
- **Trivia** (Quiz) com timer e botões A/B/C/D.
- **Enquetes (Polls)** com barras de progresso que atualizam em tempo real.
- **Pedra, Papel e Tesoura (RPS)** com interações visuais e trash-talk cyberpunk.
- Bola 8, memes, piadas, rolagens de dados e mais.

### 📊 Níveis e XP (`/rank`, `/leaderboard`...)
- Ganho de XP por mensagens (com cooldown anti-spam).
- Rank card com barra de progresso visual.
- Leaderboard (Top 10) paginado com medalhas.
- Notificações de level-up.

### 🎫 Tickets de Suporte (`/ticket setup`...)
- Painel persistente de criação de tickets com botão.
- Canais privados gerados automaticamente por categoria (Suporte, Bug, Sugestão).
- Botões de controle dentro do ticket (Fechar, Adicionar Membro, Gerar Transcript).

### 👋 Boas-vindas (`/welcome setup`...)
- Embeds cyberpunk personalizados quando membros entram ou saem.
- Atribuição automática de cargo (Auto-role).
- Mensagens customizáveis com variáveis.

### 🔧 Utilitários (`/help`, `/serverinfo`, `/embed`...)
- Menu de Ajuda interativo organizado por categorias (Select Menu).
- Criação de embeds customizados via Modal.
- Informações detalhadas de usuários, avatares e do servidor.
- Ping visual indicando a qualidade da conexão.

---

## ⚙️ Como Instalar e Rodar

Uso o Bot convidando para o seu servidor pelo link do Discord(https://discord.com/oauth2/authorize?client_id=1154902622189400074) 🤖
