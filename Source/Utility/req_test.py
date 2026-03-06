"""Test availability of required packages."""
import asyncio
import subprocess
import sys
from importlib.metadata import version, PackageNotFoundError

from pip._internal.network.session import PipSession
from pip._internal.req.constructors import install_req_from_parsed_requirement
from pip._internal.req.req_file import parse_requirements

try:
    from Source.Utility.utility import _find_main_py_file
    from Source.Config.config import Config, CfgKey
except ImportError:
    from utility import _find_main_py_file
    from config import Config, CfgKey

_REQUIREMENTS_PATH = _find_main_py_file().with_name("requirements.txt")


def test_requirements():
    """Test that each required package is available."""
    # Ref: https://stackoverflow.com/a/45474387/
    not_satisfied = []

    session = PipSession()
    requirements = parse_requirements(str(_REQUIREMENTS_PATH), session)
    for requirement in requirements:
        req_to_install = install_req_from_parsed_requirement(requirement)
        req_to_install.check_if_exists(use_user_site=False)
        if not req_to_install.satisfied_by:
            data = {"name": req_to_install.name, "req": req_to_install.req.specifier}
            try:
                upd = {"current": version(req_to_install.name)}
            except PackageNotFoundError:
                upd = {"current": "Not found"}

            data.update(upd)
            not_satisfied.append(data)

    if not_satisfied:
        print("!!! Packages not installed or outdated:", file=sys.stderr)
        for req in not_satisfied:
            print(f"!!!   {req["name"]} - Current: {req["current"]}, Required: {req["req"]}", file=sys.stderr)
        print("!!! Run 'pip install -r requirements.txt' to update and install packages", file=sys.stderr)
    else:
        print("All packages up to date")

    is_tkinter = True
    try:
        import tkinter
    except ImportError:
        is_tkinter = False
        print("!!! Module 'tkinter' not installed")

    return is_tkinter and not bool(not_satisfied)


def check_pydub():
    from pydub.utils import which
    files = ("ffmpeg", "avconv")
    return any([which(f) for f in files])


async def check_pydub_defer():
    return await asyncio.to_thread(check_pydub)


RIPPER_VERSION_MINIMAL = (1, 3, 8)


def check_ripper_version():
    def version_to_str(ver: tuple[int, int, int]):
        return '.'.join(map(str, ver))

    ripper = ""
    try:
        ripper = next(Config[CfgKey.RIPPER].rglob("AssetRippe*.exe"))
    except StopIteration:
        pass

    if ripper:
        result = subprocess.run([ripper, "--version"], capture_output=True, text=True)
        result = result.stdout.strip().split(" ")[1].split("+")[0]
        vers = tuple(map(int, result.split(".")))
        if vers < RIPPER_VERSION_MINIMAL:
            print(
                f"!!! RIPPER version is outdated. Current: {version_to_str(vers)}, Required: {version_to_str(RIPPER_VERSION_MINIMAL)}+",
                file=sys.stderr)
    else:
        print(f"! Ripper not found for automatic ripping: required version {version_to_str(RIPPER_VERSION_MINIMAL)}+",
              file=sys.stderr)


if __name__ == "__main__":
    check_ripper_version()

    if not test_requirements():
        input()
