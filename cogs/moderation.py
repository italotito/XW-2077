"""
╔══════════════════════════════════════════════════════════╗
║  XW-2077 • Módulo de Moderação                          ║
║  Comandos slash para moderação do servidor               ║
╚══════════════════════════════════════════════════════════╝
"""

import discord
from discord import app_commands
from discord.ext import commands
from datetime import timedelta
from typing import Optional

from config import Config
from utils.embeds import create_embed, success_embed, error_embed, warning_embed, moderation_embed


# ════════════════════════════════════════
#  Views (Botões de Confirmação)
# ════════════════════════════════════════

class BanConfirmView(discord.ui.View):
    """View com botões de confirmação para banimento."""

    def __init__(self, moderator: discord.Member, target: discord.Member, reason: str):
        super().__init__(timeout=30)
        self.moderator = moderator
        self.target = target
        self.reason = reason
        self.value: Optional[bool] = None
        self.message: Optional[discord.Message] = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.moderator.id:
            await interaction.response.send_message(
                embed=error_embed(
                    '⛔ Acesso Negado',
                    'Apenas o moderador que executou o comando pode interagir.'
                ),
                ephemeral=True
            )
            return False
        return True

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(
                    embed=warning_embed(
                        '⏰ Tempo Esgotado',
                        f'O banimento de {self.target.mention} foi cancelado por timeout.'
                    ),
                    view=self
                )
            except discord.HTTPException:
                pass

    @discord.ui.button(label='Confirmar', style=discord.ButtonStyle.danger, emoji='✅')
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.value = True
        for item in self.children:
            item.disabled = True

        try:
            # DM antes de banir
            try:
                dm_embed = moderation_embed(
                    '🔨 Banido',
                    f'Você foi banido de **{interaction.guild.name}**.\n'
                    f'**Motivo:** {self.reason}\n'
                    f'**Moderador:** {self.moderator.display_name}'
                )
                await self.target.send(embed=dm_embed)
            except discord.Forbidden:
                pass

            await self.target.ban(reason=f'{self.reason} | Por: {self.moderator}')

            await interaction.response.edit_message(
                embed=success_embed(
                    '🔨 Usuário Banido',
                    f'**Alvo:** {self.target.mention} (`{self.target.id}`)\n'
                    f'**Motivo:** {self.reason}\n'
                    f'**Moderador:** {self.moderator.mention}'
                ),
                view=self
            )
        except discord.Forbidden:
            await interaction.response.edit_message(
                embed=error_embed(
                    '❌ Sem Permissão',
                    'Não tenho permissão para banir este usuário. '
                    'Verifique a hierarquia de cargos.'
                ),
                view=self
            )
        self.stop()

    @discord.ui.button(label='Cancelar', style=discord.ButtonStyle.secondary, emoji='❌')
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.value = False
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(
            embed=warning_embed(
                '❌ Cancelado',
                f'O banimento de {self.target.mention} foi cancelado.'
            ),
            view=self
        )
        self.stop()


class ClearWarnsConfirmView(discord.ui.View):
    """View com botão de confirmação para limpar warnings."""

    def __init__(self, moderator: discord.Member, target: discord.Member):
        super().__init__(timeout=30)
        self.moderator = moderator
        self.target = target
        self.value: Optional[bool] = None
        self.message: Optional[discord.Message] = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.moderator.id:
            await interaction.response.send_message(
                embed=error_embed(
                    '⛔ Acesso Negado',
                    'Apenas o moderador que executou o comando pode interagir.'
                ),
                ephemeral=True
            )
            return False
        return True

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(
                    embed=warning_embed(
                        '⏰ Tempo Esgotado',
                        f'A limpeza de warnings de {self.target.mention} foi cancelada por timeout.'
                    ),
                    view=self
                )
            except discord.HTTPException:
                pass

    @discord.ui.button(label='Confirmar Limpeza', style=discord.ButtonStyle.danger, emoji='🗑️')
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.value = True
        for item in self.children:
            item.disabled = True

        count = await interaction.client.db.clear_warnings(
            interaction.guild.id, self.target.id
        )

        await interaction.response.edit_message(
            embed=success_embed(
                '🗑️ Warnings Limpos',
                f'**{count}** warning(s) de {self.target.mention} foram removidos.\n'
                f'**Moderador:** {self.moderator.mention}'
            ),
            view=self
        )
        self.stop()

    @discord.ui.button(label='Cancelar', style=discord.ButtonStyle.secondary, emoji='❌')
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.value = False
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(
            embed=warning_embed(
                '❌ Cancelado',
                'A limpeza de warnings foi cancelada.'
            ),
            view=self
        )
        self.stop()


class WarningsPaginationView(discord.ui.View):
    """View de paginação para avisos."""

    def __init__(self, pages: list[discord.Embed], author: discord.Member):
        super().__init__(timeout=120)
        self.pages = pages
        self.author = author
        self.current_page = 0
        self.message: Optional[discord.Message] = None
        self._update_buttons()

    def _update_buttons(self) -> None:
        self.prev_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page == len(self.pages) - 1

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author.id:
            await interaction.response.send_message(
                embed=error_embed(
                    '⛔ Acesso Negado',
                    'Apenas quem executou o comando pode paginar.'
                ),
                ephemeral=True
            )
            return False
        return True

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass

    @discord.ui.button(label='◀ Anterior', style=discord.ButtonStyle.secondary)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.current_page = max(0, self.current_page - 1)
        self._update_buttons()
        await interaction.response.edit_message(
            embed=self.pages[self.current_page], view=self
        )

    @discord.ui.button(label='Próximo ▶', style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.current_page = min(len(self.pages) - 1, self.current_page + 1)
        self._update_buttons()
        await interaction.response.edit_message(
            embed=self.pages[self.current_page], view=self
        )


# ════════════════════════════════════════
#  Cog Principal
# ════════════════════════════════════════

class Moderation(commands.Cog):
    """⚖️ Comandos de moderação do servidor."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # ── Helpers ──

    def _hierarchy_check(
        self,
        interaction: discord.Interaction,
        target: discord.Member
    ) -> Optional[str]:
        """Verifica hierarquia de cargos. Retorna mensagem de erro ou None."""
        if target.id == interaction.user.id:
            return 'Você não pode moderar a si mesmo, samurai.'

        if target.id == interaction.guild.owner_id:
            return 'Não posso moderar o dono do servidor, choom.'

        if target.top_role >= interaction.user.top_role:
            return (
                'Você não pode moderar alguém com cargo igual ou superior ao seu.'
            )

        if target.top_role >= interaction.guild.me.top_role:
            return (
                'Meu cargo é inferior ao do alvo. Não consigo executar essa ação.'
            )

        return None

    # ════════════════════════════════════
    #  /kick
    # ════════════════════════════════════

    @app_commands.command(name='kick', description='Expulsa um usuário do servidor')
    @app_commands.describe(user='Usuário a ser expulso', motivo='Motivo da expulsão')
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        motivo: str = 'Motivo não especificado.'
    ) -> None:
        error_msg = self._hierarchy_check(interaction, user)
        if error_msg:
            return await interaction.response.send_message(
                embed=error_embed('❌ Erro de Hierarquia', error_msg),
                ephemeral=True
            )

        # DM ao usuário antes de expulsar
        try:
            dm_embed = moderation_embed(
                '👢 Expulso',
                f'Você foi expulso de **{interaction.guild.name}**.\n'
                f'**Motivo:** {motivo}\n'
                f'**Moderador:** {interaction.user.display_name}'
            )
            await user.send(embed=dm_embed)
        except discord.Forbidden:
            pass

        await user.kick(reason=f'{motivo} | Por: {interaction.user}')

        await interaction.response.send_message(
            embed=success_embed(
                '👢 Usuário Expulso',
                f'**Alvo:** {user.mention} (`{user.id}`)\n'
                f'**Motivo:** {motivo}\n'
                f'**Moderador:** {interaction.user.mention}'
            )
        )

    # ════════════════════════════════════
    #  /ban (com confirmação)
    # ════════════════════════════════════

    @app_commands.command(name='ban', description='Bane um usuário do servidor')
    @app_commands.describe(user='Usuário a ser banido', motivo='Motivo do banimento')
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        motivo: str = 'Motivo não especificado.'
    ) -> None:
        error_msg = self._hierarchy_check(interaction, user)
        if error_msg:
            return await interaction.response.send_message(
                embed=error_embed('❌ Erro de Hierarquia', error_msg),
                ephemeral=True
            )

        view = BanConfirmView(
            moderator=interaction.user,
            target=user,
            reason=motivo
        )

        embed = warning_embed(
            '⚠️ Confirmar Banimento',
            f'Tem certeza que deseja banir {user.mention}?\n\n'
            f'**Alvo:** {user} (`{user.id}`)\n'
            f'**Motivo:** {motivo}\n\n'
            f'*Você tem 30 segundos para confirmar.*'
        )

        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()

    # ════════════════════════════════════
    #  /unban
    # ════════════════════════════════════

    @app_commands.command(name='unban', description='Remove o banimento de um usuário por ID')
    @app_commands.describe(user_id='ID do usuário a ser desbanido')
    @app_commands.checks.has_permissions(ban_members=True)
    async def unban(
        self,
        interaction: discord.Interaction,
        user_id: str
    ) -> None:
        try:
            uid = int(user_id)
        except ValueError:
            return await interaction.response.send_message(
                embed=error_embed('❌ ID Inválido', 'Forneça um ID numérico válido.'),
                ephemeral=True
            )

        try:
            user = await self.bot.fetch_user(uid)
            await interaction.guild.unban(user, reason=f'Desbanido por {interaction.user}')

            await interaction.response.send_message(
                embed=success_embed(
                    '🔓 Usuário Desbanido',
                    f'**Usuário:** {user} (`{user.id}`)\n'
                    f'**Moderador:** {interaction.user.mention}'
                )
            )
        except discord.NotFound:
            await interaction.response.send_message(
                embed=error_embed(
                    '❌ Não Encontrado',
                    'Este usuário não está banido ou o ID é inválido.'
                ),
                ephemeral=True
            )

    # ════════════════════════════════════
    #  /mute (timeout nativo)
    # ════════════════════════════════════

    @app_commands.command(name='mute', description='Silencia um usuário temporariamente')
    @app_commands.describe(
        user='Usuário a ser silenciado',
        duração='Duração em minutos (padrão: 5)',
        motivo='Motivo do silenciamento'
    )
    @app_commands.checks.has_permissions(moderate_members=True)
    async def mute(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        duração: int = 5,
        motivo: str = 'Motivo não especificado.'
    ) -> None:
        error_msg = self._hierarchy_check(interaction, user)
        if error_msg:
            return await interaction.response.send_message(
                embed=error_embed('❌ Erro de Hierarquia', error_msg),
                ephemeral=True
            )

        # Discord limita timeout a 28 dias
        if duração < 1 or duração > 40320:
            return await interaction.response.send_message(
                embed=error_embed(
                    '❌ Duração Inválida',
                    'A duração deve ser entre 1 minuto e 28 dias (40320 minutos).'
                ),
                ephemeral=True
            )

        duration = timedelta(minutes=duração)
        await user.timeout(duration, reason=f'{motivo} | Por: {interaction.user}')

        # DM ao usuário
        try:
            dm_embed = moderation_embed(
                '🔇 Silenciado',
                f'Você foi silenciado em **{interaction.guild.name}**.\n'
                f'**Duração:** {duração} minuto(s)\n'
                f'**Motivo:** {motivo}\n'
                f'**Moderador:** {interaction.user.display_name}'
            )
            await user.send(embed=dm_embed)
        except discord.Forbidden:
            pass

        await interaction.response.send_message(
            embed=success_embed(
                '🔇 Usuário Silenciado',
                f'**Alvo:** {user.mention}\n'
                f'**Duração:** {duração} minuto(s)\n'
                f'**Motivo:** {motivo}\n'
                f'**Moderador:** {interaction.user.mention}'
            )
        )

    # ════════════════════════════════════
    #  /unmute
    # ════════════════════════════════════

    @app_commands.command(name='unmute', description='Remove o silenciamento de um usuário')
    @app_commands.describe(user='Usuário a ser desmutado')
    @app_commands.checks.has_permissions(moderate_members=True)
    async def unmute(
        self,
        interaction: discord.Interaction,
        user: discord.Member
    ) -> None:
        if not user.is_timed_out():
            return await interaction.response.send_message(
                embed=error_embed(
                    '❌ Não Silenciado',
                    f'{user.mention} não está silenciado.'
                ),
                ephemeral=True
            )

        await user.timeout(None, reason=f'Desmutado por {interaction.user}')

        await interaction.response.send_message(
            embed=success_embed(
                '🔊 Silenciamento Removido',
                f'{user.mention} foi desmutado por {interaction.user.mention}.'
            )
        )

    # ════════════════════════════════════
    #  /warn
    # ════════════════════════════════════

    @app_commands.command(name='warn', description='Adiciona um aviso a um usuário')
    @app_commands.describe(user='Usuário a receber o aviso', motivo='Motivo do aviso')
    @app_commands.checks.has_permissions(manage_guild=True)
    async def warn(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        motivo: str
    ) -> None:
        error_msg = self._hierarchy_check(interaction, user)
        if error_msg:
            return await interaction.response.send_message(
                embed=error_embed('❌ Erro de Hierarquia', error_msg),
                ephemeral=True
            )

        warning = await self.bot.db.add_warning(
            interaction.guild.id,
            user.id,
            interaction.user.id,
            motivo
        )

        # DM ao usuário
        try:
            dm_embed = moderation_embed(
                '⚠️ Aviso Recebido',
                f'Você recebeu um aviso em **{interaction.guild.name}**.\n'
                f'**Motivo:** {motivo}\n'
                f'**Moderador:** {interaction.user.display_name}'
            )
            await user.send(embed=dm_embed)
            dm_status = '✅ DM enviada'
        except discord.Forbidden:
            dm_status = '❌ DM bloqueada'

        warnings_list = await self.bot.db.get_warnings(interaction.guild.id, user.id)

        await interaction.response.send_message(
            embed=success_embed(
                '⚠️ Aviso Registrado',
                f'**Alvo:** {user.mention}\n'
                f'**Motivo:** {motivo}\n'
                f'**Total de avisos:** {len(warnings_list)}\n'
                f'**DM:** {dm_status}\n'
                f'**Moderador:** {interaction.user.mention}'
            )
        )

    # ════════════════════════════════════
    #  /warnings (com paginação)
    # ════════════════════════════════════

    @app_commands.command(name='warnings', description='Lista os avisos de um usuário')
    @app_commands.describe(user='Usuário para verificar avisos')
    @app_commands.checks.has_permissions(manage_guild=True)
    async def warnings(
        self,
        interaction: discord.Interaction,
        user: discord.Member
    ) -> None:
        warnings_list = await self.bot.db.get_warnings(interaction.guild.id, user.id)

        if not warnings_list:
            return await interaction.response.send_message(
                embed=success_embed(
                    '📋 Sem Avisos',
                    f'{user.mention} não possui nenhum aviso registrado. Limpo!'
                ),
                ephemeral=True
            )

        # Paginar warnings (5 por página)
        per_page = 5
        pages: list[discord.Embed] = []

        for i in range(0, len(warnings_list), per_page):
            chunk = warnings_list[i:i + per_page]
            page_num = (i // per_page) + 1
            total_pages = -(-len(warnings_list) // per_page)  # ceil division

            embed = create_embed(
                title=f'⚠️ Avisos de {user.display_name}',
                description=f'Total: **{len(warnings_list)}** aviso(s) | Página {page_num}/{total_pages}',
                color=Config.Colors.WARNING
            )
            embed.set_thumbnail(url=user.display_avatar.url)

            for idx, w in enumerate(chunk, start=i + 1):
                moderator = interaction.guild.get_member(w.get('moderator_id', 0))
                mod_name = moderator.display_name if moderator else 'Desconhecido'
                timestamp = w.get('timestamp', 'N/A')

                embed.add_field(
                    name=f'#{idx} — ID: {w.get("id", "N/A")}',
                    value=(
                        f'**Motivo:** {w.get("reason", "Sem motivo")}\n'
                        f'**Moderador:** {mod_name}\n'
                        f'**Data:** {timestamp}'
                    ),
                    inline=False
                )

            pages.append(embed)

        if len(pages) == 1:
            return await interaction.response.send_message(embed=pages[0])

        view = WarningsPaginationView(pages, interaction.user)
        await interaction.response.send_message(embed=pages[0], view=view)
        view.message = await interaction.original_response()

    # ════════════════════════════════════
    #  /clearwarns
    # ════════════════════════════════════

    @app_commands.command(name='clearwarns', description='Limpa todos os avisos de um usuário')
    @app_commands.describe(user='Usuário para limpar os avisos')
    @app_commands.checks.has_permissions(manage_guild=True)
    async def clearwarns(
        self,
        interaction: discord.Interaction,
        user: discord.Member
    ) -> None:
        warnings_list = await self.bot.db.get_warnings(interaction.guild.id, user.id)

        if not warnings_list:
            return await interaction.response.send_message(
                embed=error_embed(
                    '📋 Sem Avisos',
                    f'{user.mention} não possui avisos para limpar.'
                ),
                ephemeral=True
            )

        view = ClearWarnsConfirmView(moderator=interaction.user, target=user)

        embed = warning_embed(
            '⚠️ Confirmar Limpeza',
            f'Deseja realmente limpar **{len(warnings_list)}** aviso(s) de {user.mention}?\n\n'
            f'*Esta ação não pode ser desfeita.*'
        )

        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()

    # ════════════════════════════════════
    #  /purge
    # ════════════════════════════════════

    @app_commands.command(name='purge', description='Deleta mensagens do canal')
    @app_commands.describe(quantidade='Quantidade de mensagens a deletar (máx. 100)')
    @app_commands.checks.has_permissions(manage_messages=True)
    async def purge(
        self,
        interaction: discord.Interaction,
        quantidade: int
    ) -> None:
        if quantidade < 1 or quantidade > 100:
            return await interaction.response.send_message(
                embed=error_embed(
                    '❌ Quantidade Inválida',
                    'A quantidade deve ser entre 1 e 100 mensagens.'
                ),
                ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)

        deleted = await interaction.channel.purge(limit=quantidade)

        await interaction.followup.send(
            embed=success_embed(
                '🗑️ Mensagens Deletadas',
                f'**{len(deleted)}** mensagem(ns) foram deletadas deste canal.\n'
                f'**Moderador:** {interaction.user.mention}'
            ),
            ephemeral=True
        )

    # ════════════════════════════════════
    #  /slowmode
    # ════════════════════════════════════

    @app_commands.command(name='slowmode', description='Define o modo lento do canal')
    @app_commands.describe(segundos='Intervalo em segundos (0 para desativar)')
    @app_commands.checks.has_permissions(manage_channels=True)
    async def slowmode(
        self,
        interaction: discord.Interaction,
        segundos: int
    ) -> None:
        if segundos < 0 or segundos > 21600:
            return await interaction.response.send_message(
                embed=error_embed(
                    '❌ Valor Inválido',
                    'O slowmode deve ser entre 0 e 21600 segundos (6 horas).'
                ),
                ephemeral=True
            )

        await interaction.channel.edit(slowmode_delay=segundos)

        if segundos == 0:
            await interaction.response.send_message(
                embed=success_embed(
                    '💨 Slowmode Desativado',
                    f'O modo lento foi desativado em {interaction.channel.mention}.'
                )
            )
        else:
            await interaction.response.send_message(
                embed=success_embed(
                    '🐌 Slowmode Ativado',
                    f'O modo lento foi definido para **{segundos}s** em {interaction.channel.mention}.'
                )
            )

    # ════════════════════════════════════
    #  /lock
    # ════════════════════════════════════

    @app_commands.command(name='lock', description='Trava o canal atual')
    @app_commands.checks.has_permissions(manage_channels=True)
    async def lock(self, interaction: discord.Interaction) -> None:
        overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = False

        await interaction.channel.set_permissions(
            interaction.guild.default_role,
            overwrite=overwrite,
            reason=f'Canal trancado por {interaction.user}'
        )

        await interaction.response.send_message(
            embed=moderation_embed(
                '🔒 Canal Trancado',
                f'Este canal foi trancado por {interaction.user.mention}.\n'
                f'Apenas membros com permissão podem enviar mensagens.'
            )
        )

    # ════════════════════════════════════
    #  /unlock
    # ════════════════════════════════════

    @app_commands.command(name='unlock', description='Destrava o canal atual')
    @app_commands.checks.has_permissions(manage_channels=True)
    async def unlock(self, interaction: discord.Interaction) -> None:
        overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = None  # Reseta para padrão

        await interaction.channel.set_permissions(
            interaction.guild.default_role,
            overwrite=overwrite,
            reason=f'Canal destrancado por {interaction.user}'
        )

        await interaction.response.send_message(
            embed=success_embed(
                '🔓 Canal Destrancado',
                f'Este canal foi destrancado por {interaction.user.mention}.'
            )
        )

    # ════════════════════════════════════
    #  Error Handler
    # ════════════════════════════════════

    async def cog_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError
    ) -> None:
        """Handler de erros para todos os comandos deste cog."""
        if isinstance(error, app_commands.MissingPermissions):
            missing = ', '.join(error.missing_permissions)
            embed = error_embed(
                '⛔ Permissão Insuficiente',
                f'Você não tem as seguintes permissões: `{missing}`'
            )
        elif isinstance(error, app_commands.CommandOnCooldown):
            embed = warning_embed(
                '⏳ Cooldown',
                f'Aguarde **{error.retry_after:.1f}s** antes de usar este comando novamente.'
            )
        elif isinstance(error, app_commands.CommandInvokeError):
            original = error.original
            if isinstance(original, discord.Forbidden):
                embed = error_embed(
                    '❌ Sem Permissão',
                    'Não tenho permissão para executar esta ação. '
                    'Verifique a hierarquia de cargos e minhas permissões.'
                )
            else:
                embed = error_embed(
                    '❌ Erro Interno',
                    f'Ocorreu um erro inesperado: ```{original}```'
                )
        else:
            embed = error_embed(
                '❌ Erro',
                f'Ocorreu um erro: ```{error}```'
            )

        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)


# ════════════════════════════════════════
#  Setup
# ════════════════════════════════════════

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Moderation(bot))
