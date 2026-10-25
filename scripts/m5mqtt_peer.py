"""Run the project local-test MQTT peer or send one independent notification."""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import replace

from sbd.core.config.models import MQTTConfig
from sbd.input_events.mqtt.local_peer import LocalTestPeer


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--topic-prefix", default="snowboard")
    parser.add_argument("--device-id", default="dev-01")
    parser.add_argument("--mode", choices=sorted(LocalTestPeer.MODES), default="empty")
    parser.add_argument("--delay-seconds", type=float, default=0.0)
    parser.add_argument("--notify")
    args = parser.parse_args()
    config = replace(MQTTConfig(), host=args.host, port=args.port,
        topic_prefix=args.topic_prefix, device_id=args.device_id,
        client_id="snowboard-local-notify" if args.notify is not None else "snowboard-local-peer")
    peer = LocalTestPeer(config=config, mode=args.mode, delay_seconds=args.delay_seconds)
    await peer.start()
    try:
        if args.notify is not None:
            await peer.send_notification(args.notify)
        else:
            while True:
                await asyncio.sleep(3600)
    finally:
        await peer.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
