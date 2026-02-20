import discord
from discord.ext import commands
from key import token


intents = discord.Intents.default()
intents.typing = False
intents.presences = True
intents.members = True
intents.message_content = True
client = discord.Client(intents=discord.Intents.default())
TOKEN = token.get('TOKEN')


@client.event
async def on_ready():
        print(f"STATUS: {client.user} ATIVADO!!!")


@client.event
async def on_message(message):

    conteudo = message.content
    l_conteudo = conteudo.lower()

    if message.author == client.user:
        return

    if l_conteudo.startswith('oi'):
        await message.channel.send(f'Oi {message.author}, tudo bem?')                      

@bot.command()
async def joined(ctx, member: discord.Member):
    await ctx.send(f'{member.name} joined {discord.utils.format_dt(member.joined_at)}')


client.run(TOKEN)


