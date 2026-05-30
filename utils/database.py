"""
╔══════════════════════════════════════════════════╗
║      XW-2077 • Gerenciador de Banco de Dados    ║
╚══════════════════════════════════════════════════╝

Classe Database com aiosqlite para todas as operações
de persistência: warnings, níveis, welcome e tickets.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Optional

import aiosqlite

from config import Config
from utils.constants import xp_for_level


class Database:
    """Gerenciador assíncrono do banco de dados SQLite do XW-2077."""

    def __init__(self, db_path: str = Config.DB_PATH) -> None:
        self.db_path = db_path
        self._db: Optional[aiosqlite.Connection] = None

    # ══════════════════════════════════════════════════
    #                  INICIALIZAÇÃO
    # ══════════════════════════════════════════════════

    async def init(self) -> None:
        """Inicializa a conexão e cria as tabelas caso não existam."""
        # Garante que o diretório existe
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)

        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row

        await self._create_tables()

    async def _create_tables(self) -> None:
        """Cria todas as tabelas do sistema."""
        assert self._db is not None

        await self._db.executescript("""
            CREATE TABLE IF NOT EXISTS warnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                moderator_id INTEGER NOT NULL,
                reason TEXT NOT NULL,
                timestamp TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS levels (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 0,
                total_messages INTEGER DEFAULT 0,
                PRIMARY KEY (guild_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS welcome_config (
                guild_id INTEGER PRIMARY KEY,
                welcome_channel_id INTEGER,
                goodbye_channel_id INTEGER,
                welcome_message TEXT DEFAULT 'Bem-vindo(a) ao servidor, {user}! 🎉',
                goodbye_message TEXT DEFAULT '{user} saiu do servidor. 👋',
                auto_role_id INTEGER,
                enabled INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS ticket_config (
                guild_id INTEGER PRIMARY KEY,
                category_id INTEGER,
                log_channel_id INTEGER,
                support_role_id INTEGER,
                enabled INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                status TEXT DEFAULT 'open',
                category TEXT DEFAULT 'geral',
                created_at TEXT NOT NULL,
                closed_at TEXT
            );
        """)
        await self._db.commit()

    async def close(self) -> None:
        """Fecha a conexão com o banco de dados."""
        if self._db:
            await self._db.close()
            self._db = None

    # ══════════════════════════════════════════════════
    #                    WARNINGS
    # ══════════════════════════════════════════════════

    async def add_warning(
        self,
        guild_id: int,
        user_id: int,
        moderator_id: int,
        reason: str,
    ) -> int:
        """Adiciona um aviso a um usuário.

        Returns
        -------
        int
            O ID do aviso criado.
        """
        assert self._db is not None
        timestamp = datetime.now(timezone.utc).isoformat()

        cursor = await self._db.execute(
            """
            INSERT INTO warnings (guild_id, user_id, moderator_id, reason, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (guild_id, user_id, moderator_id, reason, timestamp),
        )
        await self._db.commit()
        return cursor.lastrowid  # type: ignore[return-value]

    async def get_warnings(
        self, guild_id: int, user_id: int
    ) -> list[dict[str, Any]]:
        """Retorna todos os avisos de um usuário em um servidor."""
        assert self._db is not None

        cursor = await self._db.execute(
            """
            SELECT id, moderator_id, reason, timestamp
            FROM warnings
            WHERE guild_id = ? AND user_id = ?
            ORDER BY timestamp DESC
            """,
            (guild_id, user_id),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def remove_warning(self, warning_id: int) -> bool:
        """Remove um aviso pelo ID.

        Returns
        -------
        bool
            ``True`` se o aviso foi removido, ``False`` se não existia.
        """
        assert self._db is not None

        cursor = await self._db.execute(
            "DELETE FROM warnings WHERE id = ?",
            (warning_id,),
        )
        await self._db.commit()
        return cursor.rowcount > 0

    async def clear_warnings(self, guild_id: int, user_id: int) -> int:
        """Limpa todos os avisos de um usuário em um servidor.

        Returns
        -------
        int
            Quantidade de avisos removidos.
        """
        assert self._db is not None

        cursor = await self._db.execute(
            "DELETE FROM warnings WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        )
        await self._db.commit()
        return cursor.rowcount

    # ══════════════════════════════════════════════════
    #                    LEVELING
    # ══════════════════════════════════════════════════

    async def get_user_level(
        self, guild_id: int, user_id: int
    ) -> dict[str, Any]:
        """Retorna os dados de nível de um usuário.

        Retorna um dict com: xp, level, total_messages.
        Se o usuário não existe, retorna valores padrão.
        """
        assert self._db is not None

        cursor = await self._db.execute(
            """
            SELECT xp, level, total_messages
            FROM levels
            WHERE guild_id = ? AND user_id = ?
            """,
            (guild_id, user_id),
        )
        row = await cursor.fetchone()

        if row:
            return dict(row)
        return {"xp": 0, "level": 0, "total_messages": 0}

    async def add_xp(
        self, guild_id: int, user_id: int, amount: int
    ) -> tuple[int, bool]:
        """Adiciona XP a um usuário e verifica level up.

        Parameters
        ----------
        guild_id : int
            ID do servidor.
        user_id : int
            ID do usuário.
        amount : int
            Quantidade de XP a adicionar.

        Returns
        -------
        tuple[int, bool]
            ``(novo_nível, subiu_de_nível)``
        """
        assert self._db is not None

        # Garante que o registro existe
        await self._db.execute(
            """
            INSERT OR IGNORE INTO levels (guild_id, user_id, xp, level, total_messages)
            VALUES (?, ?, 0, 0, 0)
            """,
            (guild_id, user_id),
        )

        # Incrementa XP e mensagens
        await self._db.execute(
            """
            UPDATE levels
            SET xp = xp + ?, total_messages = total_messages + 1
            WHERE guild_id = ? AND user_id = ?
            """,
            (amount, guild_id, user_id),
        )

        # Busca dados atualizados
        cursor = await self._db.execute(
            "SELECT xp, level FROM levels WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        )
        row = await cursor.fetchone()
        assert row is not None

        current_xp: int = row["xp"]
        current_level: int = row["level"]
        required_xp = xp_for_level(current_level)
        leveled_up = False

        # Verifica level up (pode subir múltiplos níveis de uma vez)
        while current_xp >= required_xp:
            current_xp -= required_xp
            current_level += 1
            required_xp = xp_for_level(current_level)
            leveled_up = True

        # Atualiza se houve level up
        if leveled_up:
            await self._db.execute(
                """
                UPDATE levels SET xp = ?, level = ?
                WHERE guild_id = ? AND user_id = ?
                """,
                (current_xp, current_level, guild_id, user_id),
            )

        await self._db.commit()
        return current_level, leveled_up

    async def set_xp(
        self, guild_id: int, user_id: int, xp: int, level: int
    ) -> None:
        """Define manualmente o XP e nível de um usuário."""
        assert self._db is not None

        await self._db.execute(
            """
            INSERT INTO levels (guild_id, user_id, xp, level, total_messages)
            VALUES (?, ?, ?, ?, 0)
            ON CONFLICT(guild_id, user_id)
            DO UPDATE SET xp = ?, level = ?
            """,
            (guild_id, user_id, xp, level, xp, level),
        )
        await self._db.commit()

    async def reset_xp(self, guild_id: int, user_id: int) -> None:
        """Reseta o XP e nível de um usuário para 0."""
        assert self._db is not None

        await self._db.execute(
            """
            DELETE FROM levels
            WHERE guild_id = ? AND user_id = ?
            """,
            (guild_id, user_id),
        )
        await self._db.commit()

    async def get_leaderboard(
        self, guild_id: int, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Retorna o ranking de XP de um servidor.

        Parameters
        ----------
        guild_id : int
            ID do servidor.
        limit : int
            Quantidade máxima de resultados (padrão: 10).

        Returns
        -------
        list[dict]
            Lista de dicts com: user_id, xp, level, total_messages.
        """
        assert self._db is not None

        cursor = await self._db.execute(
            """
            SELECT user_id, xp, level, total_messages
            FROM levels
            WHERE guild_id = ?
            ORDER BY level DESC, xp DESC
            LIMIT ?
            """,
            (guild_id, limit),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_rank(self, guild_id: int, user_id: int) -> int:
        """Retorna a posição do usuário no ranking do servidor.

        Returns
        -------
        int
            Posição (1-indexed). Retorna ``0`` se o usuário não tem dados.
        """
        assert self._db is not None

        # Busca dados do usuário
        cursor = await self._db.execute(
            "SELECT level, xp FROM levels WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        )
        user_row = await cursor.fetchone()

        if not user_row:
            return 0

        # Conta quantos estão acima
        cursor = await self._db.execute(
            """
            SELECT COUNT(*) as position FROM levels
            WHERE guild_id = ?
              AND (level > ? OR (level = ? AND xp > ?))
            """,
            (guild_id, user_row["level"], user_row["level"], user_row["xp"]),
        )
        row = await cursor.fetchone()
        assert row is not None
        return row["position"] + 1

    # ══════════════════════════════════════════════════
    #                    WELCOME
    # ══════════════════════════════════════════════════

    async def get_welcome_config(
        self, guild_id: int
    ) -> Optional[dict[str, Any]]:
        """Retorna a configuração de boas-vindas de um servidor."""
        assert self._db is not None

        cursor = await self._db.execute(
            "SELECT * FROM welcome_config WHERE guild_id = ?",
            (guild_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def set_welcome_config(
        self,
        guild_id: int,
        *,
        welcome_channel_id: Optional[int] = None,
        goodbye_channel_id: Optional[int] = None,
        welcome_message: Optional[str] = None,
        goodbye_message: Optional[str] = None,
        auto_role_id: Optional[int] = None,
        enabled: Optional[int] = None,
    ) -> None:
        """Cria ou atualiza a configuração de boas-vindas.

        Apenas os parâmetros fornecidos (não-None) serão atualizados.
        """
        assert self._db is not None

        # Verifica se já existe
        existing = await self.get_welcome_config(guild_id)

        if not existing:
            # Insere novo registro com valores padrão
            await self._db.execute(
                """
                INSERT INTO welcome_config (
                    guild_id, welcome_channel_id, goodbye_channel_id,
                    welcome_message, goodbye_message, auto_role_id, enabled
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    guild_id,
                    welcome_channel_id,
                    goodbye_channel_id,
                    welcome_message or "Bem-vindo(a) ao servidor, {user}! 🎉",
                    goodbye_message or "{user} saiu do servidor. 👋",
                    auto_role_id,
                    enabled if enabled is not None else 0,
                ),
            )
        else:
            # Atualiza apenas os campos fornecidos
            updates: list[str] = []
            values: list[Any] = []

            if welcome_channel_id is not None:
                updates.append("welcome_channel_id = ?")
                values.append(welcome_channel_id)
            if goodbye_channel_id is not None:
                updates.append("goodbye_channel_id = ?")
                values.append(goodbye_channel_id)
            if welcome_message is not None:
                updates.append("welcome_message = ?")
                values.append(welcome_message)
            if goodbye_message is not None:
                updates.append("goodbye_message = ?")
                values.append(goodbye_message)
            if auto_role_id is not None:
                updates.append("auto_role_id = ?")
                values.append(auto_role_id)
            if enabled is not None:
                updates.append("enabled = ?")
                values.append(enabled)

            if updates:
                values.append(guild_id)
                await self._db.execute(
                    f"UPDATE welcome_config SET {', '.join(updates)} WHERE guild_id = ?",
                    values,
                )

        await self._db.commit()

    # ══════════════════════════════════════════════════
    #                    TICKETS
    # ══════════════════════════════════════════════════

    async def get_ticket_config(
        self, guild_id: int
    ) -> Optional[dict[str, Any]]:
        """Retorna a configuração de tickets de um servidor."""
        assert self._db is not None

        cursor = await self._db.execute(
            "SELECT * FROM ticket_config WHERE guild_id = ?",
            (guild_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def set_ticket_config(
        self,
        guild_id: int,
        *,
        category_id: Optional[int] = None,
        log_channel_id: Optional[int] = None,
        support_role_id: Optional[int] = None,
        enabled: Optional[int] = None,
    ) -> None:
        """Cria ou atualiza a configuração de tickets."""
        assert self._db is not None

        existing = await self.get_ticket_config(guild_id)

        if not existing:
            await self._db.execute(
                """
                INSERT INTO ticket_config (
                    guild_id, category_id, log_channel_id,
                    support_role_id, enabled
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    guild_id,
                    category_id,
                    log_channel_id,
                    support_role_id,
                    enabled if enabled is not None else 0,
                ),
            )
        else:
            updates: list[str] = []
            values: list[Any] = []

            if category_id is not None:
                updates.append("category_id = ?")
                values.append(category_id)
            if log_channel_id is not None:
                updates.append("log_channel_id = ?")
                values.append(log_channel_id)
            if support_role_id is not None:
                updates.append("support_role_id = ?")
                values.append(support_role_id)
            if enabled is not None:
                updates.append("enabled = ?")
                values.append(enabled)

            if updates:
                values.append(guild_id)
                await self._db.execute(
                    f"UPDATE ticket_config SET {', '.join(updates)} WHERE guild_id = ?",
                    values,
                )

        await self._db.commit()

    async def create_ticket(
        self,
        guild_id: int,
        user_id: int,
        channel_id: int,
        category: str = "geral",
    ) -> int:
        """Cria um novo ticket.

        Returns
        -------
        int
            O ID do ticket criado.
        """
        assert self._db is not None
        created_at = datetime.now(timezone.utc).isoformat()

        cursor = await self._db.execute(
            """
            INSERT INTO tickets (guild_id, user_id, channel_id, category, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (guild_id, user_id, channel_id, category, created_at),
        )
        await self._db.commit()
        return cursor.lastrowid  # type: ignore[return-value]

    async def close_ticket(self, ticket_id: int) -> bool:
        """Fecha um ticket pelo ID.

        Returns
        -------
        bool
            ``True`` se o ticket foi fechado, ``False`` se não existia.
        """
        assert self._db is not None
        closed_at = datetime.now(timezone.utc).isoformat()

        cursor = await self._db.execute(
            """
            UPDATE tickets SET status = 'closed', closed_at = ?
            WHERE id = ? AND status = 'open'
            """,
            (closed_at, ticket_id),
        )
        await self._db.commit()
        return cursor.rowcount > 0

    async def get_open_tickets(
        self, guild_id: int, user_id: Optional[int] = None
    ) -> list[dict[str, Any]]:
        """Retorna os tickets abertos de um servidor.

        Parameters
        ----------
        guild_id : int
            ID do servidor.
        user_id : int, optional
            Se fornecido, filtra apenas os tickets desse usuário.

        Returns
        -------
        list[dict]
            Lista de tickets abertos.
        """
        assert self._db is not None

        if user_id:
            cursor = await self._db.execute(
                """
                SELECT * FROM tickets
                WHERE guild_id = ? AND user_id = ? AND status = 'open'
                ORDER BY created_at DESC
                """,
                (guild_id, user_id),
            )
        else:
            cursor = await self._db.execute(
                """
                SELECT * FROM tickets
                WHERE guild_id = ? AND status = 'open'
                ORDER BY created_at DESC
                """,
                (guild_id,),
            )

        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
