"""Point d'entrée Stormer."""

from stormer.app import main
from stormer.setup_config import HardwareProfile, is_first_run, load_profile
from stormer.setup_wizard import run_setup_wizard


def entry() -> None:
    profile: HardwareProfile | None
    if is_first_run():
        profile = run_setup_wizard(force=True)
        if profile is None:
            return
    else:
        profile = load_profile()

    main(profile)


if __name__ == "__main__":
    entry()
