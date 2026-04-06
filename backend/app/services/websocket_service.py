"""WebSocket real-time push service.

Pushes pipeline stage updates to connected frontend clients
via WebSocket, with Redis Pub/Sub for multi-instance broadcast.
"""

import asyncio
import json
from datetime import datetime, timezone

import structlog
from fastapi import WebSocket, WebSocketDisconnect, APIRouter, Query
from starlette.websockets import WebSocketState
import redis.asyncio as aioredis

from app.core.config import get_settings
from app.core.security import decode_access_token

logger = structlog.get_logger()
settings = get_settings()

router = APIRouter(tags=["websocket"])


class ConnectionManager:
    """Manages WebSocket connections grouped by project_id."""

    def __init__(self):
        # project_id -> set of WebSocket connections
        self._connections: dict[str, set[WebSocket]] = {}
        self._redis: aioredis.Redis | None = None
        self._subscriber_task: asyncio.Task | None = None

    # ── Connection lifecycle ──

    async def connect(self, websocket: WebSocket, project_id: str) -> None:
        """Accept and register a WebSocket connection."""
        await websocket.accept()

        if project_id not in self._connections:
            self._connections[project_id] = set()
        self._connections[project_id].add(websocket)

        logger.info(
            "ws_connected",
            project_id=project_id,
            total=len(self._connections[project_id]),
        )

    def disconnect(self, websocket: WebSocket, project_id: str) -> None:
        """Remove a WebSocket connection."""
        conns = self._connections.get(project_id)
        if conns:
            conns.discard(websocket)
            if not conns:
                del self._connections[project_id]

        logger.info("ws_disconnected", project_id=project_id)

    @property
    def active_connections(self) -> int:
        return sum(len(s) for s in self._connections.values())

    # ── Messaging ──

    async def send_to_project(self, project_id: str, message: dict) -> None:
        """Send a message to all connections watching a project.

        Also publishes to Redis so other server instances can forward it.
        """
        payload = json.dumps(message, ensure_ascii=False, default=str)

        # Publish to Redis for cross-instance delivery
        await self._publish_to_redis(project_id, payload)

        # Deliver to local connections
        await self._deliver_local(project_id, payload)

    async def _deliver_local(self, project_id: str, payload: str) -> None:
        """Deliver to WebSocket connections on this instance."""
        conns = self._connections.get(project_id)
        if not conns:
            return

        stale: list[WebSocket] = []
        for ws in conns:
            try:
                if ws.client_state == WebSocketState.CONNECTED:
                    await ws.send_text(payload)
                else:
                    stale.append(ws)
            except Exception:
                stale.append(ws)

        for ws in stale:
            conns.discard(ws)

    # ── Redis Pub/Sub ──

    async def init_redis(self) -> None:
        """Initialize Redis connection and start subscriber."""
        try:
            self._redis = aioredis.from_url(
                settings.redis_url,
                decode_responses=True,
                max_connections=10,
            )
            await self._redis.ping()
            self._subscriber_task = asyncio.create_task(self._redis_subscriber())
            logger.info("redis_pubsub_initialized")
        except Exception as e:
            logger.warning("redis_init_failed", error=str(e))
            self._redis = None

    async def shutdown_redis(self) -> None:
        """Cleanup Redis connections."""
        if self._subscriber_task:
            self._subscriber_task.cancel()
        if self._redis:
            await self._redis.aclose()

    async def _publish_to_redis(self, project_id: str, payload: str) -> None:
        """Publish message to Redis channel."""
        if not self._redis:
            return
        try:
            channel = f"project:{project_id}"
            await self._redis.publish(channel, payload)
        except Exception as e:
            logger.warning("redis_publish_failed", error=str(e))

    async def _redis_subscriber(self) -> None:
        """Background task: subscribe to Redis and forward messages."""
        if not self._redis:
            return

        pubsub = self._redis.pubsub()
        try:
            # Subscribe to all project channels via pattern
            await pubsub.psubscribe("project:*")

            async for msg in pubsub.listen():
                if msg["type"] != "pmessage":
                    continue
                # Extract project_id from channel name "project:{id}"
                channel: str = msg["channel"]
                project_id = channel.split(":", 1)[-1] if ":" in channel else ""
                payload: str = msg["data"]

                if project_id:
                    await self._deliver_local(project_id, payload)

        except asyncio.CancelledError:
            logger.info("redis_subscriber_cancelled")
        except Exception as e:
            logger.error("redis_subscriber_error", error=str(e))
        finally:
            await pubsub.unsubscribe()
            await pubsub.aclose()


# ── Singleton ──
manager = ConnectionManager()


# ── Helper functions for agents/orchestrator ──

def build_stage_message(
    event: str,
    project_id: str,
    stage_number: int | None = None,
    data: dict | None = None,
) -> dict:
    """Build a standard WebSocket message."""
    return {
        "event": event,
        "project_id": str(project_id),
        "stage_number": stage_number,
        "data": data or {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


async def notify_stage_started(project_id: str, stage_number: int, stage_name: str) -> None:
    msg = build_stage_message("stage_started", project_id, stage_number, {"stage_name": stage_name})
    await manager.send_to_project(str(project_id), msg)


async def notify_stage_completed(
    project_id: str, stage_number: int, stage_name: str, confidence: float = 0.0
) -> None:
    msg = build_stage_message(
        "stage_completed", project_id, stage_number,
        {"stage_name": stage_name, "confidence": confidence},
    )
    await manager.send_to_project(str(project_id), msg)


async def notify_stage_failed(project_id: str, stage_number: int, error: str) -> None:
    msg = build_stage_message("stage_failed", project_id, stage_number, {"error": error})
    await manager.send_to_project(str(project_id), msg)


async def notify_pipeline_completed(project_id: str, qa_verdict: str) -> None:
    msg = build_stage_message("pipeline_completed", project_id, data={"qa_verdict": qa_verdict})
    await manager.send_to_project(str(project_id), msg)


# ── WebSocket route ──

@router.websocket("/ws/{project_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    project_id: str,
    token: str = Query(default=""),
):
    """WebSocket endpoint for real-time pipeline updates.

    Connect: ws://host/ws/{project_id}?token=<jwt_token>
    """
    # Authenticate
    if token:
        try:
            decode_access_token(token)
        except Exception:
            await websocket.close(code=4001, reason="Invalid token")
            return
    else:
        await websocket.close(code=4001, reason="Token required")
        return

    await manager.connect(websocket, project_id)

    try:
        while True:
            # Keep connection alive; handle client pings
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                # Handle client heartbeat
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # Send server-side ping to keep alive
                try:
                    await websocket.send_text(json.dumps({"event": "ping"}))
                except Exception:
                    break
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning("ws_error", project_id=project_id, error=str(e))
    finally:
        manager.disconnect(websocket, project_id)
