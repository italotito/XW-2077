"""
╔══════════════════════════════════════════════════════════╗
║  XW-2077 • Módulo de Diversão                           ║
║  Jogos, memes e entretenimento cyberpunk                 ║
╚══════════════════════════════════════════════════════════╝
"""

import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import random
import re
import html
from typing import Optional
from datetime import datetime, timezone

from config import Config
from utils.embeds import create_embed, success_embed, error_embed, info_embed, warning_embed


# ════════════════════════════════════════
#  Constantes
# ════════════════════════════════════════

EIGHTBALL_POSITIVE = [
    'Os circuitos indicam que sim.',
    'A matrix confirma.',
    'Sem dúvida, netrunner.',
    'Os dados do sistema apontam que sim.',
    'Positivo, choom.',
    'O mainframe diz sim.',
    'Análise concluída: afirmativo.',
    'Todos os algoritmos concordam: sim.',
]

EIGHTBALL_NEUTRAL = [
    'Os servidores estão instáveis, tente novamente.',
    'Não consigo decifrar... pergunte depois.',
    'Firewall bloqueando a resposta...',
    'Sinal fraco. Recalibrando...',
    'Dados corrompidos. Tente mais tarde.',
    'A rede está congestionada. Repita a consulta.',
]

EIGHTBALL_NEGATIVE = [
    'Negativo, chrome.',
    'A rede diz que não.',
    'Os algoritmos dizem que não.',
    'Sem chance, samurai.',
    'Bug no sistema: resposta = não.',
    'Análise completa: negativo.',
    'A matrix rejeitou sua consulta.',
    'Erro 404: esperança não encontrada.',
]

RPS_WINS = {'pedra': 'tesoura', 'tesoura': 'papel', 'papel': 'pedra'}
RPS_EMOJIS = {'pedra': '🪨', 'papel': '📄', 'tesoura': '✂️'}

TRIVIA_LETTERS = ['A', 'B', 'C', 'D']
TRIVIA_COLORS = [
    discord.ButtonStyle.primary,
    discord.ButtonStyle.success,
    discord.ButtonStyle.danger,
    discord.ButtonStyle.secondary,
]


# ════════════════════════════════════════
#  Views
# ════════════════════════════════════════

class MemeView(discord.ui.View):
    """Botão para buscar outro meme."""

    def __init__(self):
        super().__init__(timeout=120)

    @discord.ui.button(label='Outro Meme', style=discord.ButtonStyle.primary, emoji='🔄')
    async def another_meme(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ) -> None:
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get('https://meme-api.com/gimme') as r:
                    if r.status == 200:
                        data = await r.json()
                        embed = create_embed(
                            title=data.get('title', 'Meme'),
                            description=f'👍 {data.get("ups", 0)} | r/{data.get("subreddit", "memes")}',
                            color=Config.Colors.FUN
                        )
                        embed.set_image(url=data['url'])

                        await interaction.response.edit_message(embed=embed, view=self)
                    else:
                        await interaction.response.send_message(
                            embed=error_embed('❌ Erro', 'Falha ao buscar meme. Tente novamente.'),
                            ephemeral=True
                        )
            except Exception:
                await interaction.response.send_message(
                    embed=error_embed('❌ Erro', 'A API de memes está offline.'),
                    ephemeral=True
                )


class RPSView(discord.ui.View):
    """Botões de Pedra, Papel, Tesoura."""

    def __init__(self, author: discord.Member):
        super().__init__(timeout=30)
        self.author = author
        self.message: Optional[discord.Message] = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author.id:
            await interaction.response.send_message(
                embed=error_embed(
                    '⛔ Acesso Negado',
                    'Apenas quem iniciou o jogo pode jogar!'
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
                        'Você demorou demais, samurai. O jogo foi cancelado.'
                    ),
                    view=self
                )
            except discord.HTTPException:
                pass

    def _get_result(self, user_choice: str) -> tuple[str, str, discord.Embed]:
        """Determina o resultado do jogo."""
        bot_choice = random.choice(list(RPS_WINS.keys()))
        bot_emoji = RPS_EMOJIS[bot_choice]
        user_emoji = RPS_EMOJIS[user_choice]

        if user_choice == bot_choice:
            result = 'empate'
            title = '🤝 Empate!'
            description = (
                f'**Você:** {user_emoji} {user_choice.title()}\n'
                f'**{Config.BOT_NAME}:** {bot_emoji} {bot_choice.title()}\n\n'
                f'*Ambos na mesma frequência neural. Interessante...*'
            )
            color = Config.Colors.WARNING
        elif RPS_WINS[user_choice] == bot_choice:
            result = 'vitória'
            title = '🎉 Você Ganhou!'
            description = (
                f'**Você:** {user_emoji} {user_choice.title()}\n'
                f'**{Config.BOT_NAME}:** {bot_emoji} {bot_choice.title()}\n\n'
                f'*Tch... sorte de iniciante. Ou talvez você seja bom mesmo, choom.*'
            )
            color = Config.Colors.SUCCESS
        else:
            result = 'derrota'
            title = '🤖 Eu Ganhei!'
            description = (
                f'**Você:** {user_emoji} {user_choice.title()}\n'
                f'**{Config.BOT_NAME}:** {bot_emoji} {bot_choice.title()}\n\n'
                f'*HAHAHAH! Meus algoritmos são superiores, meatbag!*'
            )
            color = Config.Colors.ERROR

        embed = create_embed(title=title, description=description, color=color)
        return result, bot_choice, embed

    async def _handle_choice(
        self,
        interaction: discord.Interaction,
        choice: str
    ) -> None:
        for item in self.children:
            item.disabled = True

        _, _, embed = self._get_result(choice)
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()

    @discord.ui.button(label='Pedra', style=discord.ButtonStyle.secondary, emoji='🪨')
    async def rock(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._handle_choice(interaction, 'pedra')

    @discord.ui.button(label='Papel', style=discord.ButtonStyle.secondary, emoji='📄')
    async def paper(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._handle_choice(interaction, 'papel')

    @discord.ui.button(label='Tesoura', style=discord.ButtonStyle.secondary, emoji='✂️')
    async def scissors(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self._handle_choice(interaction, 'tesoura')


class TicTacToeButton(discord.ui.Button['TicTacToeView']):
    """Botão individual do Jogo da Velha."""

    def __init__(self, x: int, y: int):
        super().__init__(style=discord.ButtonStyle.secondary, label='\u200b', row=y)
        self.x = x
        self.y = y

    async def callback(self, interaction: discord.Interaction) -> None:
        view: TicTacToeView = self.view

        # Verifica se é a vez do jogador
        if interaction.user.id != view.current_player.id:
            return await interaction.response.send_message(
                embed=error_embed('⛔ Não é sua vez', 'Aguarde sua vez, choom.'),
                ephemeral=True
            )

        # Marca a posição
        if view.current_player == view.player_x:
            self.label = '❌'
            self.style = discord.ButtonStyle.danger
            view.board[self.y][self.x] = 'X'
            view.current_player = view.player_o
        else:
            self.label = '⭕'
            self.style = discord.ButtonStyle.primary
            view.board[self.y][self.x] = 'O'
            view.current_player = view.player_x

        self.disabled = True

        # Verifica vitória ou empate
        winner = view.check_winner()
        if winner:
            # Destaca a linha vencedora
            if winner != 'empate':
                for btn in view.children:
                    if isinstance(btn, TicTacToeButton):
                        if (btn.y, btn.x) in view.winning_line:
                            btn.style = discord.ButtonStyle.success
                        btn.disabled = True

                winner_player = view.player_x if winner == 'X' else view.player_o
                embed = create_embed(
                    title='🎮 Jogo da Velha — Fim!',
                    description=(
                        f'🏆 **{winner_player.display_name}** venceu!\n\n'
                        f'❌ {view.player_x.display_name} vs ⭕ {view.player_o.display_name}'
                    ),
                    color=Config.Colors.SUCCESS
                )
            else:
                for btn in view.children:
                    if isinstance(btn, TicTacToeButton):
                        btn.disabled = True

                embed = create_embed(
                    title='🎮 Jogo da Velha — Empate!',
                    description=(
                        f'🤝 Deu velha!\n\n'
                        f'❌ {view.player_x.display_name} vs ⭕ {view.player_o.display_name}'
                    ),
                    color=Config.Colors.WARNING
                )

            view.stop()
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            embed = create_embed(
                title='🎮 Jogo da Velha',
                description=(
                    f'Vez de: **{view.current_player.display_name}** '
                    f'({"❌" if view.current_player == view.player_x else "⭕"})\n\n'
                    f'❌ {view.player_x.display_name} vs ⭕ {view.player_o.display_name}'
                ),
                color=Config.Colors.FUN
            )
            await interaction.response.edit_message(embed=embed, view=view)


class TicTacToeView(discord.ui.View):
    """Grid 3x3 de botões para Jogo da Velha."""

    def __init__(self, player_x: discord.Member, player_o: discord.Member):
        super().__init__(timeout=120)
        self.player_x = player_x
        self.player_o = player_o
        self.current_player = player_x
        self.board: list[list[Optional[str]]] = [
            [None, None, None],
            [None, None, None],
            [None, None, None],
        ]
        self.winning_line: list[tuple[int, int]] = []

        # Cria grid 3x3
        for y in range(3):
            for x in range(3):
                self.add_item(TicTacToeButton(x, y))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id not in (self.player_x.id, self.player_o.id):
            await interaction.response.send_message(
                embed=error_embed(
                    '⛔ Acesso Negado',
                    'Apenas os dois jogadores podem interagir!'
                ),
                ephemeral=True
            )
            return False
        return True

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True

    def check_winner(self) -> Optional[str]:
        """Verifica se há um vencedor ou empate. Retorna 'X', 'O', 'empate' ou None."""
        lines = []
        # Linhas horizontais
        for y in range(3):
            lines.append([(y, x) for x in range(3)])
        # Linhas verticais
        for x in range(3):
            lines.append([(y, x) for y in range(3)])
        # Diagonais
        lines.append([(i, i) for i in range(3)])
        lines.append([(i, 2 - i) for i in range(3)])

        for line in lines:
            values = [self.board[y][x] for y, x in line]
            if values[0] and values[0] == values[1] == values[2]:
                self.winning_line = line
                return values[0]

        # Verifica empate
        if all(self.board[y][x] is not None for y in range(3) for x in range(3)):
            return 'empate'

        return None


class TriviaView(discord.ui.View):
    """Botões A/B/C/D para trivia."""

    def __init__(
        self,
        author: discord.Member,
        correct_index: int,
        answers: list[str],
        correct_answer: str
    ):
        super().__init__(timeout=30)
        self.author = author
        self.correct_index = correct_index
        self.answers = answers
        self.correct_answer = correct_answer
        self.answered = False
        self.message: Optional[discord.Message] = None

        for i, answer in enumerate(answers):
            button = discord.ui.Button(
                label=f'{TRIVIA_LETTERS[i]}: {answer[:60]}',
                style=TRIVIA_COLORS[i],
                custom_id=f'trivia_{i}',
                row=i // 2  # 2 buttons per row
            )
            button.callback = self._make_callback(i)
            self.add_item(button)

    def _make_callback(self, index: int):
        async def callback(interaction: discord.Interaction) -> None:
            if interaction.user.id != self.author.id:
                return await interaction.response.send_message(
                    embed=error_embed(
                        '⛔ Acesso Negado',
                        'Apenas quem iniciou o quiz pode responder!'
                    ),
                    ephemeral=True
                )

            if self.answered:
                return

            self.answered = True

            # Desabilita todos os botões e marca correto/incorreto
            for item in self.children:
                if isinstance(item, discord.ui.Button):
                    item.disabled = True
                    btn_idx = int(item.custom_id.split('_')[1])
                    if btn_idx == self.correct_index:
                        item.style = discord.ButtonStyle.success
                        item.label = f'✅ {item.label}'
                    elif btn_idx == index and index != self.correct_index:
                        item.style = discord.ButtonStyle.danger
                        item.label = f'❌ {item.label}'

            if index == self.correct_index:
                embed = create_embed(
                    title='✅ Correto!',
                    description=(
                        f'Boa, netrunner! A resposta era:\n'
                        f'**{self.correct_answer}**'
                    ),
                    color=Config.Colors.SUCCESS
                )
            else:
                embed = create_embed(
                    title='❌ Incorreto!',
                    description=(
                        f'Errou, choom! A resposta correta era:\n'
                        f'**{self.correct_answer}**\n\n'
                        f'Você respondeu: **{self.answers[index]}**'
                    ),
                    color=Config.Colors.ERROR
                )

            await interaction.response.edit_message(embed=embed, view=self)
            self.stop()

        return callback

    async def on_timeout(self) -> None:
        if self.answered:
            return

        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
                btn_idx = int(item.custom_id.split('_')[1])
                if btn_idx == self.correct_index:
                    item.style = discord.ButtonStyle.success
                    item.label = f'✅ {item.label}'

        embed = create_embed(
            title='⏰ Tempo Esgotado!',
            description=(
                f'Muito lento, samurai! A resposta correta era:\n'
                f'**{self.correct_answer}**'
            ),
            color=Config.Colors.WARNING
        )

        if self.message:
            try:
                await self.message.edit(embed=embed, view=self)
            except discord.HTTPException:
                pass


class PollView(discord.ui.View):
    """Botões de votação para enquete."""

    def __init__(
        self,
        question: str,
        options: list[str],
        author: discord.Member
    ):
        super().__init__(timeout=300)  # 5 minutos
        self.question = question
        self.options = options
        self.author = author
        self.votes: dict[str, set[int]] = {opt: set() for opt in options}
        self.message: Optional[discord.Message] = None

        poll_emojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣']

        for i, option in enumerate(options):
            button = discord.ui.Button(
                label=option[:40],
                style=discord.ButtonStyle.secondary,
                custom_id=f'poll_{i}',
                emoji=poll_emojis[i]
            )
            button.callback = self._make_callback(option)
            self.add_item(button)

    def _make_callback(self, option: str):
        async def callback(interaction: discord.Interaction) -> None:
            user_id = interaction.user.id

            # Remove voto anterior (se houver) e adiciona novo
            for opt, voters in self.votes.items():
                voters.discard(user_id)

            self.votes[option].add(user_id)

            embed = self._build_embed()
            await interaction.response.edit_message(embed=embed, view=self)

        return callback

    def _build_embed(self) -> discord.Embed:
        """Constrói o embed da enquete com barras de progresso."""
        total_votes = sum(len(v) for v in self.votes.values())

        embed = create_embed(
            title='📊 Enquete',
            description=f'**{self.question}**\n\n'
                        f'Votos totais: **{total_votes}**',
            color=Config.Colors.FUN
        )

        poll_emojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣']

        for i, (option, voters) in enumerate(self.votes.items()):
            count = len(voters)
            percentage = (count / total_votes * 100) if total_votes > 0 else 0

            # Barra visual
            filled = round(percentage / 10)
            bar = '█' * filled + '░' * (10 - filled)

            embed.add_field(
                name=f'{poll_emojis[i]} {option}',
                value=f'`{bar}` **{percentage:.0f}%** ({count} voto(s))',
                inline=False
            )

        embed.set_footer(text=f'Criado por {self.author.display_name} • {Config.EMBED_FOOTER}')
        return embed

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True

        embed = self._build_embed()
        embed.title = '📊 Enquete — Encerrada'
        embed.color = Config.Colors.WARNING

        if self.message:
            try:
                await self.message.edit(embed=embed, view=self)
            except discord.HTTPException:
                pass


# ════════════════════════════════════════
#  Cog Principal
# ════════════════════════════════════════

class Fun(commands.Cog):
    """🎮 Comandos de diversão e entretenimento."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # ════════════════════════════════════
    #  /meme
    # ════════════════════════════════════

    @app_commands.command(name='meme', description='Busca um meme aleatório da internet')
    async def meme(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get('https://meme-api.com/gimme') as r:
                    if r.status == 200:
                        data = await r.json()

                        embed = create_embed(
                            title=data.get('title', 'Meme'),
                            description=f'👍 {data.get("ups", 0)} | r/{data.get("subreddit", "memes")}',
                            color=Config.Colors.FUN
                        )
                        embed.set_image(url=data['url'])

                        view = MemeView()
                        await interaction.followup.send(embed=embed, view=view)
                    else:
                        await interaction.followup.send(
                            embed=error_embed('❌ Erro', 'Falha ao buscar meme. Tente novamente.')
                        )
            except Exception:
                await interaction.followup.send(
                    embed=error_embed('❌ Erro', 'A API de memes está offline, choom.')
                )

    # ════════════════════════════════════
    #  /joke
    # ════════════════════════════════════

    @app_commands.command(name='joke', description='Conta uma piada aleatória')
    async def joke(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get('https://official-joke-api.appspot.com/random_joke') as r:
                    if r.status == 200:
                        data = await r.json()

                        embed = create_embed(
                            title='😂 Piada',
                            description=(
                                f'**{data["setup"]}**\n\n'
                                f'||{data["punchline"]}||'
                            ),
                            color=Config.Colors.FUN
                        )
                        embed.set_footer(text=f'Tipo: {data.get("type", "N/A")} • {Config.EMBED_FOOTER}')

                        await interaction.followup.send(embed=embed)
                    else:
                        await interaction.followup.send(
                            embed=error_embed('❌ Erro', 'Falha ao buscar piada.')
                        )
            except Exception:
                await interaction.followup.send(
                    embed=error_embed('❌ Erro', 'A API de piadas está offline.')
                )

    # ════════════════════════════════════
    #  /coinflip
    # ════════════════════════════════════

    @app_commands.command(name='coinflip', description='Joga uma moeda — Cara ou Coroa')
    async def coinflip(self, interaction: discord.Interaction) -> None:
        result = random.choice(['Cara', 'Coroa'])
        emoji = '👤' if result == 'Cara' else '👑'

        embed = create_embed(
            title='🪙 Coinflip',
            description=(
                f'A moeda girou no ar...\n\n'
                f'{emoji} **{result}!**'
            ),
            color=Config.Colors.FUN
        )

        await interaction.response.send_message(embed=embed)

    # ════════════════════════════════════
    #  /rps (com botões)
    # ════════════════════════════════════

    @app_commands.command(name='rps', description='Jogue Pedra, Papel ou Tesoura')
    async def rps(self, interaction: discord.Interaction) -> None:
        view = RPSView(author=interaction.user)

        embed = create_embed(
            title='🎮 Pedra, Papel, Tesoura',
            description=(
                f'Faça sua escolha, {interaction.user.display_name}!\n\n'
                f'🪨 **Pedra** • 📄 **Papel** • ✂️ **Tesoura**\n\n'
                f'*Meus circuitos já calcularam a jogada perfeita...*'
            ),
            color=Config.Colors.FUN
        )

        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()

    # ════════════════════════════════════
    #  /8ball
    # ════════════════════════════════════

    @app_commands.command(name='8ball', description='Consulte a bola 8 mágica cyberpunk')
    @app_commands.describe(pergunta='Sua pergunta para a bola 8')
    async def eightball(
        self,
        interaction: discord.Interaction,
        pergunta: str
    ) -> None:
        category = random.choices(
            ['positive', 'neutral', 'negative'],
            weights=[45, 20, 35],
            k=1
        )[0]

        responses = {
            'positive': EIGHTBALL_POSITIVE,
            'neutral': EIGHTBALL_NEUTRAL,
            'negative': EIGHTBALL_NEGATIVE,
        }
        colors = {
            'positive': Config.Colors.SUCCESS,
            'neutral': Config.Colors.WARNING,
            'negative': Config.Colors.ERROR,
        }
        emojis = {
            'positive': '🟢',
            'neutral': '🟡',
            'negative': '🔴',
        }

        response = random.choice(responses[category])

        embed = create_embed(
            title='🎱 Bola 8 Cyberpunk',
            description=(
                f'**Pergunta:** {pergunta}\n\n'
                f'{emojis[category]} **Resposta:** *{response}*'
            ),
            color=colors[category]
        )

        await interaction.response.send_message(embed=embed)

    # ════════════════════════════════════
    #  /roll
    # ════════════════════════════════════

    @app_commands.command(name='roll', description='Rola dados (ex: 2d6, d20, 3d8)')
    @app_commands.describe(dados='Formato NdM (ex: 2d6, d20, 3d8). Padrão: 1d6')
    async def roll(
        self,
        interaction: discord.Interaction,
        dados: str = '1d6'
    ) -> None:
        # Parse NdM format
        match = re.match(r'^(\d*)d(\d+)$', dados.strip().lower())

        if not match:
            return await interaction.response.send_message(
                embed=error_embed(
                    '❌ Formato Inválido',
                    'Use o formato `NdM` (ex: `2d6`, `d20`, `3d8`).\n'
                    '`N` = quantidade de dados, `M` = lados do dado.'
                ),
                ephemeral=True
            )

        num_dice = int(match.group(1)) if match.group(1) else 1
        num_sides = int(match.group(2))

        if num_dice < 1 or num_dice > 20:
            return await interaction.response.send_message(
                embed=error_embed('❌ Erro', 'Quantidade de dados deve ser entre 1 e 20.'),
                ephemeral=True
            )

        if num_sides < 2 or num_sides > 100:
            return await interaction.response.send_message(
                embed=error_embed('❌ Erro', 'Lados do dado devem ser entre 2 e 100.'),
                ephemeral=True
            )

        rolls = [random.randint(1, num_sides) for _ in range(num_dice)]
        total = sum(rolls)

        # Formata resultados
        rolls_str = ' + '.join(f'`{r}`' for r in rolls)

        embed = create_embed(
            title='🎲 Rolagem de Dados',
            description=(
                f'**Dado:** {num_dice}d{num_sides}\n\n'
                f'**Resultados:** {rolls_str}\n'
                f'**Total:** **{total}**'
            ),
            color=Config.Colors.FUN
        )

        # Easter eggs
        if num_sides == 20:
            if total == 20:
                embed.add_field(
                    name='🎯 CRITICAL HIT!',
                    value='*Nat 20, samurai! A matrix está ao seu favor!*',
                    inline=False
                )
            elif total == 1:
                embed.add_field(
                    name='💀 CRITICAL FAIL!',
                    value='*Nat 1... seus implantes falharam.*',
                    inline=False
                )

        await interaction.response.send_message(embed=embed)

    # ════════════════════════════════════
    #  /choose
    # ════════════════════════════════════

    @app_commands.command(name='choose', description='Escolhe aleatoriamente entre opções')
    @app_commands.describe(opções='Opções separadas por vírgula (ex: pizza, hambúrguer, sushi)')
    async def choose(
        self,
        interaction: discord.Interaction,
        opções: str
    ) -> None:
        choices = [c.strip() for c in opções.split(',') if c.strip()]

        if len(choices) < 2:
            return await interaction.response.send_message(
                embed=error_embed(
                    '❌ Poucas Opções',
                    'Forneça pelo menos 2 opções separadas por vírgula.'
                ),
                ephemeral=True
            )

        chosen = random.choice(choices)
        options_formatted = '\n'.join(f'• {c}' for c in choices)

        embed = create_embed(
            title='🤔 Escolha Aleatória',
            description=(
                f'**Opções:**\n{options_formatted}\n\n'
                f'🎯 **Minha escolha:** **{chosen}**\n\n'
                f'*Os algoritmos decidiram. Não discuta com a máquina.*'
            ),
            color=Config.Colors.FUN
        )

        await interaction.response.send_message(embed=embed)

    # ════════════════════════════════════
    #  /tictactoe
    # ════════════════════════════════════

    @app_commands.command(name='tictactoe', description='Jogue Jogo da Velha com alguém')
    @app_commands.describe(oponente='Seu oponente')
    async def tictactoe(
        self,
        interaction: discord.Interaction,
        oponente: discord.Member
    ) -> None:
        if oponente.id == interaction.user.id:
            return await interaction.response.send_message(
                embed=error_embed(
                    '❌ Erro',
                    'Você não pode jogar contra si mesmo, samurai.'
                ),
                ephemeral=True
            )

        if oponente.bot:
            return await interaction.response.send_message(
                embed=error_embed(
                    '❌ Erro',
                    'Bots não jogam Jogo da Velha... ainda.'
                ),
                ephemeral=True
            )

        view = TicTacToeView(player_x=interaction.user, player_o=oponente)

        embed = create_embed(
            title='🎮 Jogo da Velha',
            description=(
                f'Vez de: **{interaction.user.display_name}** (❌)\n\n'
                f'❌ {interaction.user.display_name} vs ⭕ {oponente.display_name}'
            ),
            color=Config.Colors.FUN
        )

        await interaction.response.send_message(embed=embed, view=view)

    # ════════════════════════════════════
    #  /trivia
    # ════════════════════════════════════

    @app_commands.command(name='trivia', description='Quiz de conhecimentos gerais com timer')
    async def trivia(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    'https://opentdb.com/api.php?amount=1&type=multiple'
                ) as r:
                    if r.status != 200:
                        return await interaction.followup.send(
                            embed=error_embed('❌ Erro', 'Falha ao buscar pergunta.')
                        )

                    data = await r.json()

                    if data['response_code'] != 0 or not data['results']:
                        return await interaction.followup.send(
                            embed=error_embed('❌ Erro', 'API de trivia sem perguntas disponíveis.')
                        )

                    question_data = data['results'][0]
                    question = html.unescape(question_data['question'])
                    correct = html.unescape(question_data['correct_answer'])
                    incorrect = [html.unescape(a) for a in question_data['incorrect_answers']]
                    category = html.unescape(question_data['category'])
                    difficulty = question_data['difficulty']

                    # Embaralha as respostas
                    answers = incorrect + [correct]
                    random.shuffle(answers)
                    correct_index = answers.index(correct)

                    difficulty_emojis = {
                        'easy': '🟢 Fácil',
                        'medium': '🟡 Médio',
                        'hard': '🔴 Difícil',
                    }

                    embed = create_embed(
                        title='🧠 Trivia',
                        description=(
                            f'**Categoria:** {category}\n'
                            f'**Dificuldade:** {difficulty_emojis.get(difficulty, difficulty)}\n\n'
                            f'**{question}**\n\n'
                            f'*Você tem 30 segundos para responder!*'
                        ),
                        color=Config.Colors.FUN
                    )

                    view = TriviaView(
                        author=interaction.user,
                        correct_index=correct_index,
                        answers=answers,
                        correct_answer=correct
                    )

                    msg = await interaction.followup.send(embed=embed, view=view)
                    view.message = msg

            except Exception as e:
                await interaction.followup.send(
                    embed=error_embed('❌ Erro', f'Erro ao buscar trivia: ```{e}```')
                )

    # ════════════════════════════════════
    #  /poll
    # ════════════════════════════════════

    @app_commands.command(name='poll', description='Cria uma enquete com botões de voto')
    @app_commands.describe(
        pergunta='A pergunta da enquete',
        opção1='Primeira opção',
        opção2='Segunda opção',
        opção3='Terceira opção (opcional)',
        opção4='Quarta opção (opcional)'
    )
    async def poll(
        self,
        interaction: discord.Interaction,
        pergunta: str,
        opção1: str,
        opção2: str,
        opção3: Optional[str] = None,
        opção4: Optional[str] = None
    ) -> None:
        options = [opção1, opção2]
        if opção3:
            options.append(opção3)
        if opção4:
            options.append(opção4)

        view = PollView(question=pergunta, options=options, author=interaction.user)

        embed = view._build_embed()
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()

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
    await bot.add_cog(Fun(bot))
