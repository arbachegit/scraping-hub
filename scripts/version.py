#!/usr/bin/env python3
"""
Script de Versionamento Automático
Baseado no skill-versioning do iconsai-skills

Formato: MAJOR.DEPLOY_COUNT.YEAR
Exemplo: 1.60.2026

Uso:
    python scripts/version.py --deploy    # Incrementa contador de deploy
    python scripts/version.py --major     # Incrementa versão major
    python scripts/version.py --show      # Mostra versão atual
    python scripts/version.py --set X.Y.Z # Define versão específica
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Caminhos
PROJECT_ROOT = Path(__file__).parent.parent
VERSION_FILE = PROJECT_ROOT / "VERSION"
PACKAGE_JSON = PROJECT_ROOT / "package.json"
CHANGELOG_FILE = PROJECT_ROOT / "CHANGELOG.md"


def read_version() -> tuple[int, int, int]:
    """Lê a versão atual do arquivo VERSION."""
    if not VERSION_FILE.exists():
        return 1, 0, datetime.now().year

    content = VERSION_FILE.read_text().strip()
    parts = content.split(".")

    if len(parts) != 3:
        print(f"⚠️  Formato inválido: {content}. Usando 1.0.{datetime.now().year}")
        return 1, 0, datetime.now().year

    try:
        major = int(parts[0])
        deploy_count = int(parts[1])
        year = int(parts[2])
        return major, deploy_count, year
    except ValueError:
        return 1, 0, datetime.now().year


def write_version(major: int, deploy_count: int, year: int) -> str:
    """Escreve a nova versão no arquivo VERSION."""
    version_str = f"{major}.{deploy_count}.{year}"
    VERSION_FILE.write_text(f"{version_str}\n")
    return version_str


def update_package_json(version: str) -> None:
    """Atualiza a versão no package.json se existir."""
    if not PACKAGE_JSON.exists():
        return

    try:
        data = json.loads(PACKAGE_JSON.read_text())
        data["version"] = version
        PACKAGE_JSON.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
        print(f"📦 package.json atualizado para {version}")
    except (json.JSONDecodeError, KeyError):
        pass


def update_changelog(version: str, change_type: str) -> None:
    """Adiciona entrada no CHANGELOG.md."""
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"\n## [{version}] - {date_str}\n- {change_type.capitalize()}\n"

    if CHANGELOG_FILE.exists():
        content = CHANGELOG_FILE.read_text()
        # Insere após o título
        if "# Changelog" in content:
            content = content.replace("# Changelog\n", f"# Changelog\n{entry}", 1)
        else:
            content = entry + content
    else:
        content = f"# Changelog\n{entry}"

    CHANGELOG_FILE.write_text(content)
    print("📝 CHANGELOG.md atualizado")


def cmd_show() -> None:
    """Mostra a versão atual."""
    major, deploy_count, year = read_version()
    version = f"{major}.{deploy_count}.{year}"
    print(f"📌 Versão atual: {version}")


def cmd_deploy() -> None:
    """Incrementa o contador de deploy."""
    major, deploy_count, year = read_version()
    current_year = datetime.now().year

    # Se mudou o ano, reseta o contador
    if year != current_year:
        deploy_count = 0
        year = current_year

    deploy_count += 1
    version = write_version(major, deploy_count, year)

    update_package_json(version)
    update_changelog(version, "Deploy automático")

    print(f"🚀 Nova versão: {version}")


def cmd_major() -> None:
    """Incrementa a versão major."""
    major, deploy_count, year = read_version()
    current_year = datetime.now().year

    major += 1
    deploy_count = 0
    year = current_year

    version = write_version(major, deploy_count, year)

    update_package_json(version)
    update_changelog(version, "Breaking change - Major version")

    print(f"🎉 Nova versão major: {version}")


def cmd_set(version_str: str) -> None:
    """Define uma versão específica."""
    parts = version_str.split(".")
    if len(parts) != 3:
        print("❌ Formato inválido. Use: MAJOR.DEPLOY.YEAR (ex: 2.1.2026)")
        sys.exit(1)

    try:
        major = int(parts[0])
        deploy_count = int(parts[1])
        year = int(parts[2])
    except ValueError:
        print("❌ Valores devem ser numéricos")
        sys.exit(1)

    version = write_version(major, deploy_count, year)
    update_package_json(version)

    print(f"✅ Versão definida: {version}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gerenciador de versão do projeto",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python scripts/version.py --show
  python scripts/version.py --deploy
  python scripts/version.py --major
  python scripts/version.py --set 2.1.2026
        """,
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--show", action="store_true", help="Mostra versão atual")
    group.add_argument("--deploy", action="store_true", help="Incrementa deploy counter")
    group.add_argument("--major", action="store_true", help="Incrementa major version")
    group.add_argument("--set", type=str, metavar="X.Y.Z", help="Define versão específica")

    args = parser.parse_args()

    if args.show:
        cmd_show()
    elif args.deploy:
        cmd_deploy()
    elif args.major:
        cmd_major()
    elif args.set:
        cmd_set(args.set)


if __name__ == "__main__":
    main()
