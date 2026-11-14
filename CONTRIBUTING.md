# 🤝 Contributing

Thanks for wanting to help out! Whether it's a bug fix, a new feature, or a docs tweak, here's what you need to get a local copy running and how we like changes to land.

## 💫 Prerequisites

Everything in the [README's prerequisites](./README.md#-prerequisites), plus a couple of things only needed for development:

| Tool                                                                                                                                    | Version | Purpose                                           |
| --------------------------------------------------------------------------------------------------------------------------------------- | ------- | ------------------------------------------------- |
| [![Python](https://img.shields.io/badge/Python-%233776AB?style=for-the-badge&logo=python&logoColor=%23FFFFFF)](https://www.python.org/) | 3.14+   | The programming language used to develop the bot. |
| [![UV](https://img.shields.io/badge/UV-%23DE5FE9?style=for-the-badge&logo=uv&logoColor=%23FFFFFF)](https://docs.astral.sh/uv/)          | 0.13+   | A modern Python package manager for development.  |

## 🛸 Local Development

1. Clone the repository
    ```sh
    git clone https://github.com/swayam25/Square-Bot square
    cd square
    ```

2. Set up the project

    ```sh
    just init --dev
    ```

> [!TIP]
> Check [configuration](./README.md#-configuration) section for details on the configuration keys.

3. Run the bot and the dashboard

    ```sh
    just dev
    ```

> [!TIP]
> Drizzle Gateway starts with the other services, at http://localhost:4983.

1. Stop it when done

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
