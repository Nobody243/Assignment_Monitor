# Releasing the phone app

The test APK from CI (`mobile-ci.yml`) is signed with Android's debug key and is for trying the app. A store or public
release is signed with **your own key** and built by `.github/workflows/phone-release.yml`.

## One time: make the signing key

Keep this key safe and backed up. If it is lost you cannot update the app in the Play Store; if it leaks, someone could
publish a fake update.

```powershell
keytool -genkeypair -v -keystore upload.jks -alias upload -keyalg RSA -keysize 4096 -validity 10000
[Convert]::ToBase64String([IO.File]::ReadAllBytes("upload.jks")) | Set-Clipboard   # copies the key as text
```

Then in the GitHub repository, Settings, Secrets and variables, Actions, add four secrets:

| Secret | Value |
| --- | --- |
| `ANDROID_KEYSTORE_BASE64` | the text copied above |
| `ANDROID_KEYSTORE_PASSWORD` | the keystore password you chose |
| `ANDROID_KEY_ALIAS` | `upload` (or the alias you chose) |
| `ANDROID_KEY_PASSWORD` | the key password you chose |

Delete `upload.jks` from the folder you ran this in once it is stored somewhere safe (a password manager's file
storage, or an encrypted drive). Never commit it; `.gitignore` already refuses `*.jks`, `*.keystore` and `key.properties`.

## Every release

1. Raise `version:` in `mobile/pubspec.yaml` (for example `1.0.1+2`) and `appVersion` in `mobile/lib/alerts.dart`.
2. Push a tag named `phone-v1.0.1`, or run the workflow from the Actions tab.
3. The workflow analyses, tests, signs and builds an APK and a Play bundle (`.aab`), with checksums, and attaches them to
   a **draft** release. Nothing is published until you publish the draft.
4. **Before publishing, install the APK on a real phone** and check: sign-in, a reminder arrives (set a lead time and a
   deadline a few minutes away), Snooze and Done on the notification, the timetable share sheet, the app lock, and the
   background update (leave it closed for a few hours). Code shrinking (R8) is on in this build, so this check matters.
   If something is missing in the shrunk build, rerun the workflow with "Shrink the code" off and tell the project.

## Play Store

See [STORE.md](STORE.md) for the listing text and the data-safety answers. A one-time developer fee applies, and a new
personal developer account has to run a closed test with real testers for a while before the first production release
(Google's rule).

## Automatic releases

A change to `mobile/` that lands on `main` is released by itself (`.github/workflows/auto-release-phone.yml`), separately from the desktop app:

1. it waits for the phone CI on that commit and stops if it fails;
2. it raises the version by one patch (put `[minor]` or `[major]` in a commit subject to raise that part), writes it into `pubspec.yaml`, `lib/alerts.dart` and `CHANGELOG.md` (the "Unreleased" section, or the commit subjects), and commits it as "Release phone X.Y.Z";
3. it tags `phone-vX.Y.Z` and starts the signed build (`phone-release.yml`), which publishes the APK and the Play bundle.

It needs the four signing secrets above; until they exist the workflow only says so and releases nothing. Put `[skip release]` in a commit message to push a phone change without releasing it. The desktop app has its own workflow (`auto-release-desktop.yml`, tags `vX.Y.Z`); a change that touches only one of the two releases only that one.
