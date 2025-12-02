# Maintainer: Jona <your@email.com>
pkgname=exitnodetoggle
pkgver=1.0.0
pkgrel=1
pkgdesc="Tailscale Exit Node Toggle GUI"
arch=('x86_64')
url="https://github.com/yourusername/ExitNodeToggle"
license=('MIT')
depends=('tailscale' 'qt5-base' 'tk' 'glibc')
makedepends=('python' 'python-pip' 'python-virtualenv' 'binutils')
source=('main_linux.py' 'requirements.txt' 'config.linux.json' 'config.json' 'icon-source.svg' 'exitnodetoggle.desktop')
sha256sums=('SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP')

build() {
    echo "Setting up virtual environment for build..."
    python -m venv venv
    source venv/bin/activate
    
    echo "Installing build dependencies..."
    pip install -r requirements.txt
    pip install pyinstaller
    
    echo "Building binary..."
    # Note: We don't bundle config.json inside the binary for the system package
    # We will install a default config to /etc/ or let the app create one/warn user
    pyinstaller --onefile --windowed --hidden-import PyQt5 --name "exitnodetoggle" --add-data "config.json:." main_linux.py
}

package() {
    # Install binary
    install -Dm755 "dist/exitnodetoggle" "$pkgdir/usr/bin/exitnodetoggle"
    
    # Install desktop file
    install -Dm644 "exitnodetoggle.desktop" "$pkgdir/usr/share/applications/exitnodetoggle.desktop"
    
    # Install icon
    install -Dm644 "icon-source.svg" "$pkgdir/usr/share/icons/hicolor/scalable/apps/exitnodetoggle.svg"
    
    # Install default config to doc (user needs to set it up)
    install -Dm644 "config.linux.json" "$pkgdir/usr/share/doc/$pkgname/config.example.json"
    
    # Create license file (MIT)
    # install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
}
