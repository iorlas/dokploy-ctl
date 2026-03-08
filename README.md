# dokployctl

CLI for Dokploy deployments — sync, deploy, poll, and verify container health from the terminal.

## Install

```bash
pip install dokployctl
# or
uv tool install dokployctl
```

## Quick Start

```bash
dokployctl login --url https://your-dokploy.example.com --token <api-token>
dokployctl deploy <compose-app-id> docker-compose.prod.yml
```

## Commands

| Command  | Description                                              |
|----------|----------------------------------------------------------|
| `login`  | Store Dokploy credentials                                |
| `deploy` | Sync + deploy + poll + verify container health           |
| `sync`   | Sync compose file + env to Dokploy (without deploying)   |
| `status` | Show compose app status (`--live` for containers)        |
| `logs`   | Show container runtime logs (`-D` for deploy log)        |
| `api`    | Raw API call (like `gh api`)                             |
| `init`   | Create new compose app                                   |

## Links

- [Dokploy](https://dokploy.com)

## License

MIT
