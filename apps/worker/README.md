# Worker

Planned responsibilities:

- source sync jobs;
- SMTP/OAuth request sending;
- IMAP or signed inbound-mail processing;
- Playwright automation in an isolated process/container;
- deadline/recheck scheduling;
- report generation.

The MVP uses a SQL-backed job table. Redis/Celery is deferred until concurrency justifies it.
