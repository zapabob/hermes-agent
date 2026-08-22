# Python CI Contract Repair

Date: 2026-08-23

## Scope

The fork CI run `32587946310` for source `bcde661fd77e306d530a1d21f27331ec0e140ae2` failed in the Python test job `97067586195` with nine failures across six contract areas. The repair is limited to restoring those contracts while retaining the official upstream behavior for the Parallel failover path.

## Changes

- Nous automatic free fallback now returns only explicit `:free` or `-free` model IDs and retains the static suffix-qualified fallback when the live catalog provides no such IDs.
- Hypura publishes its configurable local base URL through the provider catalog, and profile-derived provider definitions separate base URL variables from API-key variables.
- The built-in CLI startup gate includes the registered `harness` command.
- The web backend selection ladder includes the importable `ddgs` backend after the other free search choices, matching `upstream/main`.
- Parallel keyless tests patch the current shared failover seam instead of the removed direct helper seam.
- The Hermes plugin integration skill metadata meets the repository description and related-skill validation rules.

## Verification record

Before repair, the focused local suite reproduced `1301 passed, 9 failed`. After repair, the same focused suite passed with `1310 passed, 1 warning` in 59.49 seconds. The exact pushed SHA and cloud CI result are recorded in the final handoff after the push completes.

No credentials, personal data, generated binaries, or runtime state are included.
