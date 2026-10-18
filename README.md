# xteink-x4-calibre-scripts

Turns new articles from selected [Miniflux](https://miniflux.app) feeds into a
daily EPUB digest in [Calibre](https://calibre-ebook.com), ready to copy onto
an Xteink X4 (or any e-reader).

EPUB rather than PDF: the X4's 4.3" screen needs text that reflows.

```
Miniflux API ──> lib/fetch_entries.py ──> recipes/miniflux.recipe ──> EPUB
     ──> calibredb add ──> Calibre library ──> e-reader
```

Everything runs on the machine that has Calibre. Miniflux only needs to be
reachable over HTTP(S) from there.

## How it works

- **Feeds are picked by ID**, not by Miniflux category, so they stay in their
  normal categories. A Miniflux feed can only belong to one category.
- **Miniflux read state is never touched.** The script remembers the ID of the
  newest entry it has put in a digest
  (`~/.local/state/miniflux-digest/last-entry-id`), and each digest only has
  entries newer than that. Nothing is sent twice.
- **The first run** takes entries published in the last `MINIFLUX_INITIAL_DAYS`
  days instead of each feed's whole backlog.
- **Article text comes from Miniflux**, not from re-downloading each site.
  Turn on *Fetch original content* for feeds that only publish a teaser.
- **At most one digest a day.** A systemd user timer fires hourly, plus on
  wake or login if an hour passed while the machine was off. The script
  records the date of its last successful run
  (`~/.local/state/miniflux-digest/last-run-date`) and exits early if it
  already ran today. That suits a laptop that is only open now and then.
  A failed attempt records nothing, so the next hour retries.
- **Waits for the network.** Before starting, it waits up to 2 minutes for
  Miniflux's `/healthcheck` to answer, since WiFi or a VPN may still be coming
  up right after resume.
- **Old digests are cleaned up.** Each run removes digest books added more than
  `MINIFLUX_KEEP_DAYS` days ago. They go to Calibre's trash, not straight to
  deletion, so they can be restored from the GUI for a while.
- **Up to 100 entries per digest.** Anything beyond that goes into the next
  one, without gaps.

## Requirements

- Calibre, the [official binary install](https://calibre-ebook.com/download_linux)
  (provides `ebook-convert` and `calibredb`). Distro packages are often outdated.
- `bash`, `curl`, `python3`, and systemd for the timer.
- A Miniflux API key: Miniflux → Settings → API Keys.

## Setup

1. Clone the repo and link everything into place:

   ```bash
   ./install.sh
   ```

   This symlinks `bin/miniflux-digest` into `~/.local/bin` and the systemd
   units into `~/.config/systemd/user`, so editing files in the repo changes
   the installed copies too.

2. Save the API key. The command waits for you to paste it, keeping it out of
   your shell history:

   ```bash
   mkdir -p ~/.config && (umask 077; read -rs KEY && printf '%s\n' "$KEY" > ~/.config/miniflux-token)
   ```

3. Create the config from the example and fill it in:

   ```bash
   mkdir -p ~/.config/miniflux-digest
   install -m 600 config.example ~/.config/miniflux-digest/config
   ```

   A feed's ID is the number in its Miniflux URL, `.../feed/<id>/entries`. The
   API also lists every feed with its ID:

   ```bash
   curl -s -H "X-Auth-Token: $(cat ~/.config/miniflux-token)" https://<miniflux>/v1/feeds \
     | python3 -c 'import json,sys; [print(f["id"], f["title"]) for f in json.load(sys.stdin)]'
   ```

4. Try it once with Calibre closed, then check the book in Calibre:

   ```bash
   miniflux-digest --force
   ```

5. Turn on the timer:

   ```bash
   systemctl --user enable --now miniflux-digest.timer
   ```

## Configuration

`~/.config/miniflux-digest/config` (see `config.example`):

| Variable | Meaning | Default |
|---|---|---|
| `MINIFLUX_URL` | Miniflux base URL, no trailing slash | (required) |
| `MINIFLUX_FEED_IDS` | Comma-separated feed IDs; empty means the digest does nothing | (empty) |
| `MINIFLUX_INITIAL_DAYS` | How far back the very first run goes | `7` |
| `MINIFLUX_KEEP_DAYS` | Remove digests added this many days ago | `14` |
| `CALIBRE_SERVER_PORT` | Port of a running Calibre content server, if any | `8081` |

The API key is read from `~/.config/miniflux-token`. Neither the key nor the
config is ever stored in this repo.

## Calibre being open

`calibredb` cannot write to a library while the Calibre GUI or `calibre-server`
has it open. The script handles both cases:

- **Content server running on `CALIBRE_SERVER_PORT`:** it adds and removes
  books through the server.
- **Calibre fully closed:** it writes to `~/Calibre Library` directly.
- **GUI open without its server:** that attempt fails and the next hour retries.

To make runs work while the GUI is open, enable its server: Preferences →
Sharing over the net. Set the port, tick *Run server automatically when calibre
starts*, then under *Advanced* tick *Allow un-authenticated local connections
to make changes*.

## Getting digests onto the e-reader

This last step is manual: the X4 cannot fetch books on a schedule. Either copy
the EPUB over with whatever transfer method your firmware supports, or point an
OPDS-capable firmware at the Calibre content server's catalog,
`http://<machine-lan-ip>:<port>/opds`.

## Usage

```bash
miniflux-digest                        # normal run; exits if it already ran today
miniflux-digest --force                # run now regardless
journalctl --user -u miniflux-digest   # what past runs did
systemctl --user list-timers miniflux-digest.timer
```

To re-send everything from the last few days, delete
`~/.local/state/miniflux-digest/last-entry-id`. The next run then behaves like
a first run.

## Files

| Path | Purpose |
|---|---|
| `bin/miniflux-digest` | Entry point: once-a-day check, cleanup, fetch, build, add to Calibre |
| `lib/fetch_entries.py` | Pulls new entries for the configured feeds from the Miniflux API |
| `recipes/miniflux.recipe` | Calibre recipe (Python) that turns those entries into an EPUB, one section per feed |
| `systemd/miniflux-digest.{service,timer}` | Hourly systemd user timer |
| `install.sh` | Symlinks the above into place |
| `config.example` | Template for `~/.config/miniflux-digest/config` |
