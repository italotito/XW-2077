"""
╔══════════════════════════════════════════════════════════╗
║  XW-2077 • Módulo de Utilidades                         ║
║  Comandos slash de informação e ferramentas              ║
╚══════════════════════════════════════════════════════════╝
"""

import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone
from typing import Optional

from config import Config
from utils.embeds import create_embed, success_embed, error_embed, info_embed, warning_embed


# ════════════════════════════════════════
#  Views
# ════════════════════════════════════════

class AvatarView(discord.ui.View):
    """Botões de link para download do avatar em diferentes formatos."""

    def __init__(self, user: discord.User | discord.Member):
        super().__init__(timeout=120)
        avatar_url = user.display_avatar

        self.add_item(discord.ui.Button(
            label='PNG',
            style=discord.ButtonStyle.link,
            url=str(avatar_url.replace(format='png', size=1024)),
            emoji='🖼️'
        ))
        self.add_item(discord.ui.Button(
            label='JPG',
            style=discord.ButtonStyle.link,
            url=str(avatar_url.replace(format='jpg', size=1024)),
            emoji='📸'
        ))
        self.add_item(discord.ui.Button(
            label='WEBP',
            style=discord.ButtonStyle.link,
            url=str(avatar_url.replace(format='webp', size=1024)),
            emoji='🌐'
        ))

        # Se o avatar for animado, adiciona GIF
        if avatar_url.is_animated():
            self.add_item(discord.ui.Button(
                label='GIF',
                style=discord.ButtonStyle.link,
                url=str(avatar_url.replace(format='gif', size=1024)),
                emoji='🎞️'
            ))


class HelpView(discord.ui.View):
    """Menu de seleção por categoria para o comando /help."""

    def __init__(self):
        super().__init__(timeout=180)

    @discord.ui.select(
        placeholder='🔍 Selecione uma categoria...',
        options=[
            discord.SelectOption(
                label='Moderação',
                description='Comandos de moderação do servidor',
                emoji='⚖️',
                value='moderation'
            ),
            discord.SelectOption(
                label='Utilitários',
                description='Informações e ferramentas úteis',
                emoji='🔧',
                value='utility'
            ),
            discord.SelectOption(
                label='Diversão',
                description='Jogos, memes e entretenimento',
                emoji='🎮',
                value='fun'
            ),
            discord.SelectOption(
                label='Música',
                description='Comandos de reprodução de música',
                emoji='🎵',
                value='music'
            ),
            discord.SelectOption(
                label='Welcome',
                description='Sistema de boas-vindas',
                emoji='👋',
                value='welcome'
            ),
            discord.SelectOption(
                label='Níveis',
                description='Sistema de XP e níveis',
                emoji='📊',
                value='levels'
            ),
            discord.SelectOption(
                label='Tickets',
                description='Sistema de tickets de suporte',
                emoji='🎫',
                value='tickets'
            ),
        ]
    )
    async def select_category(
        self,
        interaction: discord.Interaction,
        select: discord.ui.Select
    ) -> None:
        category = select.values[0]
        embed = self._get_category_embed(category)
        await interaction.response.edit_message(embed=embed, view=self)

    def _get_category_embed(self, category: str) -> discord.Embed:
        """Retorna o embed correspondente à categoria selecionada."""
        categories = {
            'moderation': {
                'title': '⚖️ Moderação',
                'color': Config.Colors.MODERATION,
                'commands': [
                    ('`/kick <user> [motivo]`', 'Expulsa um usuário do servidor'),
                    ('`/ban <user> [motivo]`', 'Bane um usuário (com confirmação)'),
                    ('`/unban <user_id>`', 'Remove banimento por ID'),
                    ('`/mute <user> [duração] [motivo]`', 'Silencia temporariamente'),
                    ('`/unmute <user>`', 'Remove silenciamento'),
                    ('`/warn <user> <motivo>`', 'Adiciona um aviso'),
                    ('`/warnings <user>`', 'Lista avisos de um usuário'),
                    ('`/clearwarns <user>`', 'Limpa todos os avisos'),
                    ('`/purge <quantidade>`', 'Deleta mensagens (máx. 100)'),
                    ('`/slowmode <segundos>`', 'Define modo lento'),
                    ('`/lock`', 'Trava o canal'),
                    ('`/unlock`', 'Destrava o canal'),
                ]
            },
            'utility': {
                'title': '🔧 Utilitários',
                'color': Config.Colors.INFO,
                'commands': [
                    ('`/avatar [user]`', 'Mostra avatar com links de download'),
                    ('`/userinfo [user]`', 'Informações detalhadas do usuário'),
                    ('`/serverinfo`', 'Informações do servidor'),
                    ('`/ping`', 'Latência do bot'),
                    ('`/help`', 'Este menu de ajuda'),
                    ('`/invite`', 'Link de convite do bot'),
                    ('`/uptime`', 'Tempo online do bot'),
                    ('`/embed`', 'Cria um embed customizado'),
                ]
            },
            'fun': {
                'title': '🎮 Diversão',
                'color': Config.Colors.FUN,
                'commands': [
                    ('`/meme`', 'Meme aleatório da internet'),
                    ('`/joke`', 'Piada aleatória'),
                    ('`/coinflip`', 'Cara ou Coroa'),
                    ('`/rps`', 'Pedra, Papel, Tesoura (com botões)'),
                    ('`/8ball <pergunta>`', 'Bola 8 mágica cyberpunk'),
                    ('`/roll [dados]`', 'Rola dados (ex: 2d6, d20)'),
                    ('`/choose <opções>`', 'Escolhe entre opções'),
                    ('`/tictactoe <oponente>`', 'Jogo da Velha com botões'),
                    ('`/trivia`', 'Quiz com botões A/B/C/D'),
                    ('`/poll <pergunta> <opções>`', 'Enquete com votos'),
                ]
            },
            'music': {
                'title': '🎵 Música',
                'color': Config.Colors.PRIMARY,
                'commands': [
                    ('`/play <url/busca>`', 'Toca uma música ou adiciona à fila'),
                    ('`/pause`', 'Pausa a reprodução'),
                    ('`/resume`', 'Retoma a reprodução'),
                    ('`/skip`', 'Pula para a próxima música'),
                    ('`/stop`', 'Para e desconecta o bot'),
                    ('`/queue`', 'Mostra a fila de músicas'),
                    ('`/volume <0-100>`', 'Ajusta o volume'),
                    ('`/nowplaying`', 'Mostra a música atual'),
                ]
            },
            'welcome': {
                'title': '👋 Welcome',
                'color': Config.Colors.SUCCESS,
                'commands': [
                    ('`/welcome setup <canal>`', 'Configura canal de boas-vindas'),
                    ('`/welcome message <texto>`', 'Define mensagem personalizada'),
                    ('`/welcome toggle`', 'Ativa/desativa o sistema'),
                    ('`/welcome test`', 'Testa a mensagem de boas-vindas'),
                ]
            },
            'levels': {
                'title': '📊 Níveis',
                'color': Config.Colors.SUCCESS,
                'commands': [
                    ('`/rank [user]`', 'Mostra XP e nível'),
                    ('`/leaderboard`', 'Ranking do servidor'),
                    ('`/setxp <user> <xp>`', 'Define XP manualmente'),
                    ('`/resetxp <user>`', 'Reseta XP de um usuário'),
                ]
            },
            'tickets': {
                'title': '🎫 Tickets',
                'color': Config.Colors.INFO,
                'commands': [
                    ('`/ticket setup`', 'Configura sistema de tickets'),
                    ('`/ticket close`', 'Fecha o ticket atual'),
                    ('`/ticket add <user>`', 'Adiciona usuário ao ticket'),
                    ('`/ticket remove <user>`', 'Remove usuário do ticket'),
                ]
            },
        }

        cat_data = categories.get(category, categories['utility'])

        embed = create_embed(
            title=cat_data['title'],
            description=f'Lista de comandos da categoria **{cat_data["title"]}**:',
            color=cat_data['color']
        )

        for cmd, desc in cat_data['commands']:
            embed.add_field(name=cmd, value=desc, inline=False)

        return embed


class EmbedCreatorModal(discord.ui.Modal, title='🛠️ Criar Embed'):
    """Modal para criação de embeds customizados."""

    titulo = discord.ui.TextInput(
        label='Título',
        placeholder='Título do embed...',
        max_length=256,
        style=discord.TextStyle.short
    )

    descricao = discord.ui.TextInput(
        label='Descrição',
        placeholder='Descrição do embed...',
        max_length=4000,
        style=discord.TextStyle.paragraph
    )

    cor = discord.ui.TextInput(
        label='Cor (hex)',
        placeholder='#00FFFF',
        default='#00FFFF',
        max_length=7,
        required=False,
        style=discord.TextStyle.short
    )

    imagem_url = discord.ui.TextInput(
        label='URL da Imagem',
        placeholder='https://exemplo.com/imagem.png',
        required=False,
        max_length=512,
        style=discord.TextStyle.short
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        # Parseia a cor
        try:
            color_str = self.cor.value.strip().lstrip('#')
            color = int(color_str, 16) if color_str else Config.Colors.PRIMARY
        except ValueError:
            color = Config.Colors.PRIMARY

        embed = create_embed(
            title=self.titulo.value,
            description=self.descricao.value,
            color=color
        )

        # Imagem opcional
        if self.imagem_url.value:
            embed.set_image(url=self.imagem_url.value)

        embed.set_footer(
            text=f'Embed criado por {interaction.user.display_name} • {Config.EMBED_FOOTER}'
        )

        await interaction.response.send_message(embed=embed)

    async def on_error(
        self,
        interaction: discord.Interaction,
        error: Exception
    ) -> None:
        await interaction.response.send_message(
            embed=error_embed(
                '❌ Erro ao Criar Embed',
                f'Ocorreu um erro: ```{error}```\nVerifique os campos e tente novamente.'
            ),
            ephemeral=True
        )


# ════════════════════════════════════════
#  Cog Principal
# ════════════════════════════════════════

class Utility(commands.Cog):
    """🔧 Comandos utilitários e de informação."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # ════════════════════════════════════
    #  /avatar
    # ════════════════════════════════════

    @app_commands.command(name='avatar', description='Mostra o avatar de um usuário')
    @app_commands.describe(user='Usuário para ver o avatar (padrão: você)')
    async def avatar(
        self,
        interaction: discord.Interaction,
        user: Optional[discord.User] = None
    ) -> None:
        target = user or interaction.user

        embed = create_embed(
            title=f'🖼️ Avatar de {target.display_name}',
            description=f'Avatar de {target.mention}',
            color=Config.Colors.PRIMARY
        )
        embed.set_image(url=target.display_avatar.replace(size=1024))

        view = AvatarView(target)
        await interaction.response.send_message(embed=embed, view=view)

    # ════════════════════════════════════
    #  /userinfo
    # ════════════════════════════════════

    @app_commands.command(name='userinfo', description='Mostra informações detalhadas de um usuário')
    @app_commands.describe(user='Usuário para ver informações (padrão: você)')
    async def userinfo(
        self,
        interaction: discord.Interaction,
        user: Optional[discord.Member] = None
    ) -> None:
        target = user or interaction.user

        # Badges
        badges = []
        if target.public_flags:
            flag_emojis = {
                'staff': '👨‍💻',
                'partner': '🤝',
                'hypesquad': '🏠',
                'bug_hunter': '🐛',
                'hypesquad_bravery': '💜',
                'hypesquad_brilliance': '🧡',
                'hypesquad_balance': '💚',
                'early_supporter': '⭐',
                'bug_hunter_level_2': '🐛',
                'verified_bot_developer': '🔨',
                'active_developer': '💻',
            }
            for flag in target.public_flags.all():
                emoji = flag_emojis.get(flag.name, '🏷️')
                badges.append(f'{emoji} {flag.name.replace("_", " ").title()}')

        # Status (se disponível)
        status_emojis = {
            discord.Status.online: '🟢 Online',
            discord.Status.idle: '🟡 Ausente',
            discord.Status.dnd: '🔴 Não Perturbe',
            discord.Status.offline: '⚫ Offline',
        }
        status_text = status_emojis.get(
            getattr(target, 'status', discord.Status.offline),
            '⚫ Offline'
        )

        embed = create_embed(
            title=f'👤 Informações de {target.display_name}',
            description=f'{target.mention} | `{target.id}`',
            color=target.color if target.color != discord.Color.default() else Config.Colors.PRIMARY
        )

        embed.set_thumbnail(url=target.display_avatar.replace(size=256))

        embed.add_field(name='📛 Nome', value=str(target), inline=True)
        embed.add_field(name='🆔 ID', value=f'`{target.id}`', inline=True)
        embed.add_field(name='📡 Status', value=status_text, inline=True)

        embed.add_field(
            name='📅 Conta Criada',
            value=f'<t:{int(target.created_at.timestamp())}:R>\n'
                  f'<t:{int(target.created_at.timestamp())}:F>',
            inline=True
        )

        if hasattr(target, 'joined_at') and target.joined_at:
            embed.add_field(
                name='📥 Entrou no Servidor',
                value=f'<t:{int(target.joined_at.timestamp())}:R>\n'
                      f'<t:{int(target.joined_at.timestamp())}:F>',
                inline=True
            )

        # Cargos
        roles = [role.mention for role in reversed(target.roles[1:])]  # Ignora @everyone
        if roles:
            # Limita a 10 cargos para não estourar o campo
            role_text = ' '.join(roles[:10])
            if len(roles) > 10:
                role_text += f'\n*... e mais {len(roles) - 10} cargo(s)*'
            embed.add_field(
                name=f'🎭 Cargos ({len(roles)})',
                value=role_text,
                inline=False
            )
        else:
            embed.add_field(name='🎭 Cargos', value='Nenhum cargo', inline=False)

        # Badges
        if badges:
            embed.add_field(
                name='🏅 Badges',
                value='\n'.join(badges),
                inline=False
            )

        # Cargo mais alto
        if target.top_role != interaction.guild.default_role:
            embed.add_field(
                name='👑 Cargo Mais Alto',
                value=target.top_role.mention,
                inline=True
            )

        # Boost
        if target.premium_since:
            embed.add_field(
                name='💎 Booster desde',
                value=f'<t:{int(target.premium_since.timestamp())}:R>',
                inline=True
            )

        await interaction.response.send_message(embed=embed)

    # ════════════════════════════════════
    #  /serverinfo
    # ════════════════════════════════════

    @app_commands.command(name='serverinfo', description='Mostra informações do servidor')
    async def serverinfo(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild

        # Contagem de canais
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        categories = len(guild.categories)
        total_channels = text_channels + voice_channels

        # Contagem de membros
        total_members = guild.member_count or len(guild.members)

        # Boost
        boost_levels = {0: '⬛', 1: '🟪', 2: '🟪🟪', 3: '🟪🟪🟪'}
        boost_display = boost_levels.get(guild.premium_tier, '⬛')

        embed = create_embed(
            title=f'🏰 {guild.name}',
            description=f'ID: `{guild.id}`',
            color=Config.Colors.PRIMARY
        )

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.replace(size=256))

        if guild.banner:
            embed.set_image(url=guild.banner.replace(size=1024))

        embed.add_field(
            name='👑 Dono',
            value=guild.owner.mention if guild.owner else 'Desconhecido',
            inline=True
        )
        embed.add_field(
            name='👥 Membros',
            value=f'{total_members}',
            inline=True
        )
        embed.add_field(
            name='🎭 Cargos',
            value=f'{len(guild.roles) - 1}',  # -1 para @everyone
            inline=True
        )

        embed.add_field(
            name='💬 Canais',
            value=f'📝 Texto: {text_channels}\n'
                  f'🔊 Voz: {voice_channels}\n'
                  f'📁 Categorias: {categories}\n'
                  f'**Total:** {total_channels}',
            inline=True
        )

        embed.add_field(
            name='💎 Boost',
            value=f'Nível: {guild.premium_tier} {boost_display}\n'
                  f'Boosts: {guild.premium_subscription_count or 0}',
            inline=True
        )

        embed.add_field(
            name='📅 Criado em',
            value=f'<t:{int(guild.created_at.timestamp())}:R>\n'
                  f'<t:{int(guild.created_at.timestamp())}:F>',
            inline=True
        )

        # Emojis e stickers
        embed.add_field(
            name='😀 Emojis',
            value=f'{len(guild.emojis)}/{guild.emoji_limit}',
            inline=True
        )
        embed.add_field(
            name='🔒 Verificação',
            value=str(guild.verification_level).replace('_', ' ').title(),
            inline=True
        )

        # Features notáveis
        if guild.features:
            notable_features = {
                'COMMUNITY': '🏘️ Comunidade',
                'VERIFIED': '✅ Verificado',
                'PARTNERED': '🤝 Parceiro',
                'DISCOVERABLE': '🔍 Descobrível',
                'ANIMATED_ICON': '🎞️ Ícone Animado',
                'BANNER': '🖼️ Banner',
                'VANITY_URL': '🔗 URL Personalizada',
            }
            features_text = []
            for f in guild.features:
                if f in notable_features:
                    features_text.append(notable_features[f])
            if features_text:
                embed.add_field(
                    name='⚡ Recursos',
                    value='\n'.join(features_text[:6]),
                    inline=False
                )

        await interaction.response.send_message(embed=embed)

    # ════════════════════════════════════
    #  /ping
    # ════════════════════════════════════

    @app_commands.command(name='ping', description='Verifica a latência do bot')
    async def ping(self, interaction: discord.Interaction) -> None:
        ws_latency = round(self.bot.latency * 1000)

        # Mede latência da API
        start = datetime.now(timezone.utc)
        await interaction.response.defer()
        end = datetime.now(timezone.utc)
        api_latency = round((end - start).total_seconds() * 1000)

        # Barras visuais
        def latency_bar(ms: int) -> str:
            if ms < 100:
                blocks = 1
                color = '🟢'
            elif ms < 200:
                blocks = 3
                color = '🟡'
            elif ms < 400:
                blocks = 5
                color = '🟠'
            else:
                blocks = 8
                color = '🔴'
            bar = '█' * blocks + '░' * (8 - blocks)
            return f'{color} `{bar}` **{ms}ms**'

        embed = create_embed(
            title='🏓 Pong!',
            description='Status de latência do sistema:',
            color=Config.Colors.PRIMARY
        )

        embed.add_field(
            name='📡 WebSocket',
            value=latency_bar(ws_latency),
            inline=False
        )
        embed.add_field(
            name='🌐 API Discord',
            value=latency_bar(api_latency),
            inline=False
        )

        # Status geral
        avg = (ws_latency + api_latency) // 2
        if avg < 150:
            status = '🟢 **Sistemas operacionais, netrunner.**'
        elif avg < 300:
            status = '🟡 **Latência detectada. Rede instável.**'
        else:
            status = '🔴 **Alerta: lag crítico no sistema.**'

        embed.add_field(name='📊 Status', value=status, inline=False)

        await interaction.followup.send(embed=embed)

    # ════════════════════════════════════
    #  /help
    # ════════════════════════════════════

    @app_commands.command(name='help', description='Mostra a lista de comandos por categoria')
    async def help(self, interaction: discord.Interaction) -> None:
        embed = create_embed(
            title=f'📖 {Config.BOT_NAME} — Central de Comandos',
            description=(
                'Bem-vindo ao sistema de ajuda, samurai.\n'
                'Selecione uma categoria no menu abaixo para ver os comandos disponíveis.\n\n'
                '**Categorias disponíveis:**\n'
                '⚖️ Moderação • 🔧 Utilitários • 🎮 Diversão\n'
                '🎵 Música • 👋 Welcome • 📊 Níveis • 🎫 Tickets'
            ),
            color=Config.Colors.PRIMARY
        )

        view = HelpView()
        await interaction.response.send_message(embed=embed, view=view)

    # ════════════════════════════════════
    #  /invite
    # ════════════════════════════════════

    @app_commands.command(name='invite', description='Gera o link de convite do bot')
    async def invite(self, interaction: discord.Interaction) -> None:
        permissions = discord.Permissions(
            administrator=False,
            manage_guild=True,
            manage_roles=True,
            manage_channels=True,
            kick_members=True,
            ban_members=True,
            manage_messages=True,
            embed_links=True,
            attach_files=True,
            read_message_history=True,
            send_messages=True,
            connect=True,
            speak=True,
            use_voice_activation=True,
            moderate_members=True,
        )

        invite_url = discord.utils.oauth_url(
            self.bot.user.id,
            permissions=permissions
        )

        embed = create_embed(
            title=f'🔗 Convite do {Config.BOT_NAME}',
            description=(
                f'Clique no botão abaixo para me adicionar ao seu servidor!\n\n'
                f'Ou copie o link:\n```{invite_url}```'
            ),
            color=Config.Colors.PRIMARY
        )

        view = discord.ui.View()
        view.add_item(discord.ui.Button(
            label='Adicionar ao Servidor',
            style=discord.ButtonStyle.link,
            url=invite_url,
            emoji='🤖'
        ))

        await interaction.response.send_message(embed=embed, view=view)

    # ════════════════════════════════════
    #  /uptime
    # ════════════════════════════════════

    @app_commands.command(name='uptime', description='Mostra o tempo online do bot')
    async def uptime(self, interaction: discord.Interaction) -> None:
        if not hasattr(self.bot, 'start_time') or self.bot.start_time is None:
            return await interaction.response.send_message(
                embed=error_embed(
                    '❌ Indisponível',
                    'Tempo de inicialização não registrado.'
                ),
                ephemeral=True
            )

        now = datetime.now(timezone.utc)
        delta = now - self.bot.start_time

        days = delta.days
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        parts = []
        if days > 0:
            parts.append(f'**{days}** dia(s)')
        if hours > 0:
            parts.append(f'**{hours}** hora(s)')
        if minutes > 0:
            parts.append(f'**{minutes}** minuto(s)')
        parts.append(f'**{seconds}** segundo(s)')

        uptime_str = ', '.join(parts)

        embed = create_embed(
            title='⏱️ Uptime do Sistema',
            description=(
                f'O {Config.BOT_NAME} está online há:\n\n'
                f'🕐 {uptime_str}\n\n'
                f'**Iniciado em:** <t:{int(self.bot.start_time.timestamp())}:F>'
            ),
            color=Config.Colors.SUCCESS
        )

        await interaction.response.send_message(embed=embed)

    # ════════════════════════════════════
    #  /embed
    # ════════════════════════════════════

    @app_commands.command(name='embed', description='Cria um embed customizado usando um formulário')
    async def embed(self, interaction: discord.Interaction) -> None:
        modal = EmbedCreatorModal()
        await interaction.response.send_modal(modal)

    # ════════════════════════════════════
    #  Error Handler
    # ════════════════════════════════════

    async def cog_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError
    ) -> None:
        if isinstance(error, app_commands.CommandInvokeError):
            original = error.original
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
    await bot.add_cog(Utility(bot))
