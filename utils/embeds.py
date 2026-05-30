"""
╔══════════════════════════════════════════════════╗
║      XW-2077 • Helpers para Embeds Temáticos    ║
╚══════════════════════════════════════════════════╝

Funções auxiliares para criar embeds padronizados
com o tema cyberpunk do XW-2077. Todos os cogs
devem usar essas funções para manter consistência.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import discord

from config import Config


def create_embed(
    title: str,
    description: str,
    color: int,
    *,
    thumbnail_url: Optional[str] = None,
    image_url: Optional[str] = None,
    footer_text: str = Config.EMBED_FOOTER,
    timestamp: bool = True,
    author_name: Optional[str] = None,
    author_icon_url: Optional[str] = None,
) -> discord.Embed:
    """Cria um embed base com o tema cyberpunk do XW-2077.

    Parameters
    ----------
    title : str
        Título do embed.
    description : str
        Descrição / corpo do embed.
    color : int
        Cor em formato hex int (ex: ``0x00FFFF``).
    thumbnail_url : str, optional
        URL da thumbnail.
    image_url : str, optional
        URL da imagem principal.
    footer_text : str
        Texto do footer (padrão: ``Config.EMBED_FOOTER``).
    timestamp : bool
        Se ``True``, adiciona timestamp UTC atual.
    author_name : str, optional
        Nome do autor no embed.
    author_icon_url : str, optional
        URL do ícone do autor.

    Returns
    -------
    discord.Embed
        Embed configurado e pronto para enviar.
    """
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
    )

    if timestamp:
        embed.timestamp = datetime.now(timezone.utc)

    if footer_text:
        embed.set_footer(text=footer_text)

    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)

    if image_url:
        embed.set_image(url=image_url)

    if author_name:
        embed.set_author(name=author_name, icon_url=author_icon_url or "")

    return embed


def success_embed(title: str, description: str) -> discord.Embed:
    """Cria um embed de **sucesso** (verde neon + ✅).

    Parameters
    ----------
    title : str
        Título da mensagem de sucesso.
    description : str
        Detalhes do sucesso.

    Returns
    -------
    discord.Embed
    """
    return create_embed(
        title=f"{Config.Emojis.CHECK} {title}",
        description=description,
        color=Config.Colors.SUCCESS,
    )


def error_embed(title: str, description: str) -> discord.Embed:
    """Cria um embed de **erro** (vermelho + ❌).

    Parameters
    ----------
    title : str
        Título do erro.
    description : str
        Detalhes do erro.

    Returns
    -------
    discord.Embed
    """
    return create_embed(
        title=f"{Config.Emojis.CROSS} {title}",
        description=description,
        color=Config.Colors.ERROR,
    )


def music_embed(
    title: str,
    description: str,
    *,
    thumbnail_url: Optional[str] = None,
) -> discord.Embed:
    """Cria um embed de **música** (cyan neon + 🎵).

    Parameters
    ----------
    title : str
        Título (ex: nome da música).
    description : str
        Detalhes da música / player.
    thumbnail_url : str, optional
        Thumbnail da música (capa do álbum, etc.).

    Returns
    -------
    discord.Embed
    """
    return create_embed(
        title=f"{Config.Emojis.MUSIC} {title}",
        description=description,
        color=Config.Colors.MUSIC,
        thumbnail_url=thumbnail_url,
    )


def info_embed(title: str, description: str) -> discord.Embed:
    """Cria um embed de **informação** (roxo + ℹ️).

    Parameters
    ----------
    title : str
        Título informativo.
    description : str
        Conteúdo informativo.

    Returns
    -------
    discord.Embed
    """
    return create_embed(
        title=f"{Config.Emojis.INFO} {title}",
        description=description,
        color=Config.Colors.INFO,
    )


def warning_embed(title: str, description: str) -> discord.Embed:
    """Cria um embed de **aviso** (laranja + ⚠️).

    Parameters
    ----------
    title : str
        Título do aviso.
    description : str
        Detalhes do aviso.

    Returns
    -------
    discord.Embed
    """
    return create_embed(
        title=f"{Config.Emojis.WARNING} {title}",
        description=description,
        color=Config.Colors.WARNING,
    )


def moderation_embed(title: str, description: str) -> discord.Embed:
    """Cria um embed de **moderação** (vermelho).

    Parameters
    ----------
    title : str
        Título da ação de moderação.
    description : str
        Detalhes da ação.

    Returns
    -------
    discord.Embed
    """
    return create_embed(
        title=title,
        description=description,
        color=Config.Colors.MODERATION,
    )


def leveling_embed(title: str, description: str) -> discord.Embed:
    """Cria um embed de **level up / XP** (verde neon + 🎉).

    Parameters
    ----------
    title : str
        Título (ex: "Level Up!").
    description : str
        Detalhes do progresso.

    Returns
    -------
    discord.Embed
    """
    return create_embed(
        title=f"{Config.Emojis.LEVEL_UP} {title}",
        description=description,
        color=Config.Colors.LEVELING,
    )
