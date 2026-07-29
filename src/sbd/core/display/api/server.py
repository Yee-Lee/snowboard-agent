"""
Display API server — Unix domain socket transport (future).

This module will host the server side of the IPC channel so that
worker processes in other Python processes can send commands to the
display-service process over a Unix domain socket.

For now it provides the scaffolding and the JSON serialisation helpers.

Protocol (line-delimited JSON)
------------------------------
Client → Server:
    {"type": "set_status",   "animation": "starry_night", "owner": "ai"}
    {"type": "notify",       "text": "任務完成", "duration": 1.5}
    {"type": "show_alert",   "text": "網路中斷"}
    {"type": "dismiss_alert","layer_id": "<uuid>"}
    {"type": "play_media",   "animation": "startup_animation"}

Server → Client (ack):
    {"ok": true, "layer_id": "<uuid>"}   # for show_alert / play_media
    {"ok": true}                         # for others
    {"ok": false, "error": "<msg>"}      # on rejection
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

from ..service.service import DisplayService

logger = logging.getLogger(__name__)

DEFAULT_SOCKET = "/tmp/display-service.sock"


class DisplayServer:
    """
    Accepts connections on a Unix domain socket and forwards decoded
    commands to the DisplayService.

    This is optional infrastructure; in-process clients use DisplayClient
    directly and do not need this server.
    """

    def __init__(
        self,
        service: DisplayService,
        socket_path: str = DEFAULT_SOCKET,
    ) -> None:
        self._service = service
        self._socket_path = socket_path
        self._server: Optional[asyncio.Server] = None

    async def start(self) -> None:
        self._server = await asyncio.start_unix_server(
            self._handle_connection, path=self._socket_path
        )
        logger.info("[DisplayServer] listening on %s", self._socket_path)

    async def stop(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    # ------------------------------------------------------------------

    async def _handle_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        peer = writer.get_extra_info("peername", "<unknown>")
        logger.debug("[DisplayServer] connection from %s", peer)
        try:
            async for line in reader:
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                    response = await self._dispatch(msg)
                except (json.JSONDecodeError, KeyError) as exc:
                    response = {"ok": False, "error": str(exc)}

                writer.write((json.dumps(response) + "\n").encode())
                await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    async def _dispatch(self, msg: dict) -> dict:
        cmd_type = msg.get("type", "")

        if cmd_type == "set_status":
            await self._service.set_status(
                animation=msg.get("animation", "starry_night"),
                owner=msg.get("owner", "default"),
            )
            return {"ok": True}

        if cmd_type == "notify":
            await self._service.notify(
                text=msg["text"],
                duration=float(msg.get("duration", 1.5)),
            )
            return {"ok": True}

        if cmd_type == "show_alert":
            layer_id = await self._service.show_alert(
                text=msg["text"],
                duration=msg.get("duration"),
            )
            return {"ok": True, "layer_id": layer_id}

        if cmd_type == "dismiss_alert":
            await self._service.dismiss_alert(msg["layer_id"])
            return {"ok": True}

        if cmd_type == "play_media":
            handle = await self._service.play_media(
                animation=msg["animation"],
                duration=msg.get("duration"),
            )
            return {"ok": True, "layer_id": handle.layer_id}

        return {"ok": False, "error": f"Unknown command type: {cmd_type!r}"}
