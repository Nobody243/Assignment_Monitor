/// The tester's own account sees a few extra tools in Settings (copying support info for a bug report, the Background
/// checks page with its setup and login controls). Everyone else gets a plain app with only what they need.
/// To add a phone, add the GitHub login it is signed in with (lower case).
const testerLogins = {'nobody243'};

bool isTester(String? githubLogin) => githubLogin != null && testerLogins.contains(githubLogin.trim().toLowerCase());
