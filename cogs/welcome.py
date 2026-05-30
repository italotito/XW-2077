"""
╔══════════════════════════════════════════════════════════╗
║  XW-2077 • Welcome System 👋                            ║
║  Sistema de boas-vindas e despedida cyberpunk            ║
╚══════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from config import Config
from utils.embeds import create_embed, success_embed, error_embed, info_embed

logger = logging.getLogger(__name__)


class Welcome(commands.Cog):
    """Sistema de boas-vindas e despedida com temática cyberpunk."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # ──────────────────────────────────────────────
    #  Helpers
    # ──────────────────────────────────────────────

    def _format_message(
        self,
        template: str,
        member: discord.Member,
    ) -> str:
        """Substitui variáveis de template na mensagem customizada."""
        return template.format(
            user=member.mention,
            server=member.guild.name,
            count=member.guild.member_count,
        )

    def _build_welcome_embed(self, member: discord.Member, custom_msg: Optional[str] = None) -> discord.Embed:
        """Cria o embed de boas-vindas com estética cyberpunk."""
        default_msg = (
            f"Bem-vindo(a) à megacidade, {member.mention}! 🌃\n"
            "Conecte-se à rede e explore os canais.\n"
            "Sua jornada no submundo digital começa agora."
        )
        description = self._format_message(custom_msg, member) if custom_msg else default_msg

        embed = create_embed(
            title=f"👋 Bem-vindo(a) ao {member.guild.name}!",
            description=description,
            color=Config.Colors.SUCCESS,
        )
        embed.set_thumbnail(url=member.display_avatar.url)

        # Membro # (contagem)
        embed.add_field(
            name="🔢 Membro",
            value=f"#{member.guild.member_count}",
            inline=True,
        )

        # Data de criação da conta
        account_age = discord.utils.format_dt(member.created_at, style="R")
        embed.add_field(
            name="📅 Conta criada",
            value=account_age,
            inline=True,
        )

        return embed

    def _build_goodbye_embed(self, member: discord.Member, custom_msg: Optional[str] = None) -> discord.Embed:
        """Cria o embed de despedida."""
        default_msg = (
            f"**{member.display_name}** se desconectou da rede. 📡\n"
            f"Agora somos **{member.guild.member_count}** na megacidade."
        )
        description = self._format_message(custom_msg, member) if custom_msg else default_msg

        embed = create_embed(
            title="👋 Até logo, runner...",
            description=description,
            color=Config.Colors.ERROR,
        )
        embed.set_thumbnail(url=member.display_avatar.url)

        embed.add_field(
            name="👥 Membros restantes",
            value=str(member.guild.member_count),
            inline=True,
        )

        return embed

    # ──────────────────────────────────────────────
    #  Events
    # ──────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        """Envia mensagem de boas-vindas e aplica auto-role."""
        if member.bot:
            return

        try:
            config = await self.bot.db.get_welcome_config(member.guild.id)
        except Exception as e:
            logger.error("Erro ao buscar welcome config para guild %s: %s", member.guild.id, e)
            return

        if not config or not config.get("enabled", False):
            return

        # ── Welcome message ──
        welcome_channel_id = config.get("welcome_channel_id")
        if welcome_channel_id:
            channel = member.guild.get_channel(welcome_channel_id)
            if channel:
                custom_msg = config.get("welcome_message")
                embed = self._build_welcome_embed(member, custom_msg)
                try:
                    await channel.send(embed=embed)
                except discord.Forbidden:
                    logger.warning(
                        "Sem permissão para enviar welcome em #%s (guild %s)",
                        channel.name,
                        member.guild.id,
                    )

        # ── Auto-role ──
        auto_role_id = config.get("auto_role_id")
        if auto_role_id:
            role = member.guild.get_role(auto_role_id)
            if role:
                try:
                    await member.add_roles(role, reason="XW-2077 Auto-role")
                except discord.Forbidden:
                    logger.warning(
                        "Sem permissão para atribuir cargo '%s' (guild %s)",
                        role.name,
                        member.guild.id,
                    )

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        """Envia mensagem de despedida."""
        if member.bot:
            return

        try:
            config = await self.bot.db.get_welcome_config(member.guild.id)
        except Exception as e:
            logger.error("Erro ao buscar welcome config para guild %s: %s", member.guild.id, e)
            return

        if not config or not config.get("enabled", False):
            return

        goodbye_channel_id = config.get("goodbye_channel_id") or config.get("welcome_channel_id")
        if not goodbye_channel_id:
            return

        channel = member.guild.get_channel(goodbye_channel_id)
        if not channel:
            return

        custom_msg = config.get("goodbye_message")
        embed = self._build_goodbye_embed(member, custom_msg)
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            logger.warning(
                "Sem permissão para enviar goodbye em #%s (guild %s)",
                channel.name,
                member.guild.id,
            )

    # ──────────────────────────────────────────────
    #  Slash Command Group: /welcome
    # ──────────────────────────────────────────────

    welcome_group = app_commands.Group(
        name="welcome",
        description="⚙️ Configurações do sistema de boas-vindas",
        default_permissions=discord.Permissions(manage_guild=True),
    )

    @welcome_group.command(name="setup", description="📡 Configura o sistema de boas-vindas")
    @app_commands.describe(
        canal="Canal para mensagens de boas-vindas",
        canal_saida="Canal para mensagens de despedida (opcional, usa o mesmo se omitido)",
        cargo_auto="Cargo atribuído automaticamente a novos membros",
    )
    async def welcome_setup(
        self,
        interaction: discord.Interaction,
        canal: discord.TextChannel,
        canal_saida: Optional[discord.TextChannel] = None,
        cargo_auto: Optional[discord.Role] = None,
    ) -> None:
        """Configura canais e auto-role do sistema de welcome."""
        await interaction.response.defer(ephemeral=True)

        try:
            kwargs: dict = {
                "welcome_channel_id": canal.id,
                "goodbye_channel_id": canal_saida.id if canal_saida else canal.id,
                "enabled": True,
            }
            if cargo_auto:
                kwargs["auto_role_id"] = cargo_auto.id

            await self.bot.db.set_welcome_config(interaction.guild_id, **kwargs)

            lines = [
                f"**Canal de entrada:** {canal.mention}",
                f"**Canal de saída:** {(canal_saida or canal).mention}",
            ]
            if cargo_auto:
                lines.append(f"**Auto-role:** {cargo_auto.mention}")
            lines.append("\n✅ Sistema **ativado** com sucesso!")

            embed = success_embed(
                "⚡ Welcome System Configurado",
                "\n".join(lines),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error("Erro ao configurar welcome: %s", e)
            embed = error_embed(
                "❌ Erro na Configuração",
                f"Não foi possível salvar as configurações.\n```{e}```",
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @welcome_group.command(name="toggle", description="🔌 Liga ou desliga o sistema de boas-vindas")
    async def welcome_toggle(self, interaction: discord.Interaction) -> None:
        """Alterna o estado do sistema de welcome."""
        await interaction.response.defer(ephemeral=True)

        try:
            config = await self.bot.db.get_welcome_config(interaction.guild_id)
            if not config:
                embed = error_embed(
                    "❌ Não Configurado",
                    "Use `/welcome setup` primeiro para configurar o sistema.",
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            new_state = not config.get("enabled", False)
            await self.bot.db.set_welcome_config(interaction.guild_id, enabled=new_state)

            status_text = "**ONLINE** 🟢" if new_state else "**OFFLINE** 🔴"
            emoji = "⚡" if new_state else "💤"
            embed = success_embed(
                f"{emoji} Sistema de Welcome",
                f"Status alterado para: {status_text}",
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error("Erro ao alternar welcome: %s", e)
            embed = error_embed("❌ Erro", f"Falha ao alterar estado.\n```{e}```")
            await interaction.followup.send(embed=embed, ephemeral=True)

    @welcome_group.command(name="message", description="✏️ Customiza a mensagem de entrada ou saída")
    @app_commands.describe(
        tipo="Tipo de mensagem para customizar",
        mensagem="Mensagem customizada. Use {user}, {server}, {count}",
    )
    @app_commands.choices(
        tipo=[
            app_commands.Choice(name="Entrada (boas-vindas)", value="entrada"),
            app_commands.Choice(name="Saída (despedida)", value="saida"),
        ]
    )
    async def welcome_message(
        self,
        interaction: discord.Interaction,
        tipo: app_commands.Choice[str],
        mensagem: str,
    ) -> None:
        """Define mensagens customizadas para entrada ou saída."""
        await interaction.response.defer(ephemeral=True)

        try:
            config = await self.bot.db.get_welcome_config(interaction.guild_id)
            if not config:
                embed = error_embed(
                    "❌ Não Configurado",
                    "Use `/welcome setup` primeiro.",
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            if tipo.value == "entrada":
                await self.bot.db.set_welcome_config(
                    interaction.guild_id,
                    welcome_message=mensagem,
                )
                tipo_label = "boas-vindas"
            else:
                await self.bot.db.set_welcome_config(
                    interaction.guild_id,
                    goodbye_message=mensagem,
                )
                tipo_label = "despedida"

            embed = success_embed(
                "✏️ Mensagem Atualizada",
                f"Mensagem de **{tipo_label}** salva com sucesso!\n\n"
                f"**Preview:**\n{mensagem}\n\n"
                f"💡 Variáveis: `{{user}}` `{{server}}` `{{count}}`",
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error("Erro ao definir mensagem: %s", e)
            embed = error_embed("❌ Erro", f"Falha ao salvar mensagem.\n```{e}```")
            await interaction.followup.send(embed=embed, ephemeral=True)

    @welcome_group.command(name="test", description="🧪 Envia uma mensagem de teste no canal configurado")
    async def welcome_test(self, interaction: discord.Interaction) -> None:
        """Envia embeds de teste para verificar a configuração."""
        await interaction.response.defer(ephemeral=True)

        try:
            config = await self.bot.db.get_welcome_config(interaction.guild_id)
            if not config:
                embed = error_embed(
                    "❌ Não Configurado",
                    "Use `/welcome setup` primeiro.",
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Envia welcome de teste
            welcome_channel_id = config.get("welcome_channel_id")
            if welcome_channel_id:
                channel = interaction.guild.get_channel(welcome_channel_id)
                if channel:
                    custom_msg = config.get("welcome_message")
                    embed = self._build_welcome_embed(interaction.user, custom_msg)
                    embed.set_footer(text=f"⚠️ TESTE • {Config.EMBED_FOOTER}")
                    await channel.send(embed=embed)

            # Envia goodbye de teste
            goodbye_channel_id = config.get("goodbye_channel_id")
            if goodbye_channel_id and goodbye_channel_id != welcome_channel_id:
                channel = interaction.guild.get_channel(goodbye_channel_id)
                if channel:
                    custom_msg = config.get("goodbye_message")
                    embed = self._build_goodbye_embed(interaction.user, custom_msg)
                    embed.set_footer(text=f"⚠️ TESTE • {Config.EMBED_FOOTER}")
                    await channel.send(embed=embed)

            embed = success_embed(
                "🧪 Teste Enviado",
                "Mensagens de teste enviadas nos canais configurados.\n"
                "Verifique se tudo está como esperado!",
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error("Erro no teste de welcome: %s", e)
            embed = error_embed("❌ Erro", f"Falha ao enviar teste.\n```{e}```")
            await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    """Carrega o cog Welcome no bot."""
    await bot.add_cog(Welcome(bot))
