"""
╔══════════════════════════════════════════════╗
║       XW-2077 • Configuração Central        ║
║         Cyberpunk Discord Bot               ║
╚══════════════════════════════════════════════╝
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Configurações centrais do bot XW-2077."""

    # ── Bot ───────────────────────────────────────────
    TOKEN: str = os.getenv('DISCORD_BOT_TOKEN', '')
    PREFIX: str = '!'
    BOT_NAME: str = 'XW-2077'
    BOT_VERSION: str = '2.0.0'

    # ── Cores (int hex para discord.Embed) ────────────
    class Colors:
        """Paleta de cores neon cyberpunk para embeds."""
        PRIMARY: int    = 0x00FFFF   # Cyan neon
        SECONDARY: int  = 0xFF00FF   # Magenta
        SUCCESS: int    = 0x39FF14   # Neon Green
        ERROR: int      = 0xFF3333   # Red
        WARNING: int    = 0xFF6B35   # Orange
        INFO: int       = 0x8B5CF6   # Purple
        MUSIC: int      = 0x00FFFF   # Cyan
        MODERATION: int = 0xFF3333   # Red
        FUN: int        = 0xFF00FF   # Magenta
        LEVELING: int   = 0x39FF14   # Neon Green

    # ── Lavalink / Wavelink ───────────────────────────
    LAVALINK_URI: str      = os.getenv('LAVALINK_URI', 'http://localhost:2333')
    LAVALINK_PASSWORD: str = os.getenv('LAVALINK_PASSWORD', 'youshallnotpass')

    # ── Banco de Dados ────────────────────────────────
    DB_PATH: str = 'data/xw2077.db'

    # ── Embed ─────────────────────────────────────────
    EMBED_FOOTER: str = 'XW-2077 • Cyberpunk Bot'

    # ── Sistema de XP / Níveis ────────────────────────
    XP_PER_MESSAGE: int = 15
    XP_COOLDOWN: int    = 60  # segundos

    # ── Atalhos de Emojis ─────────────────────────────
    class Emojis:
        """Emojis padronizados usados em todo o bot."""
        # Música
        PLAY: str      = '▶️'
        PAUSE: str     = '⏸️'
        STOP: str      = '⏹️'
        SKIP: str      = '⏭️'
        PREVIOUS: str  = '⏮️'
        SHUFFLE: str   = '🔀'
        LOOP: str      = '🔁'
        LOOP_ONE: str  = '🔂'
        VOLUME: str    = '🔊'
        VOLUME_MUTE: str = '🔇'
        MUSIC: str     = '🎵'
        QUEUE: str     = '📋'

        # Interface geral
        CHECK: str     = '✅'
        CROSS: str     = '❌'
        WARNING: str   = '⚠️'
        INFO: str      = 'ℹ️'
        STAR: str      = '⭐'
        TROPHY: str    = '🏆'
        TICKET: str    = '🎫'
        WELCOME: str   = '👋'
        LEVEL_UP: str  = '🎉'
