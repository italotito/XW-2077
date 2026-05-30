"""
╔══════════════════════════════════════════════╗
║     XW-2077 • Constantes & ASCII Art        ║
╚══════════════════════════════════════════════╝

Constantes adicionais, arte ASCII para o console,
e valores compartilhados entre módulos.
"""

from config import Config

# ── Arte ASCII do banner de boot ─────────────────────
BOOT_BANNER = r"""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   ██╗  ██╗██╗    ██╗     ██████╗  ██████╗ ███████╗███████╗   ║
║   ╚██╗██╔╝██║    ██║     ╚════██╗██╔═████╗╚════██║╚════██║   ║
║    ╚███╔╝ ██║ █╗ ██║█████╗█████╔╝██║██╔██║    ██╔╝    ██╔╝   ║
║    ██╔██╗ ██║███╗██║╚════╝██╔══╝ ████╔╝██║   ██╔╝    ██╔╝    ║
║   ██╔╝ ██╗╚███╔███╔╝      ██████╗╚██████╔╝   ██║     ██║     ║
║   ╚═╝  ╚═╝ ╚══╝╚══╝      ╚═════╝ ╚═════╝    ╚═╝     ╚═╝     ║
║                                                              ║
║           C Y B E R P U N K   D I S C O R D   B O T         ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""

BOOT_INFO_TEMPLATE = """
┌──────────────────────────────────────────────────┐
│  🤖  Bot:        {bot_name:<30s}     │
│  🏷️   Versão:     {version:<30s}     │
│  📡  Servidores: {guilds:<30s}     │
│  👥  Usuários:   {users:<30s}     │
│  📌  Prefixo:    {prefix:<30s}     │
│  🔗  Lavalink:   {lavalink:<30s}     │
│  💾  Database:   {db_path:<30s}     │
└──────────────────────────────────────────────────┘
"""

# ── Mensagens do sistema ─────────────────────────────
LOADING_COG = "  ⚡ Carregando cog: {cog_name}"
COG_LOADED = "  ✅ Cog carregada: {cog_name}"
COG_FAILED = "  ❌ Falha ao carregar cog {cog_name}: {error}"
DB_CONNECTED = "  💾 Banco de dados conectado: {db_path}"
LAVALINK_CONNECTED = "  🎵 Lavalink conectado: {uri}"
LAVALINK_FAILED = "  ❌ Falha ao conectar Lavalink: {error}"
BOT_READY = "  🟢 Bot pronto e online!"

# ── Limites ──────────────────────────────────────────
MAX_QUEUE_SIZE: int = 100
MAX_VOLUME: int = 100
MIN_VOLUME: int = 0
MAX_WARNINGS: int = 10
LEADERBOARD_PAGE_SIZE: int = 10

# ── Fórmula de nível ────────────────────────────────
# XP necessário para o próximo nível: 5 * (level ^ 2) + 50 * level + 100
def xp_for_level(level: int) -> int:
    """Calcula o XP necessário para atingir o próximo nível."""
    return 5 * (level ** 2) + 50 * level + 100


# ── Status do bot (rotação) ─────────────────────────
BOT_ACTIVITIES: list[str] = [
    "Use /help | XW-2077",
    "🎵 Tocando neon beats",
    "⚡ Cyberpunk vibes",
    f"v{Config.BOT_VERSION} | Night City",
]

# ── Categorias de tickets ───────────────────────────
TICKET_CATEGORIES: list[str] = [
    "geral",
    "suporte",
    "denúncia",
    "sugestão",
    "parceria",
]

# ── Tempo de timeout padrão (segundos) ──────────────
VIEW_TIMEOUT: int = 180  # 3 minutos para Views interativas
MUSIC_PLAYER_TIMEOUT: int = 300  # 5 minutos para o player de música
