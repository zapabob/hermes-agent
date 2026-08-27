# Upgrade and rollback

Hermes Agent Windows Workstation Edition updates only from
`zapabob/hermes-agent-windows`. Official upstream is an integration input; it
is not an update authority for an installed downstream workstation.

## Channels

`stable` accepts only an exact commit that passed every required Windows gate,
has recorded artifact hashes and the frozen upstream SHA, and has generated
provenance. `preview` is for candidate validation and may be incomplete. Change
channels deliberately and read the manifest before installing a preview.

## Upgrade

Download the newer installer and its `SHA256SUMS.txt` from the same downstream
release, verify the hash, close Hermes, and run the installer. The NSIS product
GUID remains continuous with the prior Desktop identity so an existing
installation is upgraded rather than forked into a second product.

Profile data, configuration, memory, and sessions live outside the application
directory and are preserved by the upgrade path. The qualification workflow
also installs a prior build, writes a profile sentinel, upgrades it, launches
the result, and verifies that the sentinel survived.

Portable users should stop Hermes, retain the previous extracted directory,
extract the new archive into a new directory, and launch it against the same
profile. Do not overlay a running portable directory.

## Frozen upstream baseline

Every Windows release records one exact Nous Research commit. A later upstream
commit does not enter an installed release until a new downstream train is
qualified. The CLI version output and release manifest show both downstream
and upstream identities.

## Rollback

Keep the previous verified installer or portable directory and its hash file.
Stop Hermes and the Go watchdog, uninstall only the application when necessary,
then install the previous downstream version. Do not delete `HERMES_HOME`.

If a schema migration or profile issue is suspected, make a profile backup
before rollback. Restore only from a snapshot produced for that profile and
release train. Application rollback and profile-data restoration are separate
operations.
