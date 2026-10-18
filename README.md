# xteink-x4-calibre-scripts

Turns new articles from selected [Miniflux](https://miniflux.app) feeds into
EPUB digests in [Calibre](https://calibre-ebook.com), ready to copy onto an
Xteink X4 (or any e-reader).

EPUB rather than PDF: the X4's 4.3" screen needs text that reflows.

```
Miniflux API ──> lib/fetch_entries.py ──> recipes/miniflux.recipe ──> EPUB
     ──> calibredb add ──> Calibre library ──> e-reader
```

Everything runs on the machine that has Calibre. Miniflux only needs to be
reachable over HTTP(S) from there.

## How it works

- **Profiles.** Each profile is a separate digest, with its own feeds,
  schedule, title and state. For example, `main` for blogs and newsletters
  and `hn` for Hacker News. Each one is a single book with a table of
  contents, so you read one file through instead of opening dozens.
- **Feeds are picked by ID**, not by Miniflux category, so they stay in their
  normal categories. A Miniflux feed can only belong to one category.
- **Miniflux read state is never touched.** Each profile remembers the ID of the
  newest entry it has sent
  (`~/.local/state/miniflux-digest/<profile>/last-entry-id`), and each digest
  only has entries newer than that. Nothing is sent twice.
- **The first run** takes entries published in the last `MINIFLUX_INITIAL_DAYS`
  days instead of each feed's whole backlog.
- **Article text comes from Miniflux**, not from re-downloading each site.
  Turn on *Fetch original content* for feeds that only publish a teaser.
  Entries with less than `MINIFLUX_MIN_CHARS` of text are skipped, such as
  link-only posts or tweets the crawler could not extract.
- **Sections** are one per feed, or one per day (`MINIFLUX_GROUP_BY=day`). Per
  day suits a digest that is mostly a single feed.
- **Images are shrunk** to the X4's 480x800 screen and recompressed. That
  usually cuts the file size several times over, which matters on a device with
  little memory.
- **Every few days, whenever the machine is on.** A systemd user timer per
  profile fires hourly, plus on wake or login if an hour passed while the
  machine was off. The script records the date of its last successful run
  (`.../<profile>/last-run-date`) and does nothing until
  `MINIFLUX_DIGEST_EVERY_DAYS` have passed. That suits a laptop that is only
  open now and then. A failed attempt records nothing, so the next hour
  retries.
- **Waits for the network.** Before starting, it waits up to 2 minutes for
  Miniflux's `/healthcheck` to answer, since WiFi or a VPN may still be coming
  up right after resume.
- **Old digests are cleaned up.** Each run removes that profile's books added
  more than `MINIFLUX_KEEP_DAYS` days ago, matched by title. They go to
  Calibre's trash, not straight to deletion, so they can be restored from the
  GUI for a while.

## Requirements

- Calibre, the [official binary install](https://calibre-ebook.com/download_linux)
  (provides `ebook-convert` and `calibredb`). Distro packages are often outdated.
- `bash`, `curl`, `python3`, and systemd for the timers.
- A Miniflux API key: Miniflux → Settings → API Keys.

## Setup

1. Clone the repo and link everything into place:

   ```bash
   ./install.sh
   ```

   This symlinks `bin/miniflux-digest` into `~/.local/bin` and the systemd
   template units into `~/.config/systemd/user`, so editing files in the repo
   changes the installed copies too.

2. Save the API key. The command waits for you to paste it, keeping it out of
   your shell history:

   ```bash
   mkdir -p ~/.config && (umask 077; read -rs KEY && printf '%s\n' "$KEY" > ~/.config/miniflux-token)
   ```

3. Create the shared config and one file per profile:

   ```bash
   mkdir -p ~/.config/miniflux-digest
   install -m 600 config.example         ~/.config/miniflux-digest/config
   install -m 600 profile.conf.example   ~/.config/miniflux-digest/main.conf
   ```

   A feed's ID is the number in its Miniflux URL, `.../feed/<id>/entries`. The
   API also lists every feed with its ID:

   ```bash
   curl -s -H "X-Auth-Token: $(cat ~/.config/miniflux-token)" https://<miniflux>/v1/feeds \
     | python3 -c 'import json,sys; [print(f["id"], f["title"]) for f in json.load(sys.stdin)]'
   ```

   For another digest, copy `profile.conf.example` to e.g. `hn.conf` and give
   it a different `MINIFLUX_DIGEST_TITLE`.

4. Try it once with Calibre closed, then check the book in Calibre:

   ```bash
   miniflux-digest --force main
   ```

5. Turn on a timer per profile:

   ```bash
   systemctl --user enable --now miniflux-digest@main.timer
   ```

## Configuration

`~/.config/miniflux-digest/config` is shared by all profiles (see `config.example`):

| Variable | Meaning | Default |
|---|---|---|
| `MINIFLUX_URL` | Miniflux base URL, no trailing slash | (required) |
| `CALIBRE_SERVER_PORT` | Port of a running Calibre content server, if any | `8081` |

`~/.config/miniflux-digest/<profile>.conf` holds one digest's settings (see `profile.conf.example`):

| Variable | Meaning | Default |
|---|---|---|
| `MINIFLUX_DIGEST_TITLE` | Book title and cover text; must be unique per profile, since cleanup matches on it. Avoid regex characters | `Miniflux digest` |
| `MINIFLUX_FEED_IDS` | Comma-separated feed IDs; empty means the digest does nothing | (empty) |
| `MINIFLUX_DIGEST_EVERY_DAYS` | Build at most once every this many days | `1` |
| `MINIFLUX_GROUP_BY` | `feed` or `day` sections | `feed` |
| `MINIFLUX_INITIAL_DAYS` | How far back the very first run goes | `7` |
| `MINIFLUX_MAX_ENTRIES` | Most entries per digest; the rest go into the next one | `100` |
| `MINIFLUX_MIN_CHARS` | Skip entries with less text than this | `0` |
| `MINIFLUX_KEEP_DAYS` | Remove this profile's digests added this many days ago | `14` |

The API key is read from `~/.config/miniflux-token`. Neither the key nor any
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
miniflux-digest main                        # normal run; exits if not due yet
miniflux-digest --force hn                  # build now regardless of schedule
journalctl --user -u 'miniflux-digest@*'    # what past runs did
systemctl --user list-timers 'miniflux-digest@*'
```

To re-send the last few days for a profile, delete
`~/.local/state/miniflux-digest/<profile>/last-entry-id`. The next run then
behaves like a first run.

## Files

| Path | Purpose |
|---|---|
| `bin/miniflux-digest` | Entry point: schedule check, cleanup, fetch, build, add to Calibre |
| `lib/fetch_entries.py` | Pulls new entries for a profile's feeds from the Miniflux API |
| `recipes/miniflux.recipe` | Calibre recipe (Python) that turns those entries into an EPUB |
| `systemd/miniflux-digest@.{service,timer}` | Hourly systemd user timer, one instance per profile |
| `install.sh` | Symlinks the above into place |
| `config.example`, `profile.conf.example` | Templates for the shared and per-profile config |
