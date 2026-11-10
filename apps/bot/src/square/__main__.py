def main() -> None:
    # Logging is configured before the bot is imported, so modules that log while loading are formatted too.
    from square.log import setup_logging
    from square.utils import config

    setup_logging(config.log_level, config.log_file)

    from square.bot import run

    run()


if __name__ == "__main__":
    main()
