# Contributing Guidelines

## Quick Start

1. Fork the repository
2. Create feature branch: `git checkout -b feature/YourFeature`
3. Make changes and test
4. Commit: `git commit -m 'Add YourFeature'`
5. Push: `git push origin feature/YourFeature`
6. Open Pull Request

## Code Standards

- **Python:** Follow PEP 8, use Black formatter
- **TypeScript:** Use ESLint + Prettier
- **Tests:** Add tests for new features
- **Docs:** Update relevant documentation

## Testing

```bash
# Python tests
pytest tests/ -v

# Frontend (if applicable)
cd frontend-nextjs
npm test
```

## Commit Messages

Use conventional commits:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation only
- `refactor:` Code refactoring
- `test:` Adding tests
- `chore:` Maintenance

Example: `feat: add WebSocket support for live data`

## Need Help?

Open an issue or discussion on GitHub.
