# Security Policy

## Security Maintainer

**Shengqinchu** ([@Shengqinchu](https://github.com/Shengqinchu)) — sole maintainer and security contact for this project.

## Reporting a Vulnerability

If you discover a security vulnerability in PinDou, please report it responsibly:

- **Email:** chus25@mcmaster.ca
- **Response time:** I aim to acknowledge reports within 48 hours and provide a fix or mitigation within 7 days.

Please do **not** open a public GitHub issue for security vulnerabilities.

## Scope

This policy covers:
- The PinDou backend API (`06_backend/`)
- The WeChat mini program frontend (`05_frontend/`)
- The Studio management application (`05_studio/`)
- Server infrastructure and deployment configurations (`07_ops/`)

## Security Measures

- Production access is restricted via SSH key authentication with fail2ban
- Inbound firewall limits exposed ports to SSH only; application traffic runs through Cloudflare Tunnel
- Nightly automated backups with integrity verification
- Unattended security updates enabled
