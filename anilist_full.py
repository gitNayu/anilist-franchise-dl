import json
import os
import re
import time

import pykakasi
import requests

API = 'https://graphql.anilist.co'
OUT = 'AniList.co'
DELAY = 0.8

FOLLOW = {
    'PREQUEL', 'SEQUEL', 'PARENT', 'SIDE_STORY', 'SPIN_OFF',
    'ALTERNATIVE', 'SUMMARY', 'ADAPTATION', 'SOURCE',
}

SEARCH_QUERY = '''
query ($search: String) {
  Media(search: $search) { id }
}
'''

MEDIA_QUERY = '''
query ($id: Int) {
  Media(id: $id) {
    id idMal
    title { userPreferred romaji english native }
    coverImage { extraLarge large medium color }
    bannerImage
    startDate { year month day }
    endDate { year month day }
    description(asHtml: false)
    season seasonYear type format status
    episodes duration chapters volumes
    genres synonyms source isAdult
    meanScore averageScore popularity favourites
    hashtag countryOfOrigin
    trailer { id site thumbnail }
    tags { id name description rank isMediaSpoiler isGeneralSpoiler category }
    studios { edges { isMain node { id name } } }
    relations { edges { id relationType node { id type format title { userPreferred } coverImage { extraLarge } bannerImage } } }
    recommendations(perPage: 25) { nodes { id rating mediaRecommendation { id title { userPreferred } coverImage { large } } } }
    externalLinks { id site url type language icon }
    streamingEpisodes { site title thumbnail url }
    rankings { id rank type format year season allTime context }
    stats { statusDistribution { status amount } scoreDistribution { score amount } }
    nextAiringEpisode { episode airingAt }
  }
}
'''

CHAR_LIST = '''
query ($id: Int, $page: Int) {
  Media(id: $id) {
    characters(page: $page, perPage: 25) {
      pageInfo { hasNextPage }
      edges { id role name node { id } voiceActors { id name { userPreferred } language image { large } } }
    }
  }
}
'''

STAFF_LIST = '''
query ($id: Int, $page: Int) {
  Media(id: $id) {
    staff(page: $page, perPage: 25) {
      pageInfo { hasNextPage }
      edges { id role node { id } }
    }
  }
}
'''

CHARACTER_QUERY = '''
query ($id: Int) {
  Character(id: $id) {
    id
    name { first middle last full native userPreferred alternative alternativeSpoiler }
    image { large medium }
    favourites
    description(asHtml: false)
    age gender bloodType
    dateOfBirth { year month day }
    media(perPage: 25) {
      pageInfo { total lastPage hasNextPage }
      edges {
        id characterRole
        voiceActorRoles { roleNotes voiceActor { id name { userPreferred } image { large } language } }
        node { id type title { userPreferred } coverImage { large } bannerImage startDate { year } }
      }
    }
  }
}
'''

STAFF_QUERY = '''
query ($id: Int) {
  Staff(id: $id) {
    id
    name { first middle last full native userPreferred alternative }
    image { large medium }
    description(asHtml: false)
    favourites age gender yearsActive homeTown bloodType primaryOccupations
    dateOfBirth { year month day }
    dateOfDeath { year month day }
    language
    characterMedia(perPage: 25) {
      pageInfo { total lastPage hasNextPage }
      edges {
        characterRole
        node { id type title { userPreferred } coverImage { large } bannerImage startDate { year } }
        characters { id name { userPreferred } image { large } }
      }
    }
    staffMedia(perPage: 25) {
      pageInfo { total lastPage hasNextPage }
      edges { staffRole node { id type title { userPreferred } coverImage { large } bannerImage startDate { year } } }
    }
  }
}
'''

def ask(query, variables):
    while True:
        r = requests.post(API, json={'query': query, 'variables': variables})
        if r.status_code == 429:
            wait = int(r.headers.get('Retry-After', 60))
            print('too many requests, waiting', wait, 'seconds')
            time.sleep(wait + 1)
            continue
        r.raise_for_status()
        time.sleep(DELAY)
        return r.json()['data']

def get_id(text):
    text = text.strip()
    if text.isdigit():
        return int(text)
    m = re.search(r'anilist\.co/(?:anime|manga)/(\d+)', text)
    if m:
        return int(m.group(1))
    return ask(SEARCH_QUERY, {'search': text})['Media']['id']

def get_all(query, media_id, key):
    items = []
    page = 1
    while True:
        data = ask(query, {'id': media_id, 'page': page})['Media'][key]
        items += data['edges']
        if not data['pageInfo']['hasNextPage']:
            break
        page += 1
    return items

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def cached(path, fn):
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    data = fn()
    save_json(path, data)
    return data

IMG = re.compile(r'^https://s\d+\.anilist\.co/file/anilistcdn/.+\.(jpg|jpeg|png|gif|webp)$')

def find_images(data, found):
    if isinstance(data, dict):
        for v in data.values():
            find_images(v, found)
    elif isinstance(data, list):
        for v in data:
            find_images(v, found)
    elif isinstance(data, str) and IMG.match(data):
        found.add(data)

def download_images(urls, folder):
    for i, url in enumerate(sorted(urls), 1):
        path = os.path.join(folder, 'images', url.split('anilistcdn/')[1])
        if os.path.exists(path):
            continue
        os.makedirs(os.path.dirname(path), exist_ok=True)
        r = requests.get(url)
        if r.status_code == 200:
            with open(path, 'wb') as f:
                f.write(r.content)
        print('image', i, '/', len(urls))

kks = pykakasi.kakasi()

def to_romaji(text):
    return ' '.join(item['hepburn'] for item in kks.convert(text))


def clean_name(m):
    t = m['title']
    name = t['english'] or t['romaji'] or to_romaji(t['native'] or '') or str(m['id'])
    name = re.sub(r'[^\w \-]', '', name).strip()
    return name or str(m['id'])

def crawl(start_id):
    medias = {}
    todo = [start_id]
    while todo:
        mid = todo.pop()
        if mid in medias:
            continue
        print('franchise media', mid)
        m = ask(MEDIA_QUERY, {'id': mid})['Media']
        medias[mid] = m
        for e in m['relations']['edges']:
            if e['relationType'] in FOLLOW and e['node']['id'] not in medias:
                todo.append(e['node']['id'])
    return medias

def start_key(m):
    d = m['startDate']
    return (d['year'] or 9999, d['month'] or 13, d['day'] or 32)

def find_root(medias):
    candidates = []
    for m in medias.values():
        kinds = {e['relationType'] for e in m['relations']['edges'] if e['node']['id'] in medias}
        if 'PREQUEL' not in kinds and 'PARENT' not in kinds:
            candidates.append(m)
    return min(candidates or list(medias.values()), key=start_key)

def build_tree(medias, root_id):
    paths = {root_id: ''}
    queue = [root_id]
    while queue:
        mid = queue.pop(0)
        for e in medias[mid]['relations']['edges']:
            nid = e['node']['id']
            if e['relationType'] not in FOLLOW or nid in paths or nid not in medias:
                continue
            rel = e['relationType'].lower() + '/' + clean_name(medias[nid])
            if rel in paths.values():
                rel = rel + ' ' + str(nid)
            paths[nid] = rel
            queue.append(nid)
    for nid in medias:
        if nid not in paths:
            rel = 'other/' + clean_name(medias[nid])
            if rel in paths.values():
                rel = rel + ' ' + str(nid)
            paths[nid] = rel
    return paths

def mark_series(data, ids):
    if isinstance(data, dict):
        node = data.get('node')
        if isinstance(node, dict) and 'type' in node and 'title' in node:
            data['inSeries'] = node['id'] in ids
        for v in data.values():
            mark_series(v, ids)
    elif isinstance(data, list):
        for v in data:
            mark_series(v, ids)

def do_characters(mid, folder, franchise, series_ids):
    chars = cached(
        os.path.join(folder, 'characters.json'),
        lambda: get_all(CHAR_LIST, mid, 'characters'),
    )
    out = [chars]
    for e in chars:
        cid = e['node']['id']
        print('character', cid)
        path = os.path.join(franchise, 'characters', str(cid) + '.json')
        data = cached(path, lambda: ask(CHARACTER_QUERY, {'id': cid})['Character'])
        mark_series(data, series_ids)
        save_json(path, data)
        out.append(data)
    return out

def do_staff(mid, folder):
    staff = cached(
        os.path.join(folder, 'staff.json'),
        lambda: get_all(STAFF_LIST, mid, 'staff'),
    )
    portraits = []
    for e in staff:
        sid = e['node']['id']
        print('staff', sid)
        path = os.path.join(OUT, 'staff', str(sid) + '.json')
        data = cached(path, lambda: ask(STAFF_QUERY, {'id': sid})['Staff'])
        portraits.append({'image': data['image']})
    return portraits

def main():
    text = input('AniList ID, URL or search: ')
    start_id = get_id(text)

    medias = crawl(start_id)
    root = find_root(medias)
    franchise = os.path.join(OUT, 'franchises', clean_name(root))
    paths = build_tree(medias, root['id'])
    series_ids = set(medias)
    print('franchise:', clean_name(root), '-', len(medias), 'media')

    franchise_data = []
    staff_data = []
    for mid, rel in paths.items():
        folder = os.path.join(franchise, rel)
        print('media', mid, rel)
        save_json(os.path.join(folder, 'media.json'), medias[mid])
        franchise_data.append(medias[mid])
        franchise_data += do_characters(mid, folder, franchise, series_ids)
        staff_data += do_staff(mid, folder)

    found = set()
    find_images(franchise_data, found)
    print('franchise images:', len(found))
    download_images(found, franchise)

    found = set()
    find_images(staff_data, found)
    print('staff portraits:', len(found))
    download_images(found, os.path.join(OUT, 'staff'))
    print('done')

main()