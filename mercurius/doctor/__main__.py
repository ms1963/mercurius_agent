import sys
from mercurius.doctor import run_doctor

if __name__ == "__main__":
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    rep = run_doctor(verbose=verbose)
    sys.exit(0 if rep.overall_status in ("HEALTHY", "DEGRADED") else 1)
