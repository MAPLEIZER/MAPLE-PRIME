# Contributing

Kenya Data Rights uses test-first development. Read `docs/ENGINEERING-STANDARD.md` before changing code.

## Required workflow

1. Create or update an issue/acceptance criterion.
2. Add a failing test first.
3. Implement the behavior.
4. Refactor while tests remain green.
5. Run API and web/mobile tests plus lint/security checks.
6. Document schema/API/privacy changes.

Pull requests that add behavior without tests should not be merged unless the change is documentation-only or the PR explains a narrow exception.

Never commit real national IDs, credit reports, message bodies, call histories, contact books, passwords, tokens, private keys, or other production evidence.
