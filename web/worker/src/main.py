import asyncio
import signal

from src.services.mqtt_worker import MQTTWorker


async def main():
    worker = MQTTWorker()
    task = asyncio.create_task(worker.start())
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, task.cancel)
    try:
        await task
    except asyncio.CancelledError:
        worker.stop()


if __name__ == "__main__":
    asyncio.run(main())
