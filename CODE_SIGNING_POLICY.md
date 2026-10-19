# Code signing policy

Free code signing for Assignment Monitor's Windows releases is provided by [SignPath.io](https://signpath.io), with a certificate issued by the [SignPath Foundation](https://signpath.org).

Signed releases are built by GitHub Actions directly from the source code in this repository on a version tag, and submitted to SignPath from that workflow. No binary that was built outside the public CI pipeline is ever signed.

## Team roles

| Role | Who |
| --- | --- |
| Committers and reviewers | [Nobody243](https://github.com/Nobody243) |
| Approvers | [Nobody243](https://github.com/Nobody243) |

## Privacy policy

This program will not transfer any information to other networked systems unless specifically requested by the user or the person installing or operating it.

In practice: the app connects only to the Bahria University portal (`cms.bahria.edu.pk`, `lms.bahria.edu.pk`) to do what the user asked it to do, and, if the user leaves the option enabled, to `api.github.com` to check for a newer release. See [PRIVACY.md](PRIVACY.md) and [SECURITY.md](SECURITY.md) for details.

## Verifying a release

Right-click `AssignmentMonitor-Setup.exe` → Properties → Digital Signatures. A signed release shows "SignPath Foundation" as the signer with the project name in the certificate. Unsigned builds, such as the rolling "Latest build" pre-release, carry no signature and Windows SmartScreen may warn when they are run.
