# Contributing to AAIF PMO Agent MCP Server

Thank you for your interest in contributing to the AAIF PMO Agent MCP Server.

## Developer Certificate of Origin (DCO)

This project uses the [Developer Certificate of Origin](https://developercertificate.org/) (DCO). All contributors must sign-off on their commits to certify that they have the right to submit the code under the project's license.

### How to Sign Off

Add a `Signed-off-by` line to your commit messages:

```
Signed-off-by: Your Name <your.email@example.com>
```

You can do this automatically with:

```bash
git commit -s -m "Your commit message"
```

### What the DCO Means

By signing off, you certify that:

1. The contribution was created in whole or in part by you and you have the right to submit it under the open source license indicated in the file; or
2. The contribution is based upon previous work that, to the best of your knowledge, is covered under an appropriate open source license and you have the right under that license to submit that work with modifications; or
3. The contribution was provided directly to you by some other person who certified (1) or (2) and you have not modified it.

## Getting Started

### Prerequisites

- Python 3.10+
- pip

### Local Development

```bash
# Clone the repository
git clone git@github.com:linuxfoundation/aaif-mcp-server.git
cd aaif-mcp-server

# Install in development mode with test dependencies
pip install -e ".[test]"

# Run in sandbox mode (no external credentials needed)
python -m aaif_mcp_server
```

### Running Tests

```bash
pytest -v --tb=short
```

### Code Style

This project uses [ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
# Check linting
ruff check src/

# Check formatting
ruff format --check src/

# Auto-fix
ruff check --fix src/
ruff format src/
```

## Making Changes

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Make your changes
4. Ensure tests pass (`pytest -v`)
5. Ensure linting passes (`ruff check src/`)
6. Commit with DCO sign-off (`git commit -s -m "Add your feature"`)
7. Push to your fork (`git push origin feature/your-feature`)
8. Open a Pull Request

## Adding New Tools

New MCP tools are auto-registered. To add a tool:

1. Create a new file in `src/aaif_mcp_server/tools/` or add to an existing module
2. Define your tool function with type hints and docstring
3. Register it in `src/aaif_mcp_server/tools/_registry.py`
4. Add tests in `tests/`
5. Update the README tool count if needed

## Adding New Connectors

1. Create a new file in `src/aaif_mcp_server/connectors/`
2. Extend the `BaseConnector` class
3. Implement `connect()` with mock-data fallback
4. Register in `src/aaif_mcp_server/connectors/registry.py`
5. Add environment variables to `.env.example`

## Reporting Issues

Please use GitHub Issues to report bugs or request features. Include:

- Steps to reproduce
- Expected vs actual behavior
- Python version and OS
- Relevant logs or error messages

## Code of Conduct

This project follows the [Linux Foundation Code of Conduct](https://www.linuxfoundation.org/code-of-conduct/).

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.
