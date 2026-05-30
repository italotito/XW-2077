"""
╔══════════════════════════════════════════════════╗
║        XW-2077 • Music Cog (Wavelink 3.x)       ║
║     Sistema de Música Completo • Lavalink v4     ║
╚══════════════════════════════════════════════════╝

Player de música interativo com controles via botões,
fila paginada, modos de loop, barra de progresso e
auto-desconexão por inatividade.

Requer: wavelink>=3.0.0, discord.py>=2.0
"""

from __future__ import annotations

import asyncio
import logging
import math
from datetime import datetime, timezone
from typing import Optional, cast

import discord
import wavelink
from discord import app_commands
from discord.ext import commands

from config import Config
from utils.embeds import create_embed, error_embed, music_embed, success_embed

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════
#  Utilitários
# ═══════════════════════════════════════════════════════

def format_duration(ms: int) -> str:
    """Converte milissegundos em formato legível (MM:SS ou HH:MM:SS)."""
    if ms <= 0:
        return "0:00"
    seconds = ms // 1000
    minutes, secs = divmod(seconds, 60)
    hours, mins = divmod(minutes, 60)
    if hours > 0:
        return f"{hours}:{mins:02d}:{secs:02d}"
    return f"{mins}:{secs:02d}"


def build_progress_bar(position_ms: int, length_ms: int, bar_length: int = 12) -> str:
    """Cria barra de progresso visual para o player.

    Exemplo: ``▬▬▬🔘▬▬▬▬▬▬▬▬ 2:30 / 5:00``
    """
    if length_ms <= 0:
        return f"🔘{'▬' * (bar_length - 1)} {format_duration(position_ms)} / 🔴 LIVE"

    ratio = min(position_ms / length_ms, 1.0)
    filled = int(ratio * bar_length)
    bar = "▬" * filled + "🔘" + "▬" * (bar_length - filled - 1)
    return f"{bar} {format_duration(position_ms)} / {format_duration(length_ms)}"


def build_volume_bar(volume: int) -> str:
    """Cria barra visual de volume.

    Exemplo: ``🔊 ████████░░ 80%``
    """
    bar_length = 10
    filled = round(volume / 100 * bar_length)
    bar = "█" * filled + "░" * (bar_length - filled)
    emoji = "🔇" if volume == 0 else "🔉" if volume < 50 else "🔊"
    return f"{emoji} {bar} {volume}%"


def get_loop_mode_label(mode: wavelink.QueueMode) -> str:
    """Retorna o label em português do modo de loop."""
    labels = {
        wavelink.QueueMode.normal: "Desligado",
        wavelink.QueueMode.loop: "🔂 Repetir Música",
        wavelink.QueueMode.loop_all: "🔁 Repetir Fila",
    }
    return labels.get(mode, "Desligado")


# ═══════════════════════════════════════════════════════
#  Views Interativas
# ═══════════════════════════════════════════════════════

class LoopSelectMenu(discord.ui.Select):
    """Menu dropdown para selecionar o modo de loop."""

    def __init__(self) -> None:
        options = [
            discord.SelectOption(
                label="Desligado",
                description="A fila toca normalmente",
                emoji="▶️",
                value="normal",
            ),
            discord.SelectOption(
                label="Repetir Música",
                description="Repete a música atual infinitamente",
                emoji="🔂",
                value="loop",
            ),
            discord.SelectOption(
                label="Repetir Fila",
                description="Repete toda a fila ao terminar",
                emoji="🔁",
                value="loop_all",
            ),
        ]
        super().__init__(
            placeholder="🔁 Escolha o modo de repetição...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        player: wavelink.Player | None = cast(
            wavelink.Player, interaction.guild.voice_client  # type: ignore[union-attr]
        )
        if not player:
            await interaction.response.send_message(
                embed=error_embed("Erro", "Não estou conectado a nenhum canal de voz."),
                ephemeral=True,
            )
            return

        mode_map = {
            "normal": wavelink.QueueMode.normal,
            "loop": wavelink.QueueMode.loop,
            "loop_all": wavelink.QueueMode.loop_all,
        }
        selected = self.values[0]
        mode = mode_map.get(selected, wavelink.QueueMode.normal)
        player.queue.mode = mode

        await interaction.response.send_message(
            embed=success_embed(
                "Modo de Repetição",
                f"Modo alterado para: **{get_loop_mode_label(mode)}**",
            ),
            ephemeral=True,
        )


class LoopSelectView(discord.ui.View):
    """View container para o menu de loop."""

    def __init__(self) -> None:
        super().__init__(timeout=60)
        self.add_item(LoopSelectMenu())


class QueueView(discord.ui.View):
    """View paginada para a fila de músicas."""

    def __init__(
        self,
        queue: wavelink.Queue,
        *,
        author_id: int,
        current_track: Optional[wavelink.Playable] = None,
    ) -> None:
        super().__init__(timeout=120)
        self.queue = queue
        self.author_id = author_id
        self.current_track = current_track
        self.page = 0
        self.per_page = 10

    @property
    def total_pages(self) -> int:
        count = len(self.queue)
        if count == 0:
            return 1
        return math.ceil(count / self.per_page)

    def build_embed(self) -> discord.Embed:
        """Constrói o embed da página atual da fila."""
        tracks = list(self.queue)
        total = len(tracks)

        desc_lines: list[str] = []

        # Tocando agora
        if self.current_track:
            desc_lines.append(
                f"**🎵 Tocando agora:**\n"
                f"[{self.current_track.title}]({self.current_track.uri}) — "
                f"`{format_duration(self.current_track.length)}`\n"
            )

        if total == 0:
            desc_lines.append("*A fila está vazia.*")
        else:
            start = self.page * self.per_page
            end = min(start + self.per_page, total)
            page_tracks = tracks[start:end]

            desc_lines.append("**📋 Próximas músicas:**\n")
            for i, track in enumerate(page_tracks, start=start + 1):
                duration = format_duration(track.length)
                desc_lines.append(
                    f"`{i}.` [{track.title}]({track.uri}) — `{duration}`"
                )

            # Duração total
            total_ms = sum(t.length for t in tracks)
            desc_lines.append(
                f"\n**{total}** música(s) na fila • "
                f"Duração total: `{format_duration(total_ms)}`"
            )

        embed = create_embed(
            title=f"{Config.Emojis.QUEUE} Fila de Músicas",
            description="\n".join(desc_lines),
            color=Config.Colors.MUSIC,
        )
        embed.set_footer(
            text=f"Página {self.page + 1}/{self.total_pages} • {Config.EMBED_FOOTER}"
        )
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "Apenas quem pediu a fila pode usar esses botões.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="⬅️ Anterior", style=discord.ButtonStyle.secondary)
    async def prev_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if self.page > 0:
            self.page -= 1
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="➡️ Próxima", style=discord.ButtonStyle.secondary)
    async def next_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if self.page < self.total_pages - 1:
            self.page += 1
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="🗑️ Limpar Fila", style=discord.ButtonStyle.danger)
    async def clear_queue(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.queue.clear()
        self.page = 0
        await interaction.response.edit_message(
            embed=success_embed("Fila Limpa", "Todas as músicas foram removidas da fila."),
            view=None,
        )
        self.stop()


class MusicPlayerView(discord.ui.View):
    """Controles interativos do player de música (persistente)."""

    def __init__(self, cog: Music) -> None:
        super().__init__(timeout=None)
        self.cog = cog

    def _get_player(self, interaction: discord.Interaction) -> Optional[wavelink.Player]:
        """Obtém o player atual do guild."""
        if interaction.guild:
            return cast(
                wavelink.Player, interaction.guild.voice_client
            )
        return None

    async def _check_voice(
        self, interaction: discord.Interaction
    ) -> Optional[wavelink.Player]:
        """Verifica se o player está ativo e retorna, ou envia erro."""
        player = self._get_player(interaction)
        if not player:
            await interaction.response.send_message(
                embed=error_embed("Erro", "Não estou tocando nada no momento."),
                ephemeral=True,
            )
            return None
        return player

    # ── Row 1 ─────────────────────────────────────────

    @discord.ui.button(
        emoji="⏮️", style=discord.ButtonStyle.secondary, custom_id="music:previous", row=0
    )
    async def btn_previous(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        player = await self._check_voice(interaction)
        if not player:
            return

        if player.queue.history and len(player.queue.history) > 0:
            try:
                prev_track = player.queue.history[-1]
                await player.play(prev_track)
                await interaction.response.send_message(
                    embed=music_embed(
                        "Música Anterior",
                        f"Voltando para: **{prev_track.title}**",
                    ),
                    ephemeral=True,
                )
            except Exception:
                await interaction.response.send_message(
                    embed=error_embed("Erro", "Não há música anterior no histórico."),
                    ephemeral=True,
                )
        else:
            # Sem histórico, faz seek pro início
            await player.seek(0)
            await interaction.response.send_message(
                embed=music_embed("Recomeçando", "Voltando ao início da música."),
                ephemeral=True,
            )

    @discord.ui.button(
        emoji="⏯️", style=discord.ButtonStyle.primary, custom_id="music:playpause", row=0
    )
    async def btn_playpause(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        player = await self._check_voice(interaction)
        if not player:
            return

        await player.pause(not player.paused)
        state = "pausada" if player.paused else "retomada"
        emoji = Config.Emojis.PAUSE if player.paused else Config.Emojis.PLAY
        await interaction.response.send_message(
            embed=music_embed("Player", f"{emoji} Música **{state}**."),
            ephemeral=True,
        )

    @discord.ui.button(
        emoji="⏭️", style=discord.ButtonStyle.secondary, custom_id="music:skip", row=0
    )
    async def btn_skip(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        player = await self._check_voice(interaction)
        if not player:
            return

        current = player.current
        await player.skip(force=True)
        title = current.title if current else "Desconhecida"
        await interaction.response.send_message(
            embed=music_embed("Pulada", f"⏭️ **{title}** foi pulada."),
            ephemeral=True,
        )

    @discord.ui.button(
        emoji="🔀", style=discord.ButtonStyle.secondary, custom_id="music:shuffle", row=0
    )
    async def btn_shuffle(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        player = await self._check_voice(interaction)
        if not player:
            return

        if len(player.queue) < 2:
            await interaction.response.send_message(
                embed=error_embed("Erro", "A fila precisa ter pelo menos 2 músicas para embaralhar."),
                ephemeral=True,
            )
            return

        player.queue.shuffle()
        await interaction.response.send_message(
            embed=success_embed("Fila Embaralhada", f"🔀 **{len(player.queue)}** músicas embaralhadas!"),
            ephemeral=True,
        )

    @discord.ui.button(
        emoji="🔁", style=discord.ButtonStyle.secondary, custom_id="music:loop", row=0
    )
    async def btn_loop(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        player = await self._check_voice(interaction)
        if not player:
            return

        # Cicla entre os modos: normal → loop → loop_all → normal
        mode_cycle = {
            wavelink.QueueMode.normal: wavelink.QueueMode.loop,
            wavelink.QueueMode.loop: wavelink.QueueMode.loop_all,
            wavelink.QueueMode.loop_all: wavelink.QueueMode.normal,
        }
        new_mode = mode_cycle.get(player.queue.mode, wavelink.QueueMode.normal)
        player.queue.mode = new_mode

        await interaction.response.send_message(
            embed=music_embed(
                "Modo de Repetição",
                f"Agora: **{get_loop_mode_label(new_mode)}**",
            ),
            ephemeral=True,
        )

    # ── Row 2 ─────────────────────────────────────────

    @discord.ui.button(
        emoji="🔉", label="-10", style=discord.ButtonStyle.secondary, custom_id="music:voldown", row=1
    )
    async def btn_vol_down(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        player = await self._check_voice(interaction)
        if not player:
            return

        new_vol = max(0, player.volume - 10)
        await player.set_volume(new_vol)
        await interaction.response.send_message(
            embed=music_embed("Volume", build_volume_bar(new_vol)),
            ephemeral=True,
        )

    @discord.ui.button(
        emoji="🔊", label="+10", style=discord.ButtonStyle.secondary, custom_id="music:volup", row=1
    )
    async def btn_vol_up(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        player = await self._check_voice(interaction)
        if not player:
            return

        new_vol = min(100, player.volume + 10)
        await player.set_volume(new_vol)
        await interaction.response.send_message(
            embed=music_embed("Volume", build_volume_bar(new_vol)),
            ephemeral=True,
        )

    @discord.ui.button(
        emoji="⏹️", style=discord.ButtonStyle.danger, custom_id="music:stop", row=1
    )
    async def btn_stop(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        player = await self._check_voice(interaction)
        if not player:
            return

        player.queue.clear()
        await player.disconnect()
        await interaction.response.send_message(
            embed=music_embed("Desconectado", "⏹️ Player parado e fila limpa."),
            ephemeral=True,
        )

    @discord.ui.button(
        emoji="📋", label="Fila", style=discord.ButtonStyle.secondary, custom_id="music:queue", row=1
    )
    async def btn_queue(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        player = await self._check_voice(interaction)
        if not player:
            return

        view = QueueView(
            player.queue,
            author_id=interaction.user.id,
            current_track=player.current,
        )
        await interaction.response.send_message(
            embed=view.build_embed(), view=view, ephemeral=True
        )


# ═══════════════════════════════════════════════════════
#  Cog Principal
# ═══════════════════════════════════════════════════════

class Music(commands.Cog):
    """🎵 Sistema de música do XW-2077 — powered by Wavelink & Lavalink."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.player_view = MusicPlayerView(self)
        # Registra a view persistente
        self.bot.add_view(self.player_view)

    async def cog_load(self) -> None:
        """Conecta aos nodes do Lavalink ao carregar o cog."""
        nodes = [
            wavelink.Node(
                uri=Config.LAVALINK_URI,
                password=Config.LAVALINK_PASSWORD,
            )
        ]
        await wavelink.Pool.connect(
            nodes=nodes,
            client=self.bot,
            cache_capacity=100,
        )
        logger.info("[Music] Conectando aos nodes do Lavalink...")

    async def cog_unload(self) -> None:
        """Desconecta todos os players ao descarregar o cog."""
        for guild in self.bot.guilds:
            if guild.voice_client:
                player = cast(wavelink.Player, guild.voice_client)
                player.queue.clear()
                await player.disconnect()
        logger.info("[Music] Cog descarregado — todos os players desconectados.")

    # ── Helpers ──────────────────────────────────────

    @staticmethod
    async def _ensure_voice(
        interaction: discord.Interaction,
    ) -> Optional[wavelink.Player]:
        """Garante que o usuário está em um canal de voz e conecta o bot se necessário.

        Returns
        -------
        wavelink.Player | None
            O player conectado, ou None se não foi possível conectar.
        """
        if not interaction.guild:
            await interaction.response.send_message(
                embed=error_embed("Erro", "Este comando só funciona em servidores."),
                ephemeral=True,
            )
            return None

        member = interaction.guild.get_member(interaction.user.id)
        if not member or not member.voice or not member.voice.channel:
            await interaction.response.send_message(
                embed=error_embed(
                    "Erro",
                    "Você precisa estar em um canal de voz para usar este comando.",
                ),
                ephemeral=True,
            )
            return None

        player = cast(wavelink.Player, interaction.guild.voice_client)

        if not player:
            try:
                player = await member.voice.channel.connect(
                    cls=wavelink.Player,  # type: ignore[arg-type]
                    self_deaf=True,
                )
                player.inactive_timeout = 180  # 3 minutos
            except Exception as e:
                logger.error(f"[Music] Erro ao conectar: {e}")
                await interaction.response.send_message(
                    embed=error_embed(
                        "Erro de Conexão",
                        "Não consegui me conectar ao canal de voz. Verifique minhas permissões.",
                    ),
                    ephemeral=True,
                )
                return None
        else:
            # Verifica se o usuário está no mesmo canal
            if member.voice.channel.id != player.channel.id:
                await interaction.response.send_message(
                    embed=error_embed(
                        "Erro",
                        f"Você precisa estar no canal {player.channel.mention} para usar comandos de música.",
                    ),
                    ephemeral=True,
                )
                return None

        return player

    def _build_now_playing_embed(
        self,
        track: wavelink.Playable,
        player: wavelink.Player,
        *,
        requester: Optional[discord.User | discord.Member] = None,
    ) -> discord.Embed:
        """Constrói o embed de 'Tocando Agora' com todas as informações."""
        progress = build_progress_bar(player.position, track.length)

        description_lines = [
            f"**{track.author}**\n",
            f"```{progress}```",
        ]

        embed = create_embed(
            title=f"{Config.Emojis.MUSIC} {track.title}",
            description="\n".join(description_lines),
            color=Config.Colors.MUSIC,
            thumbnail_url=getattr(track, "artwork", None),
        )

        embed.add_field(
            name="⏱️ Duração",
            value=f"`{format_duration(track.length)}`",
            inline=True,
        )
        embed.add_field(
            name="🔊 Volume",
            value=f"`{player.volume}%`",
            inline=True,
        )
        embed.add_field(
            name="🔁 Loop",
            value=f"`{get_loop_mode_label(player.queue.mode)}`",
            inline=True,
        )
        embed.add_field(
            name="📋 Na Fila",
            value=f"`{len(player.queue)}` música(s)",
            inline=True,
        )

        if track.uri:
            embed.add_field(
                name="🔗 Link",
                value=f"[Abrir]({track.uri})",
                inline=True,
            )

        footer_parts = [Config.EMBED_FOOTER]
        if requester:
            footer_parts.insert(0, f"Pedido por {requester.display_name}")
        embed.set_footer(text=" • ".join(footer_parts))

        return embed

    # ── Eventos Wavelink ─────────────────────────────

    @commands.Cog.listener()
    async def on_wavelink_node_ready(
        self, payload: wavelink.NodeReadyEventPayload
    ) -> None:
        """Dispara quando um node do Lavalink se conecta."""
        logger.info(
            f"[Music] Node Lavalink conectado: {payload.node.identifier} "
            f"| Resumido: {payload.resumed} | ID Sessão: {payload.session_id}"
        )

    @commands.Cog.listener()
    async def on_wavelink_track_start(
        self, payload: wavelink.TrackStartEventPayload
    ) -> None:
        """Dispara quando uma música começa a tocar — envia embed com controles."""
        player = payload.player
        track = payload.track

        if not player or not player.guild:
            return

        # Obtém o canal de texto para enviar o embed
        channel = getattr(player, "text_channel", None)
        if not channel:
            return

        requester = getattr(track, "requester", None)

        embed = self._build_now_playing_embed(
            track, player, requester=requester
        )

        try:
            # Deleta a mensagem do player anterior (se houver)
            old_msg = getattr(player, "_now_playing_msg", None)
            if old_msg:
                try:
                    await old_msg.delete()
                except (discord.NotFound, discord.HTTPException):
                    pass

            msg = await channel.send(embed=embed, view=self.player_view)
            player._now_playing_msg = msg  # type: ignore[attr-defined]
        except (discord.HTTPException, discord.Forbidden) as e:
            logger.warning(f"[Music] Não foi possível enviar Now Playing: {e}")

    @commands.Cog.listener()
    async def on_wavelink_track_end(
        self, payload: wavelink.TrackEndEventPayload
    ) -> None:
        """Dispara quando uma música termina."""
        player = payload.player
        if not player:
            return

        # Wavelink 3.x com autoplay desativado: avança a fila manualmente
        # Se autoplay está habilitado, o player cuida disso sozinho
        # Mantemos este listener para limpeza e logging
        logger.debug(
            f"[Music] Track finalizada: {payload.track.title} "
            f"| Reason: {payload.reason}"
        )

    @commands.Cog.listener()
    async def on_wavelink_inactive_player(
        self, player: wavelink.Player
    ) -> None:
        """Dispara quando o player fica inativo — auto-desconecta."""
        logger.info(
            f"[Music] Player inativo em {player.guild.name if player.guild else '???'} "
            f"— desconectando..."
        )

        channel = getattr(player, "text_channel", None)
        if channel:
            try:
                await channel.send(
                    embed=music_embed(
                        "Desconectado",
                        "⏹️ Desconectei por inatividade. Use `/play` para começar de novo!",
                    )
                )
            except (discord.HTTPException, discord.Forbidden):
                pass

        await player.disconnect()

    # ── Slash Commands ───────────────────────────────

    @app_commands.command(name="play", description="🎵 Toca uma música ou adiciona à fila")
    @app_commands.describe(query="Nome da música ou URL (YouTube, Spotify, SoundCloud)")
    @app_commands.checks.cooldown(1, 3.0, key=lambda i: (i.guild_id, i.user.id))
    async def play_cmd(self, interaction: discord.Interaction, query: str) -> None:
        """Busca e toca uma música, ou adiciona à fila se já estiver tocando."""
        player = await self._ensure_voice(interaction)
        if not player:
            return

        # Salva o canal de texto para enviar embeds de now playing
        player.text_channel = interaction.channel  # type: ignore[attr-defined]

        await interaction.response.defer()

        try:
            tracks: wavelink.Search = await wavelink.Playable.search(query)
        except wavelink.LavalinkLoadException as e:
            await interaction.followup.send(
                embed=error_embed("Erro de Busca", f"Não foi possível buscar: `{e.error}`")
            )
            return
        except Exception as e:
            logger.error(f"[Music] Erro na busca: {e}")
            await interaction.followup.send(
                embed=error_embed("Erro", "Ocorreu um erro ao buscar a música.")
            )
            return

        if not tracks:
            await interaction.followup.send(
                embed=error_embed(
                    "Nada Encontrado",
                    f"Não encontrei resultados para: **{query}**",
                )
            )
            return

        # Se é uma playlist, adiciona todas
        if isinstance(tracks, wavelink.Playlist):
            playlist_name = tracks.name or "Playlist"
            added = 0
            for track in tracks.tracks:
                track.requester = interaction.user  # type: ignore[attr-defined]
                await player.queue.put_wait(track)
                added += 1

            embed = success_embed(
                "Playlist Adicionada",
                f"📋 **{playlist_name}**\n"
                f"Adicionadas **{added}** músicas à fila.",
            )
            if tracks.tracks and hasattr(tracks.tracks[0], "artwork"):
                embed.set_thumbnail(url=tracks.tracks[0].artwork)

            if not player.playing:
                next_track = player.queue.get()
                await player.play(next_track)

            await interaction.followup.send(embed=embed)
            return

        # Pega a primeira track
        track = tracks[0]
        track.requester = interaction.user  # type: ignore[attr-defined]

        if player.playing:
            await player.queue.put_wait(track)
            position = len(player.queue)

            embed = music_embed(
                "Adicionada à Fila",
                f"**[{track.title}]({track.uri})**\n"
                f"por **{track.author}**\n\n"
                f"⏱️ Duração: `{format_duration(track.length)}`\n"
                f"📋 Posição na fila: `#{position}`",
                thumbnail_url=getattr(track, "artwork", None),
            )
            embed.set_footer(
                text=f"Pedido por {interaction.user.display_name} • {Config.EMBED_FOOTER}"
            )
            await interaction.followup.send(embed=embed)
        else:
            await player.play(track)

            embed = self._build_now_playing_embed(
                track, player, requester=interaction.user
            )
            msg = await interaction.followup.send(
                embed=embed, view=self.player_view, wait=True
            )
            player._now_playing_msg = msg  # type: ignore[attr-defined]

    @app_commands.command(name="pause", description="⏸️ Pausa ou retoma a música atual")
    async def pause_cmd(self, interaction: discord.Interaction) -> None:
        """Toggle de pause/resume."""
        if not interaction.guild or not interaction.guild.voice_client:
            await interaction.response.send_message(
                embed=error_embed("Erro", "Não estou tocando nada no momento."),
                ephemeral=True,
            )
            return

        player = cast(wavelink.Player, interaction.guild.voice_client)
        await player.pause(not player.paused)

        if player.paused:
            embed = music_embed("Pausado", f"{Config.Emojis.PAUSE} Música pausada.")
        else:
            embed = music_embed("Retomado", f"{Config.Emojis.PLAY} Música retomada!")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="resume", description="▶️ Retoma a música pausada")
    async def resume_cmd(self, interaction: discord.Interaction) -> None:
        """Resume a música caso esteja pausada."""
        if not interaction.guild or not interaction.guild.voice_client:
            await interaction.response.send_message(
                embed=error_embed("Erro", "Não estou tocando nada no momento."),
                ephemeral=True,
            )
            return

        player = cast(wavelink.Player, interaction.guild.voice_client)

        if not player.paused:
            await interaction.response.send_message(
                embed=error_embed("Erro", "A música já está tocando!"),
                ephemeral=True,
            )
            return

        await player.pause(False)
        await interaction.response.send_message(
            embed=music_embed("Retomado", f"{Config.Emojis.PLAY} Música retomada!")
        )

    @app_commands.command(name="skip", description="⏭️ Pula para a próxima música")
    async def skip_cmd(self, interaction: discord.Interaction) -> None:
        """Pula a música atual."""
        if not interaction.guild or not interaction.guild.voice_client:
            await interaction.response.send_message(
                embed=error_embed("Erro", "Não estou tocando nada no momento."),
                ephemeral=True,
            )
            return

        player = cast(wavelink.Player, interaction.guild.voice_client)
        current = player.current

        if not current:
            await interaction.response.send_message(
                embed=error_embed("Erro", "Não há música tocando para pular."),
                ephemeral=True,
            )
            return

        await player.skip(force=True)
        await interaction.response.send_message(
            embed=music_embed(
                "Pulada",
                f"{Config.Emojis.SKIP} **{current.title}** foi pulada.",
            )
        )

    @app_commands.command(name="stop", description="⏹️ Para a música e desconecta o bot")
    async def stop_cmd(self, interaction: discord.Interaction) -> None:
        """Para o player, limpa a fila e desconecta."""
        if not interaction.guild or not interaction.guild.voice_client:
            await interaction.response.send_message(
                embed=error_embed("Erro", "Não estou conectado a nenhum canal de voz."),
                ephemeral=True,
            )
            return

        player = cast(wavelink.Player, interaction.guild.voice_client)
        player.queue.clear()
        await player.disconnect()

        await interaction.response.send_message(
            embed=music_embed(
                "Desconectado",
                f"{Config.Emojis.STOP} Player parado e fila limpa. Até mais! 👋",
            )
        )

    @app_commands.command(name="queue", description="📋 Mostra a fila de músicas")
    async def queue_cmd(self, interaction: discord.Interaction) -> None:
        """Exibe a fila de músicas com paginação."""
        if not interaction.guild or not interaction.guild.voice_client:
            await interaction.response.send_message(
                embed=error_embed("Erro", "Não estou tocando nada no momento."),
                ephemeral=True,
            )
            return

        player = cast(wavelink.Player, interaction.guild.voice_client)

        view = QueueView(
            player.queue,
            author_id=interaction.user.id,
            current_track=player.current,
        )
        await interaction.response.send_message(embed=view.build_embed(), view=view)

    @app_commands.command(name="volume", description="🔊 Ajusta o volume do player")
    @app_commands.describe(level="Volume de 0 a 100")
    async def volume_cmd(
        self, interaction: discord.Interaction, level: app_commands.Range[int, 0, 100]
    ) -> None:
        """Ajusta o volume do player."""
        if not interaction.guild or not interaction.guild.voice_client:
            await interaction.response.send_message(
                embed=error_embed("Erro", "Não estou tocando nada no momento."),
                ephemeral=True,
            )
            return

        player = cast(wavelink.Player, interaction.guild.voice_client)
        await player.set_volume(level)

        await interaction.response.send_message(
            embed=music_embed("Volume Ajustado", build_volume_bar(level))
        )

    @app_commands.command(name="nowplaying", description="🎵 Mostra a música atual com detalhes")
    async def nowplaying_cmd(self, interaction: discord.Interaction) -> None:
        """Mostra informações detalhadas da música atual com barra de progresso."""
        if not interaction.guild or not interaction.guild.voice_client:
            await interaction.response.send_message(
                embed=error_embed("Erro", "Não estou tocando nada no momento."),
                ephemeral=True,
            )
            return

        player = cast(wavelink.Player, interaction.guild.voice_client)
        current = player.current

        if not current:
            await interaction.response.send_message(
                embed=error_embed("Erro", "Nenhuma música está tocando."),
                ephemeral=True,
            )
            return

        requester = getattr(current, "requester", None)
        embed = self._build_now_playing_embed(
            current, player, requester=requester
        )

        await interaction.response.send_message(
            embed=embed, view=self.player_view
        )

    @app_commands.command(name="shuffle", description="🔀 Embaralha a fila de músicas")
    async def shuffle_cmd(self, interaction: discord.Interaction) -> None:
        """Embaralha aleatoriamente a ordem da fila."""
        if not interaction.guild or not interaction.guild.voice_client:
            await interaction.response.send_message(
                embed=error_embed("Erro", "Não estou tocando nada no momento."),
                ephemeral=True,
            )
            return

        player = cast(wavelink.Player, interaction.guild.voice_client)

        if len(player.queue) < 2:
            await interaction.response.send_message(
                embed=error_embed(
                    "Erro",
                    "A fila precisa ter pelo menos **2 músicas** para embaralhar.",
                ),
                ephemeral=True,
            )
            return

        player.queue.shuffle()
        await interaction.response.send_message(
            embed=success_embed(
                "Fila Embaralhada",
                f"{Config.Emojis.SHUFFLE} **{len(player.queue)}** músicas foram embaralhadas!",
            )
        )

    @app_commands.command(name="loop", description="🔁 Altera o modo de repetição")
    async def loop_cmd(self, interaction: discord.Interaction) -> None:
        """Abre um menu para escolher o modo de loop."""
        if not interaction.guild or not interaction.guild.voice_client:
            await interaction.response.send_message(
                embed=error_embed("Erro", "Não estou tocando nada no momento."),
                ephemeral=True,
            )
            return

        player = cast(wavelink.Player, interaction.guild.voice_client)
        current_mode = get_loop_mode_label(player.queue.mode)

        view = LoopSelectView()
        await interaction.response.send_message(
            embed=music_embed(
                "Modo de Repetição",
                f"Modo atual: **{current_mode}**\n\nEscolha o novo modo abaixo:",
            ),
            view=view,
        )

    @app_commands.command(name="remove", description="🗑️ Remove uma música da fila pela posição")
    @app_commands.describe(position="Posição da música na fila (começando em 1)")
    async def remove_cmd(
        self, interaction: discord.Interaction, position: int
    ) -> None:
        """Remove uma música específica da fila pela sua posição."""
        if not interaction.guild or not interaction.guild.voice_client:
            await interaction.response.send_message(
                embed=error_embed("Erro", "Não estou tocando nada no momento."),
                ephemeral=True,
            )
            return

        player = cast(wavelink.Player, interaction.guild.voice_client)

        if len(player.queue) == 0:
            await interaction.response.send_message(
                embed=error_embed("Erro", "A fila está vazia."),
                ephemeral=True,
            )
            return

        if position < 1 or position > len(player.queue):
            await interaction.response.send_message(
                embed=error_embed(
                    "Posição Inválida",
                    f"Escolha uma posição entre **1** e **{len(player.queue)}**.",
                ),
                ephemeral=True,
            )
            return

        # Wavelink Queue suporta indexação
        idx = position - 1
        try:
            removed = player.queue.peek(idx)
            del player.queue[idx]
        except (IndexError, KeyError):
            await interaction.response.send_message(
                embed=error_embed("Erro", "Não foi possível remover a música."),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            embed=success_embed(
                "Removida",
                f"🗑️ **{removed.title}** removida da fila (posição #{position}).",
            )
        )

    @app_commands.command(name="seek", description="⏩ Avança ou retrocede na música atual")
    @app_commands.describe(seconds="Posição em segundos para avançar")
    async def seek_cmd(
        self, interaction: discord.Interaction, seconds: int
    ) -> None:
        """Avança para uma posição específica na música (em segundos)."""
        if not interaction.guild or not interaction.guild.voice_client:
            await interaction.response.send_message(
                embed=error_embed("Erro", "Não estou tocando nada no momento."),
                ephemeral=True,
            )
            return

        player = cast(wavelink.Player, interaction.guild.voice_client)
        current = player.current

        if not current:
            await interaction.response.send_message(
                embed=error_embed("Erro", "Nenhuma música está tocando."),
                ephemeral=True,
            )
            return

        position_ms = seconds * 1000

        if position_ms < 0 or position_ms > current.length:
            max_secs = current.length // 1000
            await interaction.response.send_message(
                embed=error_embed(
                    "Posição Inválida",
                    f"Escolha um valor entre **0** e **{max_secs}** segundos.",
                ),
                ephemeral=True,
            )
            return

        await player.seek(position_ms)
        await interaction.response.send_message(
            embed=music_embed(
                "Seek",
                f"⏩ Avançado para **{format_duration(position_ms)}** / "
                f"`{format_duration(current.length)}`",
            )
        )

    # ── Error Handlers ───────────────────────────────

    @play_cmd.error
    async def play_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        """Trata erros do comando /play (cooldown, etc)."""
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                embed=error_embed(
                    "Cooldown",
                    f"⏳ Aguarde **{error.retry_after:.1f}s** antes de usar este comando novamente.",
                ),
                ephemeral=True,
            )
        else:
            logger.error(f"[Music] Erro no /play: {error}")
            try:
                await interaction.response.send_message(
                    embed=error_embed(
                        "Erro Inesperado",
                        "Algo deu errado ao tentar tocar a música. Tente novamente.",
                    ),
                    ephemeral=True,
                )
            except discord.InteractionResponded:
                await interaction.followup.send(
                    embed=error_embed(
                        "Erro Inesperado",
                        "Algo deu errado ao tentar tocar a música. Tente novamente.",
                    ),
                    ephemeral=True,
                )


async def setup(bot: commands.Bot) -> None:
    """Registra o cog de música no bot."""
    await bot.add_cog(Music(bot))
