# 🤝 Contributing

Thanks for wanting to help out! Whether it's a bug fix, a new feature, or a docs tweak, here's what you need to get a local copy running and how we like changes to land.

## 💫 Prerequisites

Everything in the [README's prerequisites](./README.md#-prerequisites), plus a couple of things only needed for development:

| Tool                                                                                                                                    | Version | Purpose                                           |
| --------------------------------------------------------------------------------------------------------------------------------------- | ------- | ------------------------------------------------- |
| [![Python](https://img.shields.io/badge/Python-%233776AB?style=for-the-badge&logo=python&logoColor=%23FFFFFF)](https://www.python.org/) | 3.14+   | The programming language used to develop the bot. |
| [![UV](https://img.shields.io/badge/UV-%23DE5FE9?style=for-the-badge&logo=uv&logoColor=%23FFFFFF)](https://docs.astral.sh/uv/)          | 0.11+   | A modern Python package manager for development.  |

## 🛸 Local Development

1. Follow the first 2 steps of the [production setup](./README.md#-production) - clone the repo and create your config files.

2. Install the dependencies and set up pre-commit hooks

    ```sh
    just setup
    ```

3. Start the docker services

    ```sh
    just up
    ```

4. Run the bot

    ```sh
    just dev
    ```

    > `just dev` auto-starts services if they aren't already running, so you can skip step 3 and run it directly.

5. Stop the docker services when done
    ```sh
    just down
    ```

> [!IMPORTANT]
> The local stack runs Postgres, Drizzle Gateway - no Caddy, no auth.
>
> - Drizzle Gateway → `http://localhost:8081`
>
> Dozzle, Caddy and the containerized bot are production-only and live in [`docker-compose.prod.yml`](./docker-compose.prod.yml).

## 🍀 Making a Pull Request

1. Fork the repository and clone your fork.
2. Follow [Local Development](#-local-development) above to get it running.
3. Create a branch for your change, commit your work, and open a pull request.

## 📋 Guidelines

- **Commits**: Write clear, meaningful messages that describe *what* changed and *why*, and follow the style used in the project's history.
- **Code quality**: Keep the code clean, readable, and consistent with the surrounding style. Let the `pre-commit` hooks format and lint your changes before you push.
- **Testing**: Run the bot locally and confirm your change works as expected before opening a PR.
