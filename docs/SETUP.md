# Setting up JSS-Scripts

These are shell scripts for Jamf Pro, almost all by [Balmes Pavlov (bp88)](https://github.com/bp88/JSS-Scripts). This
fork is a 2020 snapshot. Before you use any of them, check [upstream](https://github.com/bp88/JSS-Scripts): it has
newer versions, including Apple silicon support.

Setting one up means uploading it to Jamf Pro, filling in its parameters and scoping a policy. Budget about 15 minutes
per script, plus a test Mac.

**What's tested, honestly:** a fresh Ubuntu runner checks every week, in
[`setup-check`](../.github/workflows/setup-check.yml), that each script parses with the shell named on its first line
and that the LaunchDaemon is a valid property list. That's all. Nothing here runs on a Mac or against Jamf in CI, and
nothing in this fork has been run against a Mac as part of this guide. Treat every script as untested until it has
run on your test Mac.

## What you need

- A Jamf Pro server, admin rights to add scripts and policies, and Macs enrolled in it.
- Jamf Helper, at `/Library/Application Support/JAMF/bin/jamfHelper.app`. The Jamf agent installs it.
- A test Mac and a smart or static group containing only it.
- For `TCC.db Modifier.sh`: Full Disk Access for whatever runs it (the Jamf agent, through a PPPC profile).

## 1. Get the scripts and check they parse

```sh setup-check
sudo apt-get update -qq && sudo apt-get install -y -qq zsh
git clone -q https://github.com/casareanderson/JSS-Scripts.git
cd JSS-Scripts
for f in *.sh homebrew.sh-master/*.sh; do
  shell=$(head -1 "$f" | sed 's/^\xEF\xBB\xBF//; s/^#!//; s/ .*//')
  printf '%-36s %-10s ' "$f" "$shell"
  "$(basename "$shell")" -n "$f" && echo "parses"
done
python3 -c "import plistlib; d = plistlib.load(open('com.company.reconafterupdate', 'rb')); print(d['Label'], 'is a valid plist')"
```

Each script is checked with its own shell: `AppleSoftwareUpdate.sh`, `TCC.db Modifier.sh` and `tcc_reset.sh` are zsh,
the rest are bash.

Two things the check prints that you should know about:

- `OS_Upgrade.sh` gets `warning: here-document at line 786 delimited by end-of-file (wanted 'EOD')` from bash 5. The
  here-document ends with `EOD)"` on one line, which modern bash warns about. It still parses (the check passes), and
  macOS's `/bin/bash` is 3.2. I haven't run it on a Mac, so check that the "quit all apps" step behaves on yours.
- `homebrew.sh-master/homebrew-3.2.sh` starts with a UTF-8 byte-order mark before `#!/bin/bash`, which can stop macOS
  reading the shebang. The check strips it to find the shell; you should strip it from the file before uploading:
  `sed -i '' $'1s/^\xEF\xBB\xBF//' homebrew.sh-master/homebrew-3.2.sh` on a Mac.

## 2. Read the header

Every script lists its Jamf parameters, defaults and exit codes in the comments at the top. Read it before uploading.
For example, `AppleSoftwareUpdate.sh`:

| parameter | what it does | default |
|---|---|---|
| `$4` | number of postponements allowed | `3` |
| `$5` | seconds the dialog stays up | `900` |
| `$6` | contact shown in the messages (email, number or department) | `IT` |
| `$7` | path to a custom icon | Apple Software Update's icon |

And its exit codes: `11` no power, `12` update failed, `13` FileVault still encrypting, `14` bad deferral type,
`15` not enough disk space.

A few settings are variables at the top of the file that you edit before uploading, not parameters:

| script | variable | change it to |
|---|---|---|
| `jamfHelperScreen.sh` | `it_contact` | your contact; it ships as `IT@contoso.com` |
| `JamfDeprecationNotifier.sh` | `MaxDeferralAttempts`, `MaxIdleTime`, `MoreInfoURL`, `DelayOptions` | your deferral limit, idle cut-off, "More Info" link and delay choices |

## 3. Upload it to Jamf Pro

Not testable outside Jamf.

1. **Settings → Computer Management → Scripts → New.**
2. **General:** give it a name you'll recognise in a policy log.
3. **Script:** paste the file's contents.
4. **Options → Parameter Labels:** copy the labels from the header, e.g. `$4` = "Postponements allowed". Labels make
   the policy screen readable later.
5. Save.

## 4. Make a policy and test it on one Mac

1. **Computers → Policies → New.** Add the script, and fill in the parameter values (leave optional ones blank to use
   the defaults).
2. **Scope:** your test group only.
3. **Trigger:** Recurring Check-in, or a custom trigger so you can run it on demand:
   `sudo jamf policy -event your-trigger` on the test Mac.
4. Run it, then read the policy log in Jamf Pro. Each script logs what it decided and exits with a code from its
   header.

Widen the scope only after it has done the right thing on the test Mac, including the case where a user is logged in
and the case where nobody is.

## 5. The LaunchDaemon

`com.company.reconafterupdate` runs `jamf recon` once after a macOS update, then removes itself. Deploy it to
`/Library/LaunchDaemons/` (a package, or a script in the update policy) before the update runs. It checks every 60
seconds whether `SystemVersion.plist` was added today, and when it was, runs `jamf recon` and unloads itself, so the
new OS version reaches Jamf Pro without waiting for the next inventory.

Rename the label from `com.company` to your own reverse-domain name in both the filename and the `Label` key.

## Common problems

| you see | what it means | what to do |
|---|---|---|
| the dialog never appears | Jamf Helper isn't at `/Library/Application Support/JAMF/bin/jamfHelper.app`, or nobody is logged in | check the agent is installed; some scripts act silently with no user logged in, by design |
| exit `11` from `AppleSoftwareUpdate.sh` | the laptop isn't on power | its header lists every code |
| exit `13` | FileVault is still encrypting | wait for it to finish |
| `TCC.db Modifier.sh` changes nothing | no Full Disk Access, or a newer macOS blocking `TCC.db` writes | deploy a PPPC profile; on current macOS, use a PPPC profile instead of the script |
| `tcc_reset.sh` or `OS_Upgrade.sh` misbehaves on macOS 11 or later | they target macOS 10.12–10.15 and read version numbers that way | use upstream's newer versions |
| the Homebrew script fails to find the user | it uses `/usr/bin/python`, which Apple removed in macOS 12.3 | replace that lookup (e.g. `stat -f%Su /dev/console`) before use |

## Update and uninstall

This fork isn't synced with upstream, so "update" means taking the current version of the script from
[bp88/JSS-Scripts](https://github.com/bp88/JSS-Scripts), comparing it with what you uploaded, and testing it on your
test Mac again before replacing the one in Jamf Pro.

To remove a script, delete the policies that use it, then the script, in Jamf Pro. Remove the LaunchDaemon with
`sudo launchctl bootout system/com.company.reconafterupdate` and delete its file from `/Library/LaunchDaemons/`.
