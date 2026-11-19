"""python -m cloudfolder.server [--host 0.0.0.0] [--port 8000]"""
import argparse

import uvicorn

from .app import create_app


def main() -> None:
    parser = argparse.ArgumentParser(description="Сервер «Хмарне сховище»")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--data", default=None, help="каталог даних (БД + вміст файлів)")
    args = parser.parse_args()
    uvicorn.run(create_app(args.data), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
