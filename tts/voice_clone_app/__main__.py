from . import settings
from .ui import build_demo


def main():
    demo = build_demo()
    demo.launch(server_name=settings.HOST, server_port=settings.PORT, share=False)


if __name__ == "__main__":
    main()
