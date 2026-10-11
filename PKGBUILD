# Maintainer: lostflam <LOSTFlam@users.noreply.github.com>

pkgname=flamfetch
pkgver=1.8.3
pkgrel=1
pkgdesc="Fiery animated system fetch with live flame and glitch effects"
arch=('any')
url="https://github.com/LOSTFlam/FlamFetch"
license=('MIT')
depends=('python' 'python-pyfiglet')
optdepends=('hyprland: display resolution detection'
            'gsettings: GTK theme detection'
            'nvidia-utils: GPU driver/temperature'
            'lm_sensors: CPU temperature')
source=("${pkgname}-${pkgver}.tar.gz::https://github.com/LOSTFlam/FlamFetch/archive/v${pkgver}.tar.gz")
sha256sums=('SKIP')

package() {
    cd "${srcdir}/FlamFetch-${pkgver}"

    # Основной скрипт
    install -Dm755 flamfetch/flamfetch.py "${pkgdir}/usr/bin/flamfetch"

    # Документация
    install -Dm644 README.md "${pkgdir}/usr/share/doc/${pkgname}/README.md"
    install -Dm644 LICENSE "${pkgdir}/usr/share/licenses/${pkgname}/LICENSE"
}
