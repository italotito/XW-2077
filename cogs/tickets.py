"""
╔══════════════════════════════════════════════════════════╗
║  XW-2077 • Ticket System 🎫                             ║
║  Sistema de tickets com interface interativa cyberpunk   ║
╚══════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import asyncio
import io
import logging
from datetime import datetime, timezone
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from config import Config
from utils.embeds import create_embed, success_embed, error_embed, info_embed

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════
#  Persistent Views & Components
# ══════════════════════════════════════════════

class TicketCategorySelect(discord.ui.Select):
    """Menu de seleção de categoria ao abrir um ticket."""

    def __init__(self) -> None:
        options = [
            discord.SelectOption(
                label="Suporte Geral",
                value="suporte",
                emoji="🛠️",
                description="Dúvidas gerais ou problemas",
            ),
            discord.SelectOption(
                label="Bug / Erro",
                value="bug",
                emoji="🐛",
                description="Reportar um bug ou erro",
            ),
            discord.SelectOption(
                label="Sugestão",
                value="sugestao",
                emoji="💡",
                description="Enviar uma sugestão",
            ),
            discord.SelectOption(
                label="Outro",
                value="outro",
                emoji="📝",
                description="Outros assuntos",
            ),
        ]
        super().__init__(
            placeholder="Selecione a categoria do ticket...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="xw2077:ticket_category_select",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        category_value = self.values[0]
        category_labels = {
            "suporte": "Suporte Geral",
            "bug": "Bug / Erro",
            "sugestao": "Sugestão",
            "outro": "Outro",
        }
        category_label = category_labels.get(category_value, category_value)

        guild = interaction.guild
        user = interaction.user
        bot: commands.Bot = interaction.client  # type: ignore[assignment]

        # Verifica config
        try:
            config = await bot.db.get_ticket_config(guild.id)
        except Exception as e:
            logger.error("Erro ao buscar ticket config: %s", e)
            embed = error_embed("❌ Erro", "Não foi possível acessar as configurações de ticket.")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        if not config or not config.get("enabled", False):
            embed = error_embed("❌ Sistema Desativado", "O sistema de tickets não está ativo neste servidor.")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # Verifica tickets abertos do usuário
        try:
            open_tickets = await bot.db.get_open_tickets(guild.id, user_id=user.id)
            if open_tickets and len(open_tickets) >= 3:
                embed = error_embed(
                    "❌ Limite Atingido",
                    "Você já tem **3 tickets** abertos.\nFeche um antes de abrir outro.",
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
        except Exception:
            pass  # Continua mesmo se a checagem falhar

        # Cria o canal do ticket
        category_channel = guild.get_channel(config.get("category_id", 0))
        if not category_channel or not isinstance(category_channel, discord.CategoryChannel):
            embed = error_embed(
                "❌ Categoria Inválida",
                "A categoria de tickets não foi encontrada. Peça a um admin para reconfigurar.",
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # Permissões do canal
        support_role_id = config.get("support_role_id")
        support_role = guild.get_role(support_role_id) if support_role_id else None

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                attach_files=True,
                embed_links=True,
            ),
            guild.me: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                manage_channels=True,
                manage_messages=True,
            ),
        }

        if support_role:
            overwrites[support_role] = discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                attach_files=True,
                embed_links=True,
            )

        # Nome do canal
        ticket_count = len(open_tickets) + 1 if open_tickets else 1
        safe_name = user.name.lower().replace(" ", "-")[:20]
        channel_name = f"ticket-{safe_name}-{ticket_count}"

        try:
            ticket_channel = await guild.create_text_channel(
                name=channel_name,
                category=category_channel,
                overwrites=overwrites,
                topic=f"Ticket de {user.display_name} | Categoria: {category_label}",
                reason=f"XW-2077 Ticket System — aberto por {user}",
            )
        except discord.Forbidden:
            embed = error_embed(
                "❌ Sem Permissão",
                "Não tenho permissão para criar canais nesta categoria.",
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        except Exception as e:
            logger.error("Erro ao criar canal de ticket: %s", e)
            embed = error_embed("❌ Erro", f"Falha ao criar o canal.\n```{e}```")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # Registra no banco
        try:
            ticket_data = await bot.db.create_ticket(
                guild.id, user.id, ticket_channel.id, category=category_value
            )
        except Exception as e:
            logger.error("Erro ao registrar ticket no banco: %s", e)
            ticket_data = {"id": "???"}

        # Embed de abertura dentro do ticket
        embed = create_embed(
            title="🎫 Ticket Aberto",
            description=(
                f"Olá {user.mention}! Bem-vindo(a) ao seu ticket.\n\n"
                f"**Categoria:** {category_label}\n"
                f"**ID:** `{ticket_data.get('id', '???')}`\n\n"
                "Descreva seu problema ou solicitação abaixo.\n"
                "Um membro da equipe irá atendê-lo em breve. ⚡"
            ),
            color=Config.Colors.PRIMARY,
        )
        if support_role:
            embed.add_field(
                name="👥 Equipe de Suporte",
                value=support_role.mention,
                inline=True,
            )
        embed.add_field(
            name="📅 Aberto em",
            value=discord.utils.format_dt(datetime.now(timezone.utc), style="F"),
            inline=True,
        )

        control_view = TicketControlView()
        await ticket_channel.send(embed=embed, view=control_view)
        # Menciona o usuário e cargo de suporte para notificação
        mention_text = user.mention
        if support_role:
            mention_text += f" {support_role.mention}"
        await ticket_channel.send(mention_text, delete_after=3)

        # Confirmação para o usuário
        embed = success_embed(
            "✅ Ticket Criado",
            f"Seu ticket foi aberto em {ticket_channel.mention}!",
        )
        await interaction.followup.send(embed=embed, ephemeral=True)


class TicketCategoryView(discord.ui.View):
    """View com o select de categoria (ephemeral, não-persistente)."""

    def __init__(self) -> None:
        super().__init__(timeout=60)
        self.add_item(TicketCategorySelect())


class TicketPanelView(discord.ui.View):
    """Painel permanente com botão para abrir tickets.

    Persistente: timeout=None, custom_id em todos os componentes.
    """

    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🎫 Abrir Ticket",
        style=discord.ButtonStyle.success,
        custom_id="xw2077:ticket_open_button",
    )
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        """Abre o menu de seleção de categoria."""
        view = TicketCategoryView()
        embed = info_embed(
            "🎫 Novo Ticket",
            "Selecione a categoria que melhor descreve sua solicitação:",
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class AddMemberModal(discord.ui.Modal, title="👤 Adicionar Membro"):
    """Modal para adicionar um membro ao ticket via ID ou menção."""

    user_input = discord.ui.TextInput(
        label="ID ou nome do membro",
        placeholder="Ex: 123456789 ou @usuario",
        style=discord.TextStyle.short,
        required=True,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)

        raw = self.user_input.value.strip()
        # Tenta extrair ID de menção <@123> ou <@!123>
        user_id = None
        if raw.startswith("<@") and raw.endswith(">"):
            cleaned = raw.replace("<@!", "").replace("<@", "").replace(">", "")
            if cleaned.isdigit():
                user_id = int(cleaned)
        elif raw.isdigit():
            user_id = int(raw)

        if user_id is None:
            # Tenta buscar por nome
            member = discord.utils.find(
                lambda m: m.name.lower() == raw.lower() or m.display_name.lower() == raw.lower(),
                interaction.guild.members,
            )
        else:
            member = interaction.guild.get_member(user_id)

        if not member:
            embed = error_embed("❌ Membro não encontrado", f"Não encontrei `{raw}` neste servidor.")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # Adiciona permissões
        try:
            await interaction.channel.set_permissions(
                member,
                read_messages=True,
                send_messages=True,
                attach_files=True,
                embed_links=True,
            )
            embed = success_embed(
                "👤 Membro Adicionado",
                f"{member.mention} foi adicionado ao ticket.",
            )
            await interaction.followup.send(embed=embed)
        except discord.Forbidden:
            embed = error_embed("❌ Sem Permissão", "Não tenho permissão para alterar este canal.")
            await interaction.followup.send(embed=embed, ephemeral=True)


class CloseConfirmView(discord.ui.View):
    """Confirmação para fechar o ticket."""

    def __init__(self) -> None:
        super().__init__(timeout=30)
        self.confirmed: bool = False

    @discord.ui.button(label="✅ Confirmar", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.confirmed = True
        for child in self.children:
            child.disabled = True  # type: ignore[union-attr]
        await interaction.response.edit_message(view=self)
        self.stop()

    @discord.ui.button(label="❌ Cancelar", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.confirmed = False
        for child in self.children:
            child.disabled = True  # type: ignore[union-attr]
        embed = info_embed("❌ Cancelado", "O ticket não será fechado.")
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()


class TicketControlView(discord.ui.View):
    """Painel de controle dentro do canal de ticket.

    Persistente: timeout=None, custom_id em todos os componentes.
    """

    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🔒 Fechar Ticket",
        style=discord.ButtonStyle.danger,
        custom_id="xw2077:ticket_close_button",
    )
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        """Inicia o processo de fechar o ticket."""
        embed = info_embed(
            "🔒 Fechar Ticket",
            "Tem certeza que deseja fechar este ticket?\nEsta ação não pode ser desfeita.",
        )
        view = CloseConfirmView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        timed_out = await view.wait()
        if timed_out or not view.confirmed:
            return

        await _close_ticket_channel(interaction)

    @discord.ui.button(
        label="👤 Adicionar Membro",
        style=discord.ButtonStyle.secondary,
        custom_id="xw2077:ticket_add_member_button",
    )
    async def add_member(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        """Abre o modal para adicionar um membro."""
        await interaction.response.send_modal(AddMemberModal())

    @discord.ui.button(
        label="📋 Transcript",
        style=discord.ButtonStyle.primary,
        custom_id="xw2077:ticket_transcript_button",
    )
    async def transcript(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        """Gera um transcript do ticket como arquivo de texto."""
        await interaction.response.defer(ephemeral=True)

        try:
            transcript_text = await _generate_transcript(interaction.channel)
            file = discord.File(
                io.BytesIO(transcript_text.encode("utf-8")),
                filename=f"transcript-{interaction.channel.name}.txt",
            )
            embed = success_embed(
                "📋 Transcript Gerado",
                f"Transcript de `{interaction.channel.name}` pronto!",
            )
            await interaction.followup.send(embed=embed, file=file, ephemeral=True)
        except Exception as e:
            logger.error("Erro ao gerar transcript: %s", e)
            embed = error_embed("❌ Erro", f"Falha ao gerar transcript.\n```{e}```")
            await interaction.followup.send(embed=embed, ephemeral=True)


# ══════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════

async def _generate_transcript(channel: discord.TextChannel) -> str:
    """Gera um transcript em texto das mensagens do canal."""
    lines: list[str] = [
        f"═══ TRANSCRIPT: #{channel.name} ═══",
        f"Gerado em: {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')}",
        f"Servidor: {channel.guild.name}",
        "═" * 50,
        "",
    ]

    messages: list[discord.Message] = []
    async for msg in channel.history(limit=500, oldest_first=True):
        messages.append(msg)

    for msg in messages:
        timestamp = msg.created_at.strftime("%d/%m/%Y %H:%M")
        author = f"{msg.author.display_name} ({msg.author})"
        content = msg.content or ""

        # Inclui embeds
        if msg.embeds:
            for emb in msg.embeds:
                if emb.title:
                    content += f"\n[Embed: {emb.title}]"
                if emb.description:
                    content += f"\n{emb.description}"

        # Inclui anexos
        if msg.attachments:
            for att in msg.attachments:
                content += f"\n[Anexo: {att.filename} — {att.url}]"

        lines.append(f"[{timestamp}] {author}: {content}")

    lines.append("")
    lines.append("═" * 50)
    lines.append("Fim do transcript.")
    return "\n".join(lines)


async def _close_ticket_channel(interaction: discord.Interaction) -> None:
    """Fecha o ticket: envia transcript pro log, apaga canal."""
    channel = interaction.channel
    guild = interaction.guild
    bot: commands.Bot = interaction.client  # type: ignore[assignment]

    # Gera transcript
    try:
        transcript_text = await _generate_transcript(channel)
    except Exception as e:
        logger.error("Erro ao gerar transcript no fechamento: %s", e)
        transcript_text = f"Erro ao gerar transcript: {e}"

    # Busca config para log channel
    try:
        config = await bot.db.get_ticket_config(guild.id)
        log_channel_id = config.get("log_channel_id") if config else None
    except Exception:
        log_channel_id = None

    # Envia transcript pro log channel
    if log_channel_id:
        log_channel = guild.get_channel(log_channel_id)
        if log_channel:
            file = discord.File(
                io.BytesIO(transcript_text.encode("utf-8")),
                filename=f"transcript-{channel.name}.txt",
            )
            embed = create_embed(
                title="🔒 Ticket Fechado",
                description=(
                    f"**Canal:** #{channel.name}\n"
                    f"**Fechado por:** {interaction.user.mention}\n"
                    f"**Data:** {discord.utils.format_dt(datetime.now(timezone.utc), style='F')}"
                ),
                color=Config.Colors.WARNING,
            )
            try:
                await log_channel.send(embed=embed, file=file)
            except discord.Forbidden:
                logger.warning("Sem permissão para enviar log no canal %s", log_channel_id)

    # Marca ticket como fechado no banco
    try:
        open_tickets = await bot.db.get_open_tickets(guild.id)
        for ticket in open_tickets:
            if ticket.get("channel_id") == channel.id:
                await bot.db.close_ticket(ticket["id"])
                break
    except Exception as e:
        logger.error("Erro ao fechar ticket no banco: %s", e)

    # Notifica e deleta canal
    embed = create_embed(
        title="🔒 Ticket Encerrado",
        description="Este ticket será deletado em **5 segundos**...",
        color=Config.Colors.ERROR,
    )
    try:
        await channel.send(embed=embed)
    except discord.Forbidden:
        pass

    await asyncio.sleep(5)

    try:
        await channel.delete(reason="XW-2077 Ticket System — ticket fechado")
    except discord.Forbidden:
        logger.warning("Sem permissão para deletar canal %s", channel.name)
    except discord.NotFound:
        pass  # Já foi deletado


# ══════════════════════════════════════════════
#  Cog
# ══════════════════════════════════════════════

class Tickets(commands.Cog):
    """Sistema de tickets interativo com temática cyberpunk."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        """Registra views persistentes ao carregar o cog."""
        self.bot.add_view(TicketPanelView())
        self.bot.add_view(TicketControlView())

    # ──────────────────────────────────────────────
    #  Slash Command Group: /ticket
    # ──────────────────────────────────────────────

    ticket_group = app_commands.Group(
        name="ticket",
        description="🎫 Sistema de tickets de suporte",
    )

    @ticket_group.command(name="setup", description="⚙️ Configura o sistema de tickets")
    @app_commands.describe(
        categoria="Categoria onde os tickets serão criados",
        log_channel="Canal para logs de tickets (opcional)",
        support_role="Cargo da equipe de suporte (opcional)",
    )
    @app_commands.default_permissions(manage_guild=True)
    async def ticket_setup(
        self,
        interaction: discord.Interaction,
        categoria: discord.CategoryChannel,
        log_channel: Optional[discord.TextChannel] = None,
        support_role: Optional[discord.Role] = None,
    ) -> None:
        """Configura o sistema de tickets e envia o painel."""
        await interaction.response.defer(ephemeral=True)

        try:
            kwargs = {
                "category_id": categoria.id,
                "enabled": True,
            }
            if log_channel:
                kwargs["log_channel_id"] = log_channel.id
            if support_role:
                kwargs["support_role_id"] = support_role.id

            await self.bot.db.set_ticket_config(interaction.guild_id, **kwargs)

        except Exception as e:
            logger.error("Erro ao salvar ticket config: %s", e)
            embed = error_embed("❌ Erro", f"Falha ao salvar configurações.\n```{e}```")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # Envia o painel de tickets no canal atual
        panel_embed = create_embed(
            title="🎫 Central de Suporte — XW-2077",
            description=(
                "Precisa de ajuda, runner? 🌃\n\n"
                "Clique no botão abaixo para abrir um ticket.\n"
                "Nossa equipe de suporte irá atendê-lo o mais rápido possível.\n\n"
                "**📌 Regras:**\n"
                "• Descreva seu problema com detalhes\n"
                "• Não abra tickets desnecessários\n"
                "• Seja respeitoso com a equipe\n"
                "• Máximo de **3 tickets** abertos por vez"
            ),
            color=Config.Colors.PRIMARY,
        )
        panel_embed.set_footer(text=Config.EMBED_FOOTER)

        panel_view = TicketPanelView()

        try:
            await interaction.channel.send(embed=panel_embed, view=panel_view)
        except discord.Forbidden:
            embed = error_embed("❌ Sem Permissão", "Não tenho permissão para enviar mensagens neste canal.")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # Confirmação para o admin
        lines = [
            f"**Categoria:** {categoria.mention}",
        ]
        if log_channel:
            lines.append(f"**Log Channel:** {log_channel.mention}")
        if support_role:
            lines.append(f"**Cargo de Suporte:** {support_role.mention}")
        lines.append("\n✅ Painel enviado com sucesso!")

        embed = success_embed("⚡ Ticket System Configurado", "\n".join(lines))
        await interaction.followup.send(embed=embed, ephemeral=True)

    @ticket_group.command(name="close", description="🔒 Fecha o ticket atual")
    @app_commands.describe(motivo="Motivo para fechar o ticket (opcional)")
    async def ticket_close(
        self,
        interaction: discord.Interaction,
        motivo: Optional[str] = None,
    ) -> None:
        """Fecha o ticket no canal atual com confirmação."""
        # Verifica se estamos em um canal de ticket
        if not interaction.channel.name.startswith("ticket-"):
            embed = error_embed(
                "❌ Canal Inválido",
                "Este comando só pode ser usado dentro de um canal de ticket.",
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        reason_text = f"\n**Motivo:** {motivo}" if motivo else ""
        embed = info_embed(
            "🔒 Fechar Ticket",
            f"Tem certeza que deseja fechar este ticket?{reason_text}\n"
            "Esta ação não pode ser desfeita.",
        )
        view = CloseConfirmView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        timed_out = await view.wait()
        if timed_out or not view.confirmed:
            return

        await _close_ticket_channel(interaction)

    @ticket_group.command(name="add", description="👤 Adiciona um membro ao ticket")
    @app_commands.describe(user="Membro para adicionar ao ticket")
    async def ticket_add(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
    ) -> None:
        """Adiciona um membro ao canal de ticket atual."""
        if not interaction.channel.name.startswith("ticket-"):
            embed = error_embed(
                "❌ Canal Inválido",
                "Este comando só pode ser usado dentro de um canal de ticket.",
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        try:
            await interaction.channel.set_permissions(
                user,
                read_messages=True,
                send_messages=True,
                attach_files=True,
                embed_links=True,
            )
            embed = success_embed(
                "👤 Membro Adicionado",
                f"{user.mention} foi adicionado ao ticket.",
            )
            await interaction.response.send_message(embed=embed)
        except discord.Forbidden:
            embed = error_embed("❌ Sem Permissão", "Não tenho permissão para alterar este canal.")
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @ticket_group.command(name="remove", description="👤 Remove um membro do ticket")
    @app_commands.describe(user="Membro para remover do ticket")
    async def ticket_remove(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
    ) -> None:
        """Remove um membro do canal de ticket atual."""
        if not interaction.channel.name.startswith("ticket-"):
            embed = error_embed(
                "❌ Canal Inválido",
                "Este comando só pode ser usado dentro de um canal de ticket.",
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        try:
            await interaction.channel.set_permissions(user, overwrite=None)
            embed = success_embed(
                "👤 Membro Removido",
                f"{user.mention} foi removido do ticket.",
            )
            await interaction.response.send_message(embed=embed)
        except discord.Forbidden:
            embed = error_embed("❌ Sem Permissão", "Não tenho permissão para alterar este canal.")
            await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    """Carrega o cog Tickets no bot."""
    await bot.add_cog(Tickets(bot))
