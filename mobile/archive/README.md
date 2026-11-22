# Archive: parts taken out of the phone app

Kept so they can be brought back or updated later. Nothing here is compiled or shipped (the files end in `.txt`).

- `portal-mode/`: the phone signing in to the university portal itself (hidden browser, lectures, downloads), as of commit
  `5dd2e2c`. To bring it back: copy the files into `lib/` and `test/` (drop the `.txt`), re-add the packages
  `webview_flutter`, `file_picker`, `html` and `path_provider`, and restore the proguard keep lines. The whole history is
  also in git (`git show 5dd2e2c:mobile/lib/portal.dart`).
