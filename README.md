# AniList Franchise Downloader

A small Python script that builds a **local copy of AniList** for a whole franchise.

Give it an AniList ID, an AniList URL or a search text. It finds the whole franchise (prequels, sequels, side stories, spin-offs, adaptations and more) and saves everything as `.json` files, together with all the images.

It uses the free public AniList GraphQL API. You do **not** need an account or an API key.

## What it saves

- Every media of the franchise (anime, manga, novels, OVAs, movies, ...)
- All characters of every media, with their voice actors
- All staff of every media
- Every image it finds (covers, banners, character portraits, staff portraits)

## Install

You need Python 3 and two libraries:

```
pip install requests pykakasi
```

On Raspberry Pi OS you may need `pip install requests pykakasi --break-system-packages`.

`pykakasi` is only used to turn a Japanese title into romaji when a media has no English and no romaji title.

## Usage

```
python3 anilist_full.py
```

Then type one of these:

| Input  | Example                                   |
| ------ | ----------------------------------------- |
| ID     | `154587`                                  |
| URL    | `https://anilist.co/anime/154587`         |
| Search | `Frieren`                                 |

A search takes the best match. Anime and manga have different IDs, so for a manga use the URL or the ID.

## Output

```
AniList.co/
  franchises/
    <parent name>/
      media.json
      characters.json            (all characters of this media, with roles and voice actors)
      staff.json                 (all staff of this media, with roles)
      characters/<id>.json       (one file per character, shared by the whole franchise)
      images/...
      prequel/<name>/            (media.json, characters.json, staff.json)
      sequel/<name>/
      side_story/<name>/
      spin_off/<name>/
      adaptation/<name>/
      other/<name>/
  staff/
    <id>.json                    (one file per person, shared by all franchises)
    images/...                   (portraits only)
```

Folder names use the English title. If there is none, the romaji title is used. If there is none either, the native title is converted to romaji.

## How the franchise is found

1. The script starts with the media you typed.
2. It follows the relations of every media until nothing new appears. Only these relation types are followed:
   `PREQUEL`, `SEQUEL`, `PARENT`, `SIDE_STORY`, `SPIN_OFF`, `ALTERNATIVE`, `SUMMARY`, `ADAPTATION`, `SOURCE`.
   `CHARACTER` and `OTHER` are not followed, because they often link to unrelated shows.
3. The **parent** is the oldest media that has no `PREQUEL` and no `PARENT`. For a show based on a manga, this is usually the manga.
4. Every other media goes into a folder named after its relation type (for example `sequel/`).

You can change the list at the top of the script (`FOLLOW`) if the franchise is too big or too small.

## Things to know

- **Rate limit.** AniList allows about 90 requests per minute. The script waits a short time after every request and waits longer if AniList answers with "too many requests" (HTTP 429).
- **Big franchises take a long time.** The script makes requests for every media, every page of characters and staff, every different character and every different staff member.
- **You can run it again.** Characters and staff that are already saved are skipped. Images that already exist are skipped. The list of media is fetched again.
- **No loops from staff.** The works of a staff member (and of a character) are saved in the file, but they are never used to make new requests.
- **`inSeries`.** In the character files, every show has `"inSeries": true` or `false`. It tells you if the show is part of the franchise that was downloaded.
- **Staff images.** Only the portrait of every staff member is downloaded, not the covers of all their other works.

## Disclaimer

This project is not affiliated with AniList. Please follow the [AniList API terms](https://docs.anilist.co/) and do not overload the API.
