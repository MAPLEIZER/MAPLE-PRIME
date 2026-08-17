# Security Policy

KDR may process extremely sensitive identity and credit information. Do not disclose vulnerabilities involving authentication, authorization, encryption, secret handling or user evidence in a public issue before maintainers can assess the impact.

## Supported status

The repository is pre-alpha. It is suitable for development and local experimentation, not for storing other users' sensitive data as a public service.

## Never include in issues

- national ID/passport images or numbers;
- real credit reports;
- email/SMTP/IMAP credentials;
- OAuth refresh tokens;
- real evidence attachments containing PII;
- encryption keys.

## Security design documents

See `docs/THREAT-MODEL.md` and the hosted go/no-go gate in `docs/ROADMAP.md`.
