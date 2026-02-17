#!/usr/bin/env python3
"""
SKILL: skill-versioning
Gerencia versionamento do projeto iconsai-scraping.

Formato: MAJOR.DEPLOY_COUNT.YEAR
- MAJOR: Versao principal (incrementa em breaking changes)
- DEPLOY_COUNT: Numero sequencial de deploys
- YEAR: Ano atual

Uso:
    python script.py --deploy    # Incrementa DEPLOY_COUNT (obrigatorio em cada deploy)
    python script.py --major     # Incrementa MAJOR (breaking changes)
    python script.py --show      # Mostra versao atual
    python script.py --set X.Y.Z # Define versao especifica
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

# Diretorio raiz do projeto
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
VERSION_FILE = PROJECT_ROOT / "VERSION"
CHANGELOG_FILE = PROJECT_ROOT / "CHANGELOG.md"

CURRENT_YEAR = datetime.now().year


def read_version() -> tuple[int, int, int]:
    """Le a versao atual do arquivo VERSION. Formato: MAJOR.DEPLOY_COUNT.YEAR"""
    if not VERSION_FILE.exists():
        print(f"Arquivo VERSION nao encontrado. Criando com 1.1.{CURRENT_YEAR}...")
        write_version(1, 1, CURRENT_YEAR)
        return (1, 1, CURRENT_YEAR)

    content = VERSION_FILE.read_text().strip()
    match = re.match(r'^(\d+)\.(\d+)\.(\d+)$', content)

    if not match:
        print(f"Formato de versao invalido: {content}. Usando 1.1.{CURRENT_YEAR}...")
        return (1, 1, CURRENT_YEAR)

    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def write_version(major: int, deploy_count: int, year: int) -> str:
    """Escreve a nova versao no arquivo VERSION."""
    version_string = f"{major}.{deploy_count}.{year}"

    # Atualizar VERSION
    VERSION_FILE.write_text(version_string + "\n")
    print(f"VERSION atualizado: {version_string}")

    return version_string


def increment_major() -> str:
    """Incrementa o numero MAJOR e reseta DEPLOY_COUNT para 1."""
    major, deploy_count, year = read_version()
    # Ao incrementar major, resetamos o contador de deploys
    new_version = write_version(major + 1, 1, CURRENT_YEAR)
    print(f"MAJOR incrementado: V{new_version}")
    return new_version


def increment_deploy() -> str:
    """Incrementa o contador de deploys."""
    major, deploy_count, year = read_version()
    # Se mudou o ano, podemos opcionalmente resetar ou continuar
    # Vamos continuar incrementando
    return write_version(major, deploy_count + 1, CURRENT_YEAR)


def show_version() -> str:
    """Mostra a versao atual."""
    major, deploy_count, year = read_version()
    version_string = f"{major}.{deploy_count}.{year}"
    print(f"Versao atual: V{version_string}")
    print(f"  - Major: {major}")
    print(f"  - Deploy Count: {deploy_count}")
    print(f"  - Ano: {year}")
    return version_string


def set_version(version_str: str) -> str:
    """Define uma versao especifica."""
    match = re.match(r'^(\d+)\.(\d+)\.(\d+)$', version_str)
    if not match:
        print(f"Erro: Formato de versao invalido: {version_str}")
        print("Use o formato: MAJOR.DEPLOY_COUNT.YEAR (ex: 2.15.2026)")
        sys.exit(1)

    new_version = write_version(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    print(f"Versao definida: V{new_version}")
    return new_version


def deploy_version() -> str:
    """
    Incrementa versao para deploy (incrementa DEPLOY_COUNT).
    Esta funcao DEVE ser chamada em cada deploy.
    """
    print("=" * 60)
    print("VERSIONAMENTO AUTOMATICO - DEPLOY")
    print("=" * 60)

    old_major, old_deploy, old_year = read_version()
    old_version = f"{old_major}.{old_deploy}.{old_year}"

    # Incrementa DEPLOY_COUNT para cada deploy
    new_version = increment_deploy()

    print("-" * 60)
    print(f"Versao anterior: V{old_version}")
    print(f"Nova versao:     V{new_version}")
    print("-" * 60)

    # Registrar no changelog
    log_deploy(old_version, new_version)

    print("=" * 60)
    print(f"Deploy versao V{new_version} pronto!")
    print("=" * 60)

    return new_version


def log_deploy(old_version: str, new_version: str):
    """Registra o deploy no changelog."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log_entry = f"\n## [V{new_version}] - {timestamp}\n### Deploy #{new_version.split('.')[1]}\n- Versao incrementada de V{old_version} para V{new_version}\n"

    if CHANGELOG_FILE.exists():
        content = CHANGELOG_FILE.read_text()
        # Inserir apos o cabecalho
        if "# Changelog" in content:
            parts = content.split("# Changelog", 1)
            new_content = parts[0] + "# Changelog" + log_entry + parts[1] if len(parts) > 1 else content + log_entry
        else:
            new_content = content + log_entry
    else:
        new_content = f"# Changelog\n\nTodas as mudancas notaveis do projeto iconsai-scraping.\n{log_entry}"

    CHANGELOG_FILE.write_text(new_content)
    print("CHANGELOG.md atualizado")


def main():
    parser = argparse.ArgumentParser(
        description='Gerenciador de Versionamento - iconsai-scraping',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Formato: MAJOR.DEPLOY_COUNT.YEAR

Exemplos:
  python script.py --deploy      # OBRIGATORIO em cada deploy (incrementa contador)
  python script.py --show        # Ver versao atual
  python script.py --major       # Nova versao major (breaking changes)
  python script.py --set 2.1.2026 # Definir versao especifica
        """
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--deploy', action='store_true',
                       help='Incrementar contador de deploys (OBRIGATORIO em cada deploy)')
    group.add_argument('--major', action='store_true',
                       help='Incrementar MAJOR (breaking changes, reseta contador)')
    group.add_argument('--show', action='store_true',
                       help='Mostrar versao atual')
    group.add_argument('--set', type=str, metavar='X.Y.Z',
                       help='Definir versao especifica (MAJOR.DEPLOY_COUNT.YEAR)')

    args = parser.parse_args()

    if args.deploy:
        deploy_version()
    elif args.major:
        increment_major()
    elif args.show:
        show_version()
    elif args.set:
        set_version(args.set)


if __name__ == '__main__':
    main()
