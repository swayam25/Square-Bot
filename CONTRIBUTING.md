# 🤝 Contributing

Thanks for wanting to help out! Whether it's a bug fix, a new feature, or a docs tweak, here's what you need to get a local copy running and how we like changes to land.

## 📦 Prerequisites

[![Python](https://shieldcn.dev/badge/Python-v3.14.svg?brand=python)](https://www.python.org/downloads/)
[![uv](https://shieldcn.dev/badge/uv-v0.13.9.svg?brand=uv)](https://docs.astral.sh/uv/getting-started/installation/)
[![Node.js](https://shieldcn.dev/badge/Node.js-v24.svg?color=5fa04e&logo=nodedotjs)](https://nodejs.org/en/download)
[![pnpm](https://shieldcn.dev/badge/pnpm-v12.16.1.svg?brand=pnpm)](https://pnpm.io/installation)

[![Docker](https://shieldcn.dev/badge/Docker-v23%2B.svg?brand=docker)](https://docs.docker.com/engine/install/)
[![Just](https://shieldcn.dev/badge/Just-v1.23%2B.svg?logo=lu:SquareTerminal&variant=secondary)](https://just.systems/man/en/packages.html)

## 🛸 Local Development

1. Clone the repository
    ```sh
    git clone https://github.com/swayam25/Square-Bot square
    cd square
    ```

2. Set up the project, then fill in the empty keys in `apps/bot/config.toml` and `apps/web/.env`

    ```sh
    just init --dev
    ```

> [!TIP]
> Check the [configuration](./README.md#-configuration) section for details on the configuration keys.

3. Run the bot and the dashboard

    ```sh
    just dev
    ```

> [!TIP]
> Drizzle Gateway starts with the other services, at http://localhost:4983. So does RustFS, with its console at http://localhost:9001/rustfs/console (`square` / `youcannotpass`).

4. Stop it when done

    ```sh
    just down --dev
    ```

## 🍀 Making a Pull Request

1. Fork the repository and clone your fork.
2. Follow [Local Development](#-local-development) above to get it running.
3. Create a branch for your change, commit your work, and open a pull request.

## 📋 Guidelines

- **Commits**: Write clear, meaningful messages that describe *what* changed and *why*, and follow the style used in the project's history.
- **Code quality**: Keep the code clean, readable, and consistent with the surrounding style.
- **Design**: Dashboard and image card changes follow [DESIGN.md](./DESIGN.md).
- **Testing**: Run the bot locally and confirm your change works as expected before opening a PR.
