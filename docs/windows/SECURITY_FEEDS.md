# Security Feeds

The feed catalogue is declared in `downstream/security/security-feeds.json`. The default catalogue contains official ClamAV CVD/CLD definitions, local curated YARA rules, and local SHA-256 reputation. No feed uploads files, matched content, prompts, or conversation data.

## ClamAV updates

`hermes security update` invokes the installed `freshclam` executable with a unique staging directory inside the active profile. The candidate update must contain nontrivial CVD or CLD files. When `sigtool` is present, every candidate database must also pass `sigtool --info`.

Only validated candidates are activated. The current directory is moved to `previous`, staging is moved to `current`, and a failed activation restores the former current directory. Download, validation, and activation failures update feed state without replacing the last valid database.

## YARA and hash reputation

YARA rules are loaded from `<HERMES_HOME>/security/feeds/yara`. The core tier should contain curated, high-confidence rules; broader experimental rules must declare `meta.hermes_tier = "extended"` and cannot trigger automatic quarantine by themselves.

Hash reputation uses lowercase hexadecimal SHA-256 as its canonical identifier in the `malware_hashes` table. Optional external feeds may populate only documented hashes and indicators. Sample download, sample retention, file upload, and default remote hash lookup are outside this subsystem.

## Privacy and rollback

Feed state records source identifiers, versions, timestamps, validation results, and bounded updater output. It does not store credentials or file contents. The previous ClamAV database remains available for operator rollback after a successful activation.
