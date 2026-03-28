# Push Security Checklist

Use this checklist before pushing the repository to a remote.

## Automated checks

Run the repository scanner locally:

```powershell
python scripts/check_repo_secrets.py
```

Enable the local pre-commit hook once per clone:

```powershell
python scripts/install_git_hooks.py
```

The hook runs the same scanner before every commit, and GitHub Actions reruns it on each push and pull request.

## Manual review before `git add .`

Review any newly generated attachments before staging them, especially:

- `evidence/screenshots/*.png`
- `reports/*.pdf`
- `excel/*.xlsx`
- exported JSON manifests outside the normal checked-in deliverables

Check that they do not expose wallet UIs, copied env values, usernames, local filesystem paths, or browser/account metadata.

## Secret handling rules

- Keep real secrets only in local env files such as `config/sepolia.env` and `frontend/.env`.
- Do not pass private keys through `--private-key` style CLI flags unless there is no safer option; shells persist command history.
- Treat the checked-in Sepolia addresses as public demo data. The matching private keys must remain disposable test-only accounts.

## Checked-in `solc.exe`

This repository currently keeps the Windows `solc.exe` used by Slither under `.tooling/solcx/solc-v0.8.24/solc.exe`.

- Source: installed by `py-solc-x` for Solidity `0.8.24`
- Pinned SHA-256: `580ee56b61bbcaad953117e1e4a0874d90e6af5cb4ce4359571d7da25f6620e9`

If the binary is refreshed, update the checksum and re-run static analysis before pushing.
