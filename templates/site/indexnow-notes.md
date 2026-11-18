# IndexNow on an Astro site on Vercel

IndexNow tells Bing, Yandex, Seznam and Naver that a URL was added, changed or removed. Google does not take part. Bing's index also feeds ChatGPT search and Copilot, so a quick Bing pickup matters for AI answers.

1. Create the key file once: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/indexnow.py" key --write`. It writes `public/<key>.txt` whose only content is the key (8 to 128 characters, letters, digits, hyphen) and records the path in `config.connectors.indexnow.key_file`. Commit it on the action branch like any other change.
2. After the deploy, check that the file is served: `indexnow.py check --live https://www.example.de`.
3. After every production change and its live verification, submit the changed URLs: `indexnow.py submit --action <id>` prints the request (dry run); add `--execute` to send it. Submit removed URLs too, so the engines drop them.
4. Status 200 or 202 means accepted. 403 means the key file is not reachable; 422 means a URL is on another host than the key.

Never submit URLs of preview hosts, and never submit unchanged pages on a schedule. IndexNow is not a ranking lever; it only shortens the time until a change is seen.
