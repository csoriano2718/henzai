# Building henzai for COPR

This document describes how to build and publish henzai packages to COPR.

## Prerequisites

1. **COPR account**: Create at https://copr.fedorainfracloud.org/
2. **copr-cli**: Install with `sudo dnf install copr-cli`
3. **Configure copr-cli**: Follow https://copr.fedorainfracloud.org/api/

## Quick Build

The COPR repository is already configured at:
https://copr.fedorainfracloud.org/coprs/csoriano/henzai/

### Trigger a build from Git

COPR is configured to build automatically from the main branch. To trigger manually:

```bash
# From the COPR web interface:
# 1. Go to https://copr.fedorainfracloud.org/coprs/csoriano/henzai/
# 2. Click "Packages" → "henzai" → "Rebuild"
```

### Build locally and submit

```bash
# Create tarball and source RPM
make srpm

# Submit to COPR
copr-cli build csoriano/henzai henzai-0.1.0-1.*.src.rpm
```

## What Gets Built

The RPM package includes:
- **henzai-daemon**: Python daemon for LLM interaction
- **GNOME Shell extension**: UI and D-Bus client
- **Systemd services**: ramalama.service and henzai-daemon.service
- **D-Bus activation**: org.gnome.henzai.service
- **Documentation**: README.md and LICENSE

## Post-Install

Users need to:
1. Enable the systemd user services
2. Restart GNOME Shell or log out/in
3. Enable the extension with gnome-extensions

See the main README.md for detailed instructions.

## Updating the Version

1. Update `Version:` in `henzai.spec`
2. Update `VERSION` in `Makefile`
3. Update version in `.copr/Makefile`
4. Add changelog entry in `henzai.spec`
5. Commit and push
6. Trigger COPR build

## Troubleshooting

### Build fails in COPR

Check the build logs at:
https://copr.fedorainfracloud.org/coprs/csoriano/henzai/builds/

Common issues:
- Missing BuildRequires in spec
- Incorrect file paths in %files section
- Python module not found (check setup.py)

### Testing locally before COPR

```bash
# Build in mock (Fedora 42)
mock -r fedora-42-x86_64 henzai-0.1.0-1.*.src.rpm

# Build in mock (Fedora 43)
mock -r fedora-43-x86_64 henzai-0.1.0-1.*.src.rpm
```

## References

- COPR Documentation: https://docs.pagure.org/copr.copr/
- RPM Packaging Guide: https://docs.fedoraproject.org/en-US/packaging-guidelines/
- Fedora Python Guidelines: https://docs.fedoraproject.org/en-US/packaging-guidelines/Python/

