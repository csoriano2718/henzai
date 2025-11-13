Name:           henzai
Version:        0.1.2
Release:        1%{?dist}
Summary:        Local AI integrated into GNOME Shell

License:        GPL-3.0
URL:            https://github.com/csoriano2718/henzai
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch

# Python dependencies for the daemon
Requires:       python3
Requires:       python3-requests
Requires:       python3-dasbus
Requires:       python3-gobject

# GNOME Shell for the extension
Requires:       gnome-shell >= 45

# Ramalama for LLM inference (required)
Requires:       ramalama

# Systemd for service management
Requires:       systemd

BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
BuildRequires:  systemd-rpm-macros

%description
henzai is local AI integrated into GNOME Shell, providing seamless access to
local LLMs through Ramalama. Features include streaming responses, reasoning
mode with visual thinking process, real-time model switching, generation
cancellation, and synchronized settings across UI and preferences.

Assisted-by: Generated (vibe-coded) by Cursor AI with Claude Sonnet 4.5

%prep
%autosetup -n %{name}-%{version}

%build
# Build Python daemon
cd henzai-daemon
%py3_build

%install
# Install Python daemon
cd henzai-daemon
%py3_install

# Install GNOME Shell extension
mkdir -p %{buildroot}%{_datadir}/gnome-shell/extensions/henzai@csoriano
cp -r ../henzai-extension/* %{buildroot}%{_datadir}/gnome-shell/extensions/henzai@csoriano/

# Install systemd user services
mkdir -p %{buildroot}%{_userunitdir}
install -m 644 ../henzai-daemon/systemd/henzai-daemon.service %{buildroot}%{_userunitdir}/
install -m 644 ../henzai-daemon/systemd/ramalama.service %{buildroot}%{_userunitdir}/

# Install D-Bus service activation file
mkdir -p %{buildroot}%{_datadir}/dbus-1/services
install -m 644 ../henzai-daemon/dbus/org.gnome.henzai.service %{buildroot}%{_datadir}/dbus-1/services/

# Install documentation
mkdir -p %{buildroot}%{_docdir}/%{name}
install -m 644 ../README.md %{buildroot}%{_docdir}/%{name}/
install -m 644 ../LICENSE %{buildroot}%{_docdir}/%{name}/

%post
# Use systemd macros to enable user services
# These will be enabled for users who install the package
%systemd_user_post ramalama.service
%systemd_user_post henzai-daemon.service

# Enable GNOME Shell extension for the user running the install
# This works when user installs via 'dnf install' (not during sudo dnf)
if [ -n "$SUDO_USER" ] && [ "$SUDO_USER" != "root" ]; then
    # Get the actual user's runtime directory
    USER_HOME=$(getent passwd "$SUDO_USER" | cut -d: -f6)
    
    # Enable the extension using gnome-extensions
    sudo -u "$SUDO_USER" DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$(id -u $SUDO_USER)/bus" \
        gnome-extensions enable henzai@csoriano 2>/dev/null || true
fi

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║         henzai installed successfully!                     ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo ""
echo "1. Restart your computer (or log out and back in)"
echo "   This will:"
echo "   - Start the services automatically"
echo "   - Load the GNOME Shell extension"
echo ""
echo "2. Press Super+A to open henzai"
echo ""
echo "Note: Services are enabled and will auto-start on every login."
echo ""

%preun
%systemd_user_preun ramalama.service
%systemd_user_preun henzai-daemon.service

%postun
%systemd_user_postun ramalama.service
%systemd_user_postun henzai-daemon.service

%files
# Python daemon
%{python3_sitelib}/henzai/
%{python3_sitelib}/henzai-*.egg-info/
%{python3_sitelib}/tests/

# Daemon binary
%{_bindir}/henzai-daemon

# GNOME Shell extension
%{_datadir}/gnome-shell/extensions/henzai@csoriano/

# Systemd services
%{_userunitdir}/henzai-daemon.service
%{_userunitdir}/ramalama.service

# D-Bus service
%{_datadir}/dbus-1/services/org.gnome.henzai.service

# Documentation
%{_docdir}/%{name}/

%changelog
* Thu Nov 13 2025 Carlos Soriano <csoriano@redhat.com> - 0.1.2-1
- Change keyboard shortcut from Super+H to Super+A (fix conflict with minimize)
- Consolidate UI design documentation
- Fix GitHub Pages media paths for website
- Assisted-by: Generated (vibe-coded) by Cursor AI with Claude Sonnet 4.5

* Thu Nov 13 2025 Carlos Soriano <csoriano@redhat.com> - 0.1.1-1
- Update welcome message example (Zeno's dichotomy paradox)
- Improve UX with better loading states and disabled inputs
- Faster model status polling (1s instead of 2s)
- Add demo videos and screenshots to website
- Assisted-by: Generated (vibe-coded) by Cursor AI with Claude Sonnet 4.5

* Thu Nov 13 2025 Carlos Soriano <csoriano@redhat.com> - 0.1.0-1
- MVP Release (stable foundation)
- Fix critical opacity bug (0-255 scale not 0.0-1.0)
- Add daemon connection checks to prevent crashes
- Improve polling interval (2s instead of 500ms)
- Complete working implementation with all features
- Single clean commit history for stable foundation
- Comprehensive documentation in AGENTS.md
- Assisted-by: Generated (vibe-coded) by Cursor AI with Claude Sonnet 4.5

