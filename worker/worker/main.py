"""
Worker main entry point.

Subscribes to worker:control Redis channel and manages per-channel pipelines.
"""

import json
import logging
import signal
import sys
import time

import redis

from .config import settings
from .pipeline.channel_runner import ChannelConfig, ChannelRunner

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

CONTROL_CHANNEL = "worker:control"


class WorkerDaemon:
    def __init__(self) -> None:
        self._redis = redis.from_url(settings.redis_url, decode_responses=True)
        self._runners: dict[str, ChannelRunner] = {}
        self._running = True

    def run(self) -> None:
        pubsub = self._redis.pubsub()
        pubsub.subscribe(CONTROL_CHANNEL)
        logger.info("Worker listening on %s", CONTROL_CHANNEL)

        while self._running:
            message = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message.get("type") == "message":
                self._handle_message(json.loads(message["data"]))

        # Clean shutdown
        for channel_id, runner in list(self._runners.items()):
            logger.info("Shutting down channel %s", channel_id)
            runner.stop()
        pubsub.unsubscribe()
        pubsub.close()

    def _handle_message(self, msg: dict) -> None:
        action = msg.get("action")
        channel_id = msg.get("channel_id")
        if not channel_id:
            return

        if action == "start":
            self._start_channel(msg)
        elif action == "stop":
            self._stop_channel(channel_id)
        elif action == "restart":
            self._stop_channel(channel_id)
            time.sleep(1)
            self._start_channel(msg)

    def _start_channel(self, msg: dict) -> None:
        channel_id = msg["channel_id"]
        if channel_id in self._runners:
            logger.warning("Channel %s already running", channel_id)
            return
        config = ChannelConfig(
            channel_id=channel_id,
            name=msg.get("name", channel_id),
            input_protocol=msg.get("input_protocol", "file"),
            input_url=msg.get("input_url", ""),
            output_dir=msg.get("output_dir"),
        )
        runner = ChannelRunner(config, self._redis)
        self._runners[channel_id] = runner
        runner.start()

    def _stop_channel(self, channel_id: str) -> None:
        runner = self._runners.pop(channel_id, None)
        if runner:
            runner.stop()
        else:
            logger.warning("No runner found for channel %s", channel_id)

    def shutdown(self) -> None:
        logger.info("Received shutdown signal")
        self._running = False


def main() -> None:
    daemon = WorkerDaemon()

    def _handler(signum, frame):
        daemon.shutdown()

    signal.signal(signal.SIGTERM, _handler)
    signal.signal(signal.SIGINT, _handler)

    daemon.run()


if __name__ == "__main__":
    main()
