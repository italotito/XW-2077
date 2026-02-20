import discord
from discord.ext import commands
import yt_dlp
import asyncio
import random
import os
import aiohttp
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

# --- CONFIGURAÇÃO DE INTENTS ---
# Habilita as intents necessárias, incluindo a para ler mensagens
intents = discord.Intents.default()
intents.members = True
intents.message_content = True 

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None) # Remove o comando de ajuda padrão

# ===================================
#         CONFIGS GLOBAIS / UTILS
# ===================================

# Opções para o yt-dlp e ffmpeg
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',  # bind to ipv4 since ipv6 addresses cause issues sometimes
}
ffmpeg_options = {
    'options': '-vn',
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
}
ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

# Fila de música agora é mais robusta
music_queues = {}  # { guild_id: [url1, url2, ...] }

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # Pega o primeiro item de uma playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

# Função para tocar a próxima música da fila
def play_next(ctx):
    guild_id = ctx.guild.id
    if guild_id in music_queues and music_queues[guild_id]:
        # Pega a próxima música da fila
        next_url = music_queues[guild_id].pop(0)
        # Cria uma corrotina para tocar a próxima música
        coro = play_music(ctx, next_url)
        # Executa a corrotina
        fut = asyncio.run_coroutine_threadsafe(coro, bot.loop)
        try:
            fut.result()
        except Exception as e:
            print(f"Erro ao tocar a próxima música: {e}")

# Função auxiliar para tocar música, usada por !play e play_next
async def play_music(ctx, url: str):
    vc = ctx.voice_client
    try:
        player = await YTDLSource.from_url(url, loop=bot.loop, stream=True)
        # A função 'after' é a chave para a fila funcionar
        vc.play(player, after=lambda e: play_next(ctx) if e is None else print(f'Erro na reprodução: {e}'))
        await ctx.send(f'🎶 Tocando agora: **{player.title}**')
    except Exception as e:
        await ctx.send(f'❌ Ocorreu um erro ao tentar tocar a música: `{e}`')

# ===================================
#              EVENTOS
# ===================================
@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user} (ID: {bot.user.id})')
    print('------')

# ===================================
#           COMANDOS BÁSICOS
# ===================================
@bot.command()
async def ping(ctx):
    """Verifica a latência do bot."""
    ms = round(bot.latency * 1000)
    await ctx.send(f'Pong! 🏓 `{ms}ms`')

@bot.command(name='help')
async def help_command(ctx):
    """Lista todos os comandos disponíveis."""
    embed = discord.Embed(title='📖 Lista de Comandos', description="Use `!` antes de cada comando.", color=discord.Color.blurple())

    # Organiza os comandos por categoria (se você usar Cogs no futuro, isso pode ser melhorado)
    command_map = {
        "Básicos": ["ping", "help", "avatar", "userinfo"],
        "Moderação": ["kick", "ban", "mute", "unmute", "warn"],
        "Música": ["play", "pause", "resume", "stop", "skip", "volume", "queue", "showqueue"],
        "Diversão": ["meme", "joke", "coinflip", "rps"]
    }

    for category, cmd_list in command_map.items():
        field_value = ""
        for cmd_name in cmd_list:
            cmd = bot.get_command(cmd_name)
            if cmd:
                field_value += f"`{cmd.name}`: {cmd.help or 'Sem descrição.'}\n"
        if field_value:
             embed.add_field(name=f"**{category}**", value=field_value, inline=False)

    await ctx.send(embed=embed)


@bot.command()
async def avatar(ctx, member: discord.Member = None):
    """Mostra o avatar de um usuário."""
    user = member or ctx.author
    embed = discord.Embed(title=f"Avatar de {user.display_name}", color=user.color)
    embed.set_image(url=user.avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def userinfo(ctx, member: discord.Member = None):
    """Exibe informações de um usuário."""
    user = member or ctx.author
    embed = discord.Embed(title=f"Informações de: {user}", color=discord.Color.green())
    embed.set_thumbnail(url=user.avatar.url)
    embed.add_field(name='ID', value=user.id, inline=True)
    embed.add_field(name='Conta criada em', value=user.created_at.strftime('%d/%m/%Y às %H:%M'), inline=True)
    embed.add_field(name='Entrou no servidor em', value=user.joined_at.strftime('%d/%m/%Y às %H:%M'), inline=True)
    roles = [role.mention for role in user.roles[1:]] # Ignora o @everyone
    embed.add_field(name=f"Cargos ({len(roles)})", value=" ".join(roles) if roles else "Nenhum cargo", inline=False)
    await ctx.send(embed=embed)

# ===================================
#             MODERAÇÃO
# ===================================
@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason: str = "Motivo não especificado."):
    """Expulsa um usuário do servidor."""
    await member.kick(reason=reason)
    await ctx.send(f'👢 {member.mention} foi expulso. Motivo: {reason}')

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason: str = "Motivo não especificado."):
    """Bane um usuário do servidor."""
    await member.ban(reason=reason)
    await ctx.send(f'🔨 {member.mention} foi banido. Motivo: {reason}')

@bot.command()
@commands.has_permissions(manage_roles=True)
async def mute(ctx, member: discord.Member, *, reason: str = "Motivo não especificado."):
    """Silencia um usuário (adiciona o cargo 'Muted')."""
    role = discord.utils.get(ctx.guild.roles, name='Muted')
    # Se o cargo 'Muted' não existir, cria e configura ele.
    if not role:
        try:
            role = await ctx.guild.create_role(name='Muted', reason="Cargo para mutar usuários")
            # Configura permissões do cargo em cada canal (de forma mais otimizada)
            for channel in ctx.guild.channels:
                await channel.set_permissions(role, send_messages=False, speak=False)
            await ctx.send("Cargo `Muted` não encontrado. Criei e configurei um novo.")
        except discord.Forbidden:
            return await ctx.send("Não tenho permissão para criar cargos.")

    await member.add_roles(role, reason=reason)
    await ctx.send(f'🔇 {member.mention} foi mutado. Motivo: {reason}')

@bot.command()
@commands.has_permissions(manage_roles=True)
async def unmute(ctx, member: discord.Member):
    """Remove o silêncio de um usuário."""
    role = discord.utils.get(ctx.guild.roles, name='Muted')
    if role and role in member.roles:
        await member.remove_roles(role)
        await ctx.send(f'🔊 {member.mention} foi desmutado.')
    else:
        await ctx.send(f'{member.mention} não está mutado.')

@bot.command()
@commands.has_permissions(manage_guild=True)
async def warn(ctx, member: discord.Member, *, reason: str = "Motivo não especificado."):
    """Dá um aviso a um usuário."""
    await ctx.send(f'⚠️ {member.mention} recebeu um aviso. Motivo: {reason}')
    try:
        await member.send(f'Você foi avisado em **{ctx.guild.name}**. Motivo: {reason}')
    except discord.Forbidden:
        await ctx.send(f"Não consegui enviar a DM para {member.mention}, mas o aviso foi registrado.")

# ===================================
#           MÚSICA / ÁUDIO
# ===================================
@bot.command()
async def play(ctx, *, url: str):
    """Toca uma música do YouTube ou adiciona à fila se já estiver tocando."""
    if not ctx.author.voice:
        return await ctx.send('Você precisa estar em um canal de voz para usar este comando!')

    vc = ctx.voice_client
    if not vc:
        vc = await ctx.author.voice.channel.connect()

    guild_id = ctx.guild.id

    # Se já estiver tocando algo, adiciona na fila
    if vc.is_playing() or vc.is_paused():
        if guild_id not in music_queues:
            music_queues[guild_id] = []
        music_queues[guild_id].append(url)
        # Pega o título sem precisar baixar tudo
        try:
            info = ytdl.extract_info(url, download=False)
            title = info.get('title', 'uma música')
            await ctx.send(f'✅ Adicionado à fila: **{title}**')
        except Exception as e:
            print(e)
            await ctx.send(f'✅ Adicionado à fila: `{url}`')
    else:
        # Se não estiver tocando, começa a tocar imediatamente
        async with ctx.typing():
            await play_music(ctx, url)

@bot.command()
async def queue(ctx):
    """Mostra a fila de músicas."""
    guild_id = ctx.guild.id
    if guild_id in music_queues and music_queues[guild_id]:
        embed = discord.Embed(title="🎵 Fila de Músicas", color=discord.Color.blue())
        # Mostra as próximas 10 músicas
        for i, url in enumerate(music_queues[guild_id][:10]):
            try:
                info = ytdl.extract_info(url, download=False)
                title = info.get('title', url)
                embed.add_field(name=f"{i+1}. {title}", value=f"Pedido por: `quem pediu`", inline=False) #_TODO: Adicionar quem pediu
            except:
                embed.add_field(name=f"{i+1}. Música indisponível", value=url, inline=False)
        await ctx.send(embed=embed)
    else:
        await ctx.send("A fila de músicas está vazia.")


@bot.command()
async def pause(ctx):
    """Pausa a música atual."""
    vc = ctx.voice_client
    if vc and vc.is_playing():
        vc.pause()
        await ctx.send('⏸️ Música pausada.')
    else:
        await ctx.send('Não há música tocando para pausar.')

@bot.command()
async def resume(ctx):
    """Retoma a música pausada."""
    vc = ctx.voice_client
    if vc and vc.is_paused():
        vc.resume()
        await ctx.send('▶️ Música retomada.')
    else:
        await ctx.send('Não há música pausada para retomar.')

@bot.command()
async def stop(ctx):
    """Para a música e desconecta o bot."""
    vc = ctx.voice_client
    if vc:
        # Limpa a fila ao parar
        if ctx.guild.id in music_queues:
            music_queues[ctx.guild.id].clear()
        await vc.disconnect()
        await ctx.send('⏹️ Música parada e bot desconectado.')

@bot.command()
async def skip(ctx):
    """Pula para a próxima música na fila."""
    vc = ctx.voice_client
    if vc and (vc.is_playing() or vc.is_paused()):
        vc.stop() # A função 'after' cuidará de chamar play_next
        await ctx.send('⏭️ Música pulada!')
    else:
        await ctx.send('Não há música tocando para pular.')

@bot.command()
async def volume(ctx, vol: int):
    """Ajusta o volume (0 a 100)."""
    vc = ctx.voice_client
    if not vc or not vc.source:
        return await ctx.send('Não estou tocando nada no momento.')
    if not 0 <= vol <= 100:
        return await ctx.send('O volume deve ser um número entre 0 e 100.')

    vc.source.volume = vol / 100
    await ctx.send(f'🔊 Volume ajustado para **{vol}%**')

# ===================================
#             DIVERSÃO
# ===================================
@bot.command()
async def meme(ctx):
    """Busca um meme aleatório da internet."""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get('https://meme-api.com/gimme') as r:
                if r.status == 200:
                    data = await r.json()
                    embed = discord.Embed(title=data['title'], url=data['postLink'], color=discord.Color.random())
                    embed.set_image(url=data['url'])
                    await ctx.send(embed=embed)
                else:
                    await ctx.send("Não consegui buscar um meme. Tente novamente.")
        except Exception as e:
            await ctx.send("Ocorreu um erro com a API de memes.")
            print(e)


@bot.command()
async def joke(ctx):
    """Conta uma piada aleatória (em inglês)."""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get('https://official-joke-api.appspot.com/random_joke') as r:
                if r.status == 200:
                    data = await r.json()
                    await ctx.send(f"{data['setup']}\n||{data['punchline']}||")
                else:
                    await ctx.send("Não consegui buscar uma piada. Tente novamente.")
        except Exception as e:
            await ctx.send("Ocorreu um erro com a API de piadas.")
            print(e)


@bot.command()
async def coinflip(ctx):
    """Joga uma moeda (cara ou coroa)."""
    result = random.choice(['Cara', 'Coroa'])
    await ctx.send(f'🪙 A moeda caiu em: **{result}**!')

@bot.command()
async def rps(ctx, choice: str):
    """Jogue Pedra, Papel ou Tesoura."""
    choices = ['pedra', 'papel', 'tesoura']
    user_choice = choice.lower()

    if user_choice not in choices:
        return await ctx.send('Escolha inválida! Use: `pedra`, `papel` ou `tesoura`.')

    bot_choice = random.choice(choices)

    wins = {'pedra': 'tesoura', 'tesoura': 'papel', 'papel': 'pedra'}

    if user_choice == bot_choice:
        outcome = f"Eu também escolhi `{bot_choice}`. Empatamos! 🤝"
    elif wins[user_choice] == bot_choice:
        outcome = f"Eu escolhi `{bot_choice}`. Você ganhou, DROGA!! 🤬🎉"
    else:
        outcome = f"Eu escolhi `{bot_choice}`. Eu ganhei! HAHAHAH 🤖"

    await ctx.send(outcome)

# ===================================
#           EXECUÇÃO DO BOT
# ===================================
# Obtenha o token do arquivo .env
BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
if BOT_TOKEN is None:
    print("Erro: A variável de ambiente 'DISCORD_BOT_TOKEN' não está definida.")
    print("Certifique-se de criar um arquivo '.env' na mesma pasta do script com o conteúdo: DISCORD_BOT_TOKEN=SEU_TOKEN_AQUI")
else:
    bot.run(BOT_TOKEN)
