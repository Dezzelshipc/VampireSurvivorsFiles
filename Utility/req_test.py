"""Test availability of required packages."""
import asyncio
import sys
from importlib.metadata import version, PackageNotFoundError
from pathlib import Path

from pip._internal.network.session import PipSession
from pip._internal.req.constructors import install_req_from_parsed_requirement
from pip._internal.req.req_file import parse_requirements

_REQUIREMENTS_PATH = Path(__file__).parent.with_name("requirements.txt")


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
        return False
    else:
        print("All packages up to date")
    return True



def check_pydub():
    from pydub.utils import which
    files = ("ffmpeg", "avconv")
    return any([which(f) for f in files])

async def check_pydub_defer():
    return await asyncio.to_thread(check_pydub)


if __name__ == "__main__":
    if not test_requirements():
        input()
