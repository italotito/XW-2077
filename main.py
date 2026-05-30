"""
╔══════════════════════════════════════════════════╗
║       XW-2077 • Cyberpunk Discord Bot v2.0.0     ║
║         O MESTRE SUPREMO DOS BOTS                ║
╚══════════════════════════════════════════════════╝
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import discord
from discord.ext import commands

from config import Config
from utils.constants import (
    BOOT_BANNER,
    BOOT_INFO_TEMPLATE,
    BOT_READY,
    COG_FAILED,
    COG_LOADED,
    LOADING_COG,
)
from utils.database import Database

# ── Logging ──────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("data/xw2077.log", encoding="utf-8"),
    ],
)

# Reduz logs ruidosos de bibliotecas externas
logging.getLogger("discord").setLevel(logging.WARNING)
logging.getLogger("wavelink").setLevel(logging.INFO)

log = logging.getLogger(Config.BOT_NAME)


# ── Bot ──────────────────────────────────────────────
class XW2077Bot(commands.Bot):
    """Classe principal do bot XW-2077."""

    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True

        super().__init__(
            command_prefix=Config.PREFIX,
            intents=intents,
            help_command=None,
            activity=discord.Game(name="Use /help | XW-2077"),
        )

        self.db: Database = Database()
        self.start_time: datetime = datetime.now(timezone.utc)

    async def setup_hook(self) -> None:
        """Configuração executada antes do bot conectar."""
        # Garante o diretório de dados
        os.makedirs("data", exist_ok=True)

        # Inicializa banco de dados
        await self.db.init()
        log.info("💾 Banco de dados inicializado: %s", Config.DB_PATH)

        # Carrega cogs dinamicamente
        await self._load_cogs()

        # Conecta ao Lavalink via Wavelink
        await self._connect_wavelink()

        # Sincroniza slash commands
        try:
            synced = await self.tree.sync()
            log.info("⚡ %d slash commands sincronizados.", len(synced))
        except Exception as e:
            log.error("❌ Falha ao sincronizar commands: %s", e)

    async def _load_cogs(self) -> None:
        """Carrega todas as cogs do diretório cogs/."""
        cogs_dir = Path("cogs")
        if not cogs_dir.exists():
            log.warning("⚠️ Diretório 'cogs/' não encontrado.")
            return

        for filename in sorted(cogs_dir.glob("*.py")):
            if filename.name.startswith("_"):
                continue

            cog_name = f"cogs.{filename.stem}"
            log.info(LOADING_COG.format(cog_name=cog_name))

            try:
                await self.load_extension(cog_name)
                log.info(COG_LOADED.format(cog_name=cog_name))
            except Exception as e:
                log.error(COG_FAILED.format(cog_name=cog_name, error=e))

    async def _connect_wavelink(self) -> None:
        """Conecta ao servidor Lavalink via Wavelink."""
        try:
            import wavelink

            node = wavelink.Node(
                uri=Config.LAVALINK_URI,
                password=Config.LAVALINK_PASSWORD,
            )
            await wavelink.Pool.connect(
                nodes=[node],
                client=self,
                cache_capacity=100,
            )
            log.info("🎵 Wavelink conectado: %s", Config.LAVALINK_URI)
        except ImportError:
            log.warning("⚠️ Wavelink não instalado — música desabilitada.")
        except Exception as e:
            log.warning("⚠️ Lavalink indisponível: %s (música pode não funcionar)", e)

    async def on_ready(self) -> None:
        """Evento disparado quando o bot está online."""
        assert self.user is not None

        print(BOOT_BANNER)
        print(
            BOOT_INFO_TEMPLATE.format(
                bot_name=str(self.user),
                version=Config.BOT_VERSION,
                guilds=str(len(self.guilds)),
                users=str(sum(g.member_count or 0 for g in self.guilds)),
                prefix=Config.PREFIX,
                lavalink=Config.LAVALINK_URI,
                db_path=Config.DB_PATH,
            )
        )
        log.info(BOT_READY)

    async def on_command_error(
        self, ctx: commands.Context, error: commands.CommandError  # type: ignore[override]
    ) -> None:
        """Handler global de erros para comandos de prefixo."""
        from utils.embeds import error_embed

        if isinstance(error, commands.CommandNotFound):
            return  # Ignora comandos inexistentes

        if isinstance(error, commands.MissingPermissions):
            perms = ", ".join(error.missing_permissions)
            embed = error_embed(
                "Permissão Negada",
                f"Você precisa das permissões: `{perms}`",
            )
            await ctx.send(embed=embed)
            return

        if isinstance(error, commands.MissingRequiredArgument):
            embed = error_embed(
                "Argumento Faltando",
                f"Uso incorreto. Parâmetro obrigatório: `{error.param.name}`",
            )
            await ctx.send(embed=embed)
            return

        if isinstance(error, commands.BotMissingPermissions):
            perms = ", ".join(error.missing_permissions)
            embed = error_embed(
                "Sem Permissão",
                f"Eu preciso das permissões: `{perms}`",
            )
            await ctx.send(embed=embed)
            return

        # Erro desconhecido
        log.error("Erro não tratado em '%s': %s", ctx.command, error, exc_info=error)

    async def close(self) -> None:
        """Fecha conexões ao desligar o bot."""
        await self.db.close()
        await super().close()


# ── Tratamento de erros de slash commands (global) ──
bot = XW2077Bot()


@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error: discord.app_commands.AppCommandError,
) -> None:
    """Handler global de erros para slash commands."""
    from utils.embeds import error_embed

    if isinstance(error, discord.app_commands.MissingPermissions):
        perms = ", ".join(error.missing_permissions)
        embed = error_embed(
            "Permissão Negada",
            f"Você precisa das permissões: `{perms}`",
        )
    elif isinstance(error, discord.app_commands.CommandOnCooldown):
        embed = error_embed(
            "Cooldown",
            f"Aguarde **{error.retry_after:.1f}s** antes de usar novamente.",
        )
    else:
        embed = error_embed(
            "Erro",
            "Ocorreu um erro inesperado. Tente novamente mais tarde.",
        )
        log.error("Erro em app command: %s", error, exc_info=error)

    try:
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)
    except discord.HTTPException:
        pass


# ── Execução ─────────────────────────────────────────
def main() -> None:
    """Ponto de entrada principal do bot."""
    if not Config.TOKEN:
        log.critical(
            "❌ DISCORD_BOT_TOKEN não definido!\n"
            "   Crie um arquivo '.env' com: DISCORD_BOT_TOKEN=seu_token_aqui\n"
            "   Ou defina a variável de ambiente."
        )
        sys.exit(1)

    log.info("🚀 Iniciando %s v%s ...", Config.BOT_NAME, Config.BOT_VERSION)
    bot.run(Config.TOKEN, log_handler=None)


if __name__ == "__main__":
    main()
