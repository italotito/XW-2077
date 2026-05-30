"""
╔══════════════════════════════════════════════════════════╗
║  XW-2077 • Leveling System 📊                           ║
║  Sistema de XP e níveis cyberpunk                       ║
╚══════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import logging
import random
import time
from typing import Dict, Optional, Tuple

import discord
from discord import app_commands
from discord.ext import commands

from config import Config
from utils.embeds import create_embed, success_embed, error_embed, info_embed

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
#  Level formula helpers
# ──────────────────────────────────────────────

def xp_for_level(level: int) -> int:
    """XP total necessário para alcançar um nível.

    Formula: xp_needed = (level * 10) ** 2
    - Level 1  →    100 XP
    - Level 2  →    400 XP
    - Level 5  →  2,500 XP
    - Level 10 → 10,000 XP
    """
    return (level * 10) ** 2


def level_from_xp(xp: int) -> int:
    """Calcula o nível atual a partir do XP total."""
    if xp <= 0:
        return 0
    # level = floor(sqrt(xp) / 10)
    return int(xp ** 0.5 / 10)


def build_progress_bar(current: int, total: int, length: int = 10) -> str:
    """Cria uma barra de progresso visual.

    Exemplo: ████████░░ 80%
    """
    if total <= 0:
        percentage = 100
    else:
        percentage = min(int((current / total) * 100), 100)

    filled = int(length * (percentage / 100))
    empty = length - filled
    bar = "█" * filled + "░" * empty
    return f"{bar} {percentage}%"


# ──────────────────────────────────────────────
#  Leaderboard Paginator View
# ──────────────────────────────────────────────

class LeaderboardView(discord.ui.View):
    """Paginação interativa para o leaderboard."""

    def __init__(
        self,
        pages: list[discord.Embed],
        author_id: int,
        *,
        timeout: float = 120,
    ) -> None:
        super().__init__(timeout=timeout)
        self.pages = pages
        self.author_id = author_id
        self.current_page = 0
        self._update_buttons()

    def _update_buttons(self) -> None:
        self.btn_prev.disabled = self.current_page <= 0
        self.btn_next.disabled = self.current_page >= len(self.pages) - 1

    @discord.ui.button(label="◀ Anterior", style=discord.ButtonStyle.secondary)
    async def btn_prev(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message(
                "❌ Só quem usou o comando pode navegar.", ephemeral=True
            )
        self.current_page = max(0, self.current_page - 1)
        self._update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

    @discord.ui.button(label="Próximo ▶", style=discord.ButtonStyle.secondary)
    async def btn_next(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message(
                "❌ Só quem usou o comando pode navegar.", ephemeral=True
            )
        self.current_page = min(len(self.pages) - 1, self.current_page + 1)
        self._update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True  # type: ignore[union-attr]


# ──────────────────────────────────────────────
#  Cog
# ──────────────────────────────────────────────

class Leveling(commands.Cog):
    """Sistema de XP, níveis e ranking com temática cyberpunk."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        # In-memory cooldown: {(guild_id, user_id): timestamp}
        self._cooldowns: Dict[Tuple[int, int], float] = {}

    # ──────────────────────────────────────────────
    #  XP Event
    # ──────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Concede XP por mensagem (com cooldown)."""
        # Ignora bots, DMs e mensagens de comando (prefixo /)
        if message.author.bot:
            return
        if not message.guild:
            return
        if message.content.startswith("/"):
            return

        guild_id = message.guild.id
        user_id = message.author.id
        key = (guild_id, user_id)
        now = time.time()

        # Verifica cooldown
        last_xp = self._cooldowns.get(key, 0.0)
        if now - last_xp < Config.XP_COOLDOWN:
            return

        # Atualiza cooldown
        self._cooldowns[key] = now

        # Calcula XP com variação aleatória (±5)
        xp_gain = Config.XP_PER_MESSAGE + random.randint(-5, 5)
        xp_gain = max(1, xp_gain)  # Garante pelo menos 1 XP

        try:
            new_xp, new_level, leveled_up = await self.bot.db.add_xp(guild_id, user_id, xp_gain)
        except Exception as e:
            logger.error("Erro ao adicionar XP para %s em %s: %s", user_id, guild_id, e)
            return

        # Level-up notification
        if leveled_up:
            embed = create_embed(
                title="⚡ LEVEL UP!",
                description=(
                    f"Parabéns, {message.author.mention}! 🎉\n\n"
                    f"Você alcançou o **Nível {new_level}**!\n"
                    f"Continue escalando a hierarquia da megacidade. 🏙️"
                ),
                color=Config.Colors.LEVELING,
            )
            embed.set_thumbnail(url=message.author.display_avatar.url)
            next_level_xp = xp_for_level(new_level + 1)
            embed.add_field(
                name="📊 Próximo nível",
                value=f"`{new_xp:,}` / `{next_level_xp:,}` XP",
                inline=True,
            )
            try:
                await message.channel.send(embed=embed)
            except discord.Forbidden:
                pass

    # ──────────────────────────────────────────────
    #  /rank
    # ──────────────────────────────────────────────

    @app_commands.command(name="rank", description="📊 Mostra seu rank card ou de outro membro")
    @app_commands.describe(user="Membro para ver o rank (opcional)")
    async def rank(
        self,
        interaction: discord.Interaction,
        user: Optional[discord.Member] = None,
    ) -> None:
        """Exibe o rank card com nível, XP, progresso e posição."""
        await interaction.response.defer()

        target = user or interaction.user
        guild_id = interaction.guild_id

        try:
            data = await self.bot.db.get_user_level(guild_id, target.id)
        except Exception as e:
            logger.error("Erro ao buscar rank: %s", e)
            embed = error_embed("❌ Erro", "Não foi possível buscar os dados de rank.")
            await interaction.followup.send(embed=embed)
            return

        if not data:
            xp = 0
            level = 0
            total_messages = 0
        else:
            xp = data.get("xp", 0)
            level = data.get("level", 0)
            total_messages = data.get("total_messages", 0)

        # Posição no ranking
        try:
            position = await self.bot.db.get_rank(guild_id, target.id)
        except Exception:
            position = "?"

        # Cálculos de progresso
        current_level_xp = xp_for_level(level)
        next_level_xp = xp_for_level(level + 1)
        xp_in_level = xp - current_level_xp
        xp_needed_in_level = next_level_xp - current_level_xp
        progress_bar = build_progress_bar(xp_in_level, xp_needed_in_level)

        embed = create_embed(
            title=f"📊 Rank Card — {target.display_name}",
            description=f"Posição no submundo digital de **{interaction.guild.name}**",
            color=Config.Colors.LEVELING,
        )
        embed.set_thumbnail(url=target.display_avatar.url)

        embed.add_field(name="🏆 Ranking", value=f"#{position}", inline=True)
        embed.add_field(name="⚡ Nível", value=str(level), inline=True)
        embed.add_field(name="💬 Mensagens", value=f"{total_messages:,}", inline=True)

        embed.add_field(
            name="📈 Progresso",
            value=f"{progress_bar}\n`{xp_in_level:,}` / `{xp_needed_in_level:,}` XP",
            inline=False,
        )

        embed.add_field(
            name="🔮 XP Total",
            value=f"`{xp:,}` XP",
            inline=True,
        )

        await interaction.followup.send(embed=embed)

    # ──────────────────────────────────────────────
    #  /leaderboard
    # ──────────────────────────────────────────────

    @app_commands.command(name="leaderboard", description="🏆 Top membros do servidor por XP")
    async def leaderboard(self, interaction: discord.Interaction) -> None:
        """Mostra o leaderboard com paginação (10 por página)."""
        await interaction.response.defer()

        guild_id = interaction.guild_id
        per_page = 10

        try:
            # Busca um número generoso para paginação
            all_entries = await self.bot.db.get_leaderboard(guild_id, limit=100)
        except Exception as e:
            logger.error("Erro ao buscar leaderboard: %s", e)
            embed = error_embed("❌ Erro", "Não foi possível carregar o leaderboard.")
            await interaction.followup.send(embed=embed)
            return

        if not all_entries:
            embed = info_embed(
                "🏆 Leaderboard",
                "Nenhum dado de XP encontrado ainda.\nConverse para ganhar XP!",
            )
            await interaction.followup.send(embed=embed)
            return

        # Gera páginas
        pages: list[discord.Embed] = []
        total_pages = max(1, (len(all_entries) + per_page - 1) // per_page)

        for page_num in range(total_pages):
            start = page_num * per_page
            end = start + per_page
            entries = all_entries[start:end]

            lines: list[str] = []
            medals = {0: "🥇", 1: "🥈", 2: "🥉"}

            for i, entry in enumerate(entries):
                global_pos = start + i
                medal = medals.get(global_pos, f"**{global_pos + 1}.**")
                uid = entry.get("user_id", 0)
                lvl = entry.get("level", 0)
                xp_val = entry.get("xp", 0)

                # Tenta resolver o nome do membro
                member = interaction.guild.get_member(uid)
                name = member.display_name if member else f"User#{uid}"

                lines.append(
                    f"{medal} **{name}** — Nível `{lvl}` • `{xp_val:,}` XP"
                )

            embed = create_embed(
                title=f"🏆 Leaderboard — {interaction.guild.name}",
                description="\n".join(lines),
                color=Config.Colors.LEVELING,
            )
            embed.set_footer(text=f"Página {page_num + 1}/{total_pages} • {Config.EMBED_FOOTER}")
            pages.append(embed)

        view = LeaderboardView(pages, interaction.user.id) if len(pages) > 1 else None
        await interaction.followup.send(embed=pages[0], view=view)

    # ──────────────────────────────────────────────
    #  Admin commands
    # ──────────────────────────────────────────────

    @app_commands.command(name="setxp", description="⚙️ [Admin] Define o XP de um membro")
    @app_commands.describe(user="Membro alvo", xp="Quantidade de XP para definir")
    @app_commands.default_permissions(manage_guild=True)
    async def setxp(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        xp: int,
    ) -> None:
        """Define o XP de um usuário (admin)."""
        await interaction.response.defer(ephemeral=True)

        if xp < 0:
            embed = error_embed("❌ Valor Inválido", "O XP não pode ser negativo.")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        try:
            await self.bot.db.set_xp(interaction.guild_id, user.id, xp)
            new_level = level_from_xp(xp)
            embed = success_embed(
                "⚙️ XP Definido",
                f"**{user.display_name}** agora tem:\n"
                f"• XP: `{xp:,}`\n"
                f"• Nível: `{new_level}`",
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error("Erro ao definir XP: %s", e)
            embed = error_embed("❌ Erro", f"Falha ao definir XP.\n```{e}```")
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="resetxp", description="⚙️ [Admin] Reseta o XP de um membro")
    @app_commands.describe(user="Membro para resetar o XP")
    @app_commands.default_permissions(manage_guild=True)
    async def resetxp(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
    ) -> None:
        """Reseta o XP de um usuário (admin)."""
        await interaction.response.defer(ephemeral=True)

        try:
            await self.bot.db.reset_xp(interaction.guild_id, user.id)
            embed = success_embed(
                "🔄 XP Resetado",
                f"O XP de **{user.display_name}** foi zerado.\n"
                f"Volta pro nível 0, runner. 💀",
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error("Erro ao resetar XP: %s", e)
            embed = error_embed("❌ Erro", f"Falha ao resetar XP.\n```{e}```")
            await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    """Carrega o cog Leveling no bot."""
    await bot.add_cog(Leveling(bot))
