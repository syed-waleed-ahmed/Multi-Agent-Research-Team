# Security Policy

## Supported versions

Security fixes are provided for the latest `1.0.x` release line.

| Version | Supported |
| --- | --- |
| 1.0.x | Yes |
| < 1.0 | No |

## Reporting a vulnerability

Please do not open a public issue for security vulnerabilities.

Report suspected vulnerabilities privately using one of the following:

- GitHub's private vulnerability reporting: open the repository's **Security**
  tab and choose **Report a vulnerability**.
- Email the maintainer at **syedwaleedahmed9@gmail.com** with a description of
  the issue, steps to reproduce, and any relevant logs (with secrets redacted).

You can expect an acknowledgement within a few business days. Once the issue is
confirmed, a fix will be prepared and released, and the report will be credited
unless you prefer to remain anonymous.

## Handling secrets

This application requires API credentials (`GROQ_API_KEY`, `SERPER_API_KEY`).
To keep them safe:

- Store credentials only in a local `.env` file. This file is git-ignored and
  must never be committed. Commit only `.env.example`, which contains
  placeholders.
- Never paste real keys into issues, pull requests, logs, or screenshots.
- Rotate any key that may have been exposed. Groq keys can be rotated at
  <https://console.groq.com/keys> and Serper keys at
  <https://serper.dev/api-key>.
- The application reads credentials from the environment at runtime and does not
  log them.

## Dependencies

Third-party dependencies (CrewAI, LiteLLM, and their transitive packages) are
pinned to tested ranges in `pyproject.toml`. Keep them updated and review
security advisories for the packages you deploy.
