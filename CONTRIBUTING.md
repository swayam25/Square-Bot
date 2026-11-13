# 🤝 Contributing

Thanks for wanting to help out! Whether it's a bug fix, a new feature, or a docs tweak, here's what you need to get a local copy running and how we like changes to land.

## 💫 Prerequisites

Everything in the [README's prerequisites](./README.md#-prerequisites), plus a couple of things only needed for development:

| Tool                                                                                                                                     | Version | Purpose                                           |
| ---------------------------------------------------------------------------------------------------------------------------------------- | ------- | ------------------------------------------------- |
| [![Python](https://img.shields.io/badge/Python-%233776AB?style=for-the-badge&logo=python&logoColor=%23FFFFFF)](https://www.python.org/)  | 3.14+   | The programming language used to develop the bot. |
| [![UV](https://img.shields.io/badge/UV-%23DE5FE9?style=for-the-badge&logo=uv&logoColor=%23FFFFFF)](https://docs.astral.sh/uv/)           | 0.13+   | A modern Python package manager for development.  |
| [![Node.js](https://img.shields.io/badge/Node.js-%235FA04E?style=for-the-badge&logo=nodedotjs&logoColor=%23FFFFFF)](https://nodejs.org/) | 24+     | Runs the web dashboard and the tooling.           |
| [![pnpm](https://img.shields.io/badge/pnpm-%23F69220?style=for-the-badge&logo=pnpm&logoColor=%23FFFFFF)](https://pnpm.io/)               | 12+     | Installs the JavaScript packages.                 |

## 🛸 Local Development

1. Follow the first step of the [production setup](./README.md#-production) - clone the repo.

2. Install the dependencies and git hooks, and create your `config.toml` file

    ```sh
    just init
    ```

> [!TIP]
> Check [configuration](./README.md#-configuration) section for details on the configuration keys.

3. Start the local docker services

    ```sh
    just up --dev
    ```

4. Run the bot and the dashboard

    ```sh
    just dev
    ```

> `just dev` auto-starts services if they aren't already running, so you can skip step 3 and run it directly. It also logs at `DEBUG`. The dashboard runs at http://localhost:5173.

5. Stop it when done

    ```sh
    just down --dev
    ```

## 🍀 Making a Pull Request

1. Fork the repository and clone your fork.
2. Follow [Local Development](#-local-development) above to get it running.
3. Create a branch for your change, commit your work, and open a pull request.

## 📋 Guidelines

- **Commits**: Write clear, meaningful messages that describe *what* changed and *why*, and follow the style used in the project's history.
- **Code quality**: Keep the code clean, readable, and consistent with the surrounding style. Git hooks (lefthook) run ruff, prettier and eslint on staged files at every commit. `pnpm run lint`, `pnpm run check` and `pnpm run format:check` run the same checks as CI.
- **Design**: Dashboard and image card changes follow [DESIGN.md](./DESIGN.md).
- **Testing**: Run the bot locally and confirm your change works as expected before opening a PR.
