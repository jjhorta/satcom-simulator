# Contributing to Satcom

Thank you for your interest in contributing to the Satellite Constellation Simulator! This document provides guidelines for contributing to the project.

## Getting Started

### Development Setup

1. Clone the repository:
```bash
git clone https://github.com/jjhorta/satcom.git
cd satcom
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

4. Install the package in development mode:
```bash
pip install -e .
```

## Development Workflow

### Running Tests

Run all tests:
```bash
pytest tests/
```

Run with coverage:
```bash
pytest --cov=satcom --cov-report=html tests/
```

### Code Style

- Follow PEP 8 guidelines
- Use descriptive variable names
- Add docstrings to all functions and classes
- Keep functions focused and modular

### Testing Guidelines

- Write tests for all new features
- Maintain test coverage above 80%
- Use descriptive test names (e.g., `test_satellite_propagation`)
- Test edge cases and error conditions

### Project Structure

```
satcom/
├── src/satcom/           # Source code
│   ├── __init__.py
│   ├── orbital_mechanics.py
│   ├── satellite.py
│   ├── ground_station.py
│   ├── constellation.py
│   ├── simulator.py
│   ├── visualization.py
│   └── cli.py
├── tests/                # Test files
├── examples/             # Example scripts
├── configs/              # Configuration examples
└── docs/                 # Documentation (future)
```

## Contributing Guidelines

### Reporting Bugs

When reporting bugs, please include:
- Python version
- Operating system
- Steps to reproduce
- Expected behavior
- Actual behavior
- Error messages/stack traces

### Suggesting Features

For feature requests:
- Describe the use case
- Explain the expected behavior
- Provide examples if possible
- Discuss potential implementation approaches

### Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add/update tests
5. Ensure all tests pass
6. Update documentation
7. Commit your changes (`git commit -m 'Add amazing feature'`)
8. Push to the branch (`git push origin feature/amazing-feature`)
9. Open a Pull Request

### Pull Request Checklist

- [ ] Tests pass locally
- [ ] New tests added for new features
- [ ] Documentation updated
- [ ] Code follows project style
- [ ] Commit messages are clear
- [ ] Branch is up to date with main

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers
- Focus on constructive feedback
- Assume good intentions

## Areas for Contribution

Here are some areas where contributions are welcome:

### Enhancements
- Additional orbital propagation methods (SGP4, numerical integration)
- More constellation patterns (polar, sun-synchronous, etc.)
- Advanced perturbation modeling (atmospheric drag, solar pressure, J2)
- Link budget calculations
- Doppler shift calculations
- Inter-satellite links
- More visualization options

### Documentation
- API documentation
- Tutorial notebooks
- Real-world examples
- Performance optimization guide

### Testing
- Additional test cases
- Performance benchmarks
- Integration tests

### Tools
- Configuration file loader (JSON/YAML)
- Data export capabilities
- Animation generation
- Real-time visualization

## Questions?

If you have questions about contributing, feel free to:
- Open an issue for discussion
- Reach out to the maintainers
- Check existing issues and PRs

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
