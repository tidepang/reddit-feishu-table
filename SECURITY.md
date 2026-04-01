# Security

## Sensitive Data

Do not commit any of the following:

- Feishu / Lark `base_token`
- `table_id` / `view_id` values from private workspaces
- local config files such as `config/*.local.json`
- generated reports in `data/`
- any user auth state, cookies, or API secrets

## Responsible Use

This repository is intended for collecting public signals and organizing them
into an editorial workflow. Users are responsible for complying with the terms
of any external source they collect from.

## Reporting

If you discover a security issue in the starter repo itself, do not open a
public issue with secrets or private workspace details attached. Report the
problem privately to the repository maintainer.
