import asyncio

# Fila compartilhada entre handlers e worker.
# Para produção com alto volume, substituir por SQLite-backed queue.
activity_queue: asyncio.Queue = asyncio.Queue()
