"""Point d'entrée Stormer."""

from stormer.app import main
from stormer.setup_config import is_first_run, load_profile
from stormer.setup_wizard import run_setup_wizard


def entry() -> None:
    if is_first_run():
        profile = run_setup_wizard(force=True)
        if profile is None:
            return
    else:
        load_profile()
    main()


if __name__ == "__main__":
    entry()
