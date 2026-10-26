# DIY Find My-compatible tag (OpenHaystack-style) as a fallback for tracking Larry -- status as of 2026-10-26

Scope: a self-made BLE tag that broadcasts a **static** Find My advertisement key, whose reports are fetched with FindMy.py 0.10.2 via `KeyPair.from_b64(...)`, for use with this repo's `FINDMY_AIRTAG_KEY_B64` env var (consumed at `location-service/src/location_service/findmy_client.py:64`, `KeyPair.from_b64(self._settings.airtag_key_b64)`).

Legend: **[V]** = verified by me against primary source (code, API, repo) on 2026-10-26; **[R]** = reported by a third party (issue thread, blog), not independently verified; **[S]** = my speculation/inference.

> **Headline blocker (applies to genuine AirTags too):** Since about 2026-10-12, Apple stopped giving `searchPartyToken` to logins that use the Android-derived Anisette that FindMy.py 0.10.2 uses by default. Without that token, every report fetch returns HTTP 401. A DIY tag does **not** get around this. See the "Reliability" section.

## Which firmware projects are maintained in 2026, with release dates and supported boards?

### Takeaway
Only **dchristl/macless-haystack** (v2.7.2, 2026-03-15) is still actively released, and it is the practical choice. Its firmware covers ESP32 and nRF51/nRF52 (its nRF52 build is marked "untested"). The original seemoo-lab/openhaystack has had no release since v0.5.3 (2023-10-09) and needs a Mac plus a Mail plugin. find-you and acalatrava's firmware are effectively dormant. All the major firmwares broadcast a static key by default. macless-haystack and find-you can rotate through a fixed list of keys.

### Cited Findings
- [V] GitHub API on 2026-10-26 (release dates and last push):
  - seemoo-lab/openhaystack: latest release v0.5.3 on 2023-10-09, last push 2026-08-17, not archived.
  - dchristl/macless-haystack: latest release v2.7.2 on 2026-03-15 (previous v2.7.0 on 2025-07-25), last push 2026-03-15.
  - positive-security/find-you: no releases, last push 2022-02-24.
  - acalatrava/openhaystack-firmware: release 0.1 on 2021-05-07, last push 2023-12-21.
  - biemster/FindMy: no releases, last push 2024-12-12.
  - malmeloo/FindMy.py: v0.10.2 on 2026-09-14.
  - Sources: [openhaystack](https://github.com/seemoo-lab/openhaystack/releases), [macless-haystack](https://github.com/dchristl/macless-haystack/releases), [find-you](https://github.com/positive-security/find-you), [acalatrava fw](https://github.com/acalatrava/openhaystack-firmware), [biemster/FindMy](https://github.com/biemster/FindMy), [FindMy.py](https://github.com/malmeloo/FindMy.py/releases)
- [V] OpenHaystack supports these targets:
  - nRF51822 only (BBC micro:bit v1).
  - ESP32-WROOM / WROVER.
  - Linux HCI (Raspberry Pi).
  - It requires macOS 11 or later and an Apple Mail plugin, and it calls itself experimental. Its README says current firmware broadcasts a fixed public key, so the tag can be tracked by others nearby.
  - Source: [seemoo-lab/openhaystack README](https://github.com/seemoo-lab/openhaystack)
- [V] macless-haystack ships `firmware/ESP32` and `firmware/nrf5x`. It needs no Mac, but it does need an Apple ID with 2FA (README: "Only sms/text message as second factor is supported!") and an Anisette server. Its README says other OpenHaystack-compatible devices such as the ST17H66 may work with just the Base64 advertisement key. -- [macless-haystack README](https://github.com/dchristl/macless-haystack)
- [V] The macless-haystack nrf5x firmware is acalatrava's battery-optimised SoftDevice firmware. Its README says:
  - It "consumes more power when more than 1 key is used. The controller wakes up every 30 minutes and switches the key."
  - "Currently, only the NRF51 build has been tested, and the NRF52 build has not been tested yet."
  - Firmware is patched by `dd`-ing the `PREFIX_keyfile` over the `OFFLINEFINDINGPUBLICKEYHERE!` marker, then flashing with openocd.
  - Source: [macless-haystack firmware/nrf5x README](https://github.com/dchristl/macless-haystack/tree/main/firmware/nrf5x)
- [V] acalatrava's firmware runs on Nordic SDK 11 with SoftDevice S130/S132. It was tested on the EBYTE E104-BT5032A and an "AliExpress beacon". It is patched with `ADV_KEY_BASE64=... make patch`. -- [acalatrava openhaystack-alternative README](https://github.com/acalatrava/openhaystack-firmware/blob/main/apps/openhaystack-alternative/README.md)
- [V] Open macless-haystack PRs and issues from July 2026 add ESP32-S3 support (#241, #243). -- [macless-haystack issues](https://github.com/dchristl/macless-haystack/issues)
- [R] koenvervloesem/openhaystack-zephyr is a proof of concept with a single static key and no power management. dakhnod/FakeTag (nRF51) rotates keys hourly but is not OpenHaystack-compatible. -- [openhaystack-zephyr](https://github.com/koenvervloesem/openhaystack-zephyr/blob/main/README.rst), [FakeTag](https://github.com/dakhnod/FakeTag)
- [R] pix/heystack-nrf5x (OpenHaystack firmware for nRF51/52) was last pushed on 2024-11-02. -- [gittrend summary](https://gittrend.io/repo/pix/heystack-nrf5x)
- [R] biemster's "$1 tracker" thread (2024-12) evaluated very cheap chips:
  - Candidates were WCH CH592/CH582 (Find My firmware at oshwlab.com/biemster/ch592tag), PHY6252 (Ai-Thinker PB-03M module, about $0.60-0.66 on LCSC), Telink TLSR825x, and InPlay IN100.
  - Commenters said the PB-03M was "the winner".
  - An open issue (#80, updated 2026-08-19) reports the flashing script writing the wrong flash area on ST17H66B.
  - Sources: [biemster/FindMy #74](https://github.com/biemster/FindMy/issues/74), [#80](https://github.com/biemster/FindMy/issues/80)

### Inferences
- [S] For this project, use macless-haystack's `generate_keys.py` (or FindMy.py's `KeyPair.new()`) plus its nRF51 build on a cheap AliExpress nRF51822 coin-cell beacon. That is the best-documented path. The macless-haystack backend/app is not needed, because FindMy.py does the fetching.
- [S] Use **one** key (the default) so the static `KeyPair.from_b64` path works unchanged. Several keys would need FindMy.py's `FixedRollingKeyPairAccessory` (see the next section), which means changing `findmy_client.py`.

### Gaps
- I did not verify which macless-haystack ESP32 variants are confirmed working; the ESP32 README was not fetched.
- I found no confirmed reports of the nRF52 build working on specific boards.
- I found no 2026 maker write-ups comparing the firmwares.

## How is the key pair generated, and how does FindMy.py consume it?

### Takeaway
The key is a P-224 (SECP224R1) key pair. The private key is a 28-byte big-endian scalar, base64-encoded. That is exactly what `KeyPair.from_b64` decodes, and FindMy.py can generate one itself with `KeyPair.new()`. The firmware needs the **advertisement key**: the 28-byte X coordinate of the public key, base64. FindMy.py exposes it as `adv_key_b64`. macless-haystack's `generate_keys.py` writes all three values to a `.keys` file.

### Cited Findings
- [V] FindMy.py v0.10.2 `findmy/keys.py`:
  - `KeyPair.__init__(private_key: bytes)` builds the key with `ec.derive_private_key(int, ec.SECP224R1())`.
  - `KeyPair.new()` returns `cls(secrets.token_bytes(28))`.
  - `KeyPair.from_b64(key_b64)` returns `cls(base64.b64decode(key_b64))`, in the "Same format as returned by `KeyPair.private_key_b64`", which is the 28-byte big-endian private value, base64.
  - The `adv_key_b64`, `hashed_adv_key_b64` (SHA-256 of the adv key), `mac_address` and `adv_data()` / `of_data()` helpers build the BLE payload.
  - Source: [FindMy.py keys.py @ v0.10.2](https://github.com/malmeloo/FindMy.py/blob/v0.10.2/findmy/keys.py)
- [V] The `examples/fetch_reports.py` example:
  - It calls `key = KeyPair.from_b64(priv_key)` and then `acc.fetch_location(key)`.
  - Its usage text says "The private key should be base64-encoded."
  - It notes that a saved report JSON "will contain the tag's private key!"
  - Source: [fetch_reports.py](https://github.com/malmeloo/FindMy.py/blob/main/examples/fetch_reports.py)
- [V] FindMy.py v0.10.2 also ships `examples/macless_haystack_json_to_findmypy_json.py`:
  - It reads macless-haystack's `PREFIX_devices.json` (`privateKey` + `additionalKeys`) into a `FixedRollingKeyPairAccessory`.
  - This is the supported path for multi-key tags.
  - Source: [FindMy.py examples @ v0.10.2](https://github.com/malmeloo/FindMy.py/tree/v0.10.2/examples)
- [V] macless-haystack `generate_keys.py`:
  - It draws `priv = random.getrandbits(224)` and derives the X coordinate on SECP224R1.
  - It writes `Private key: <b64>`, `Advertisement key: <b64>` and `Hashed adv key: <b64>` to `output/PREFIX.keys`, and also writes `PREFIX_keyfile` (a count byte plus the raw 28-byte adv keys, for patching firmware) and `PREFIX_devices.json`.
  - It regenerates any key whose hashed key has a `/` in its first 7 base64 characters.
  - The default limit is 1 key. A hidden flag `--thisisnotforstalking i_agree` raises it to 50.
  - Source: [generate_keys.py](https://github.com/dchristl/macless-haystack/blob/main/generate_keys.py)
- [V] Open issue #244 (2026-08-07) says `generate_keys.py` uses the non-cryptographic `random.getrandbits()` for private keys and should use `secrets`. -- [macless-haystack #244](https://github.com/dchristl/macless-haystack/issues/244)

### Inferences
- [S] Recommended flow:
  1. Run `python -c "from findmy import KeyPair; k=KeyPair.new(); print(k.private_key_b64, k.adv_key_b64)"`. This uses a CSPRNG, so it avoids the #244 weakness.
  2. Set `FINDMY_AIRTAG_KEY_B64=<private_key_b64>`.
  3. Patch the firmware with `adv_key_b64`. For acalatrava, use `ADV_KEY_BASE64=...`. For macless-haystack's nrf5x `dd` method, use a keyfile of `\x01` followed by the 28 raw adv-key bytes.
  4. The macless-haystack `.keys` "Private key:" line also works directly in `from_b64`.
- [S] A small edge case: `KeyPair.new()` does not apply macless-haystack's `/`-in-hash regeneration. That check seems to exist for macless-haystack's own backend/URL handling, so it probably does not matter for FindMy.py. This is unverified.

### Gaps
- I did not confirm that `KeyPair.new()` output works end to end with the macless nrf5x `dd` patch method; only the format matches on paper.

## Hardware for a cat collar: size, weight, battery, battery life, cost, enclosure

### Takeaway
The realistic collar candidate is an AliExpress nRF51822 (or nRF52) CR2032 "iBeacon" fob in a small plastic case, often sold as "waterproof". Flashing it needs an SWD programmer. ESP32 boards draw too much power for a coin cell and are too big for a cat. I found no OpenHaystack-specific measured battery-life figures. Generic nRF51 figures range from about a week to about a year depending on interval and sleep behaviour, so measure your own unit.

### Cited Findings
- [V] macless-haystack's nrf5x firmware was tested on two AliExpress beacons, one bare and one "waterproof beacon with case". The repo includes pinout photos for both. -- [macless-haystack firmware/nrf5x](https://github.com/dchristl/macless-haystack/tree/main/firmware/nrf5x)
- [R] Make: lists two hardware options, with an overall cost of "$0-$50":
  - An nRF51822 "iBeacon" tracker with a CR2032 and an SWD programmer (J-Link EDU Mini or Adafruit 3571).
  - An ESP32 Feather with a USB power bank.
  - Source: [Make: Find My DIY AirTag Tracker (2022, updated 2024-06-03)](https://makezine.com/projects/find-my-diy-airtag-tracker/)
- [R] Generic nRF51 / CR2032 beacon power figures (not OpenHaystack firmware):
  - Nordic DevZone model: about 41 days at a 100 ms interval and about 366 days at a 1000 ms interval for a 220 mAh cell. nRF52 draws about 40% less than nRF51.
  - A poorly sleeping nRF51 ran out in about 2 days.
  - An nRF51-DK drew 1.23 mA at a 1 s interval, about 8 days.
  - Sources: [Nordic DevZone 11522](https://devzone.nordicsemi.com/f/nordic-q-a/11522/consumption-in-nrf51822), [mbed forum](https://os.mbed.com/forum/mbed/post/53284/)
- [R] Ai-Thinker PB-03M (PHY6252) modules cost about $0.60-0.66 on LCSC. biemster designed a 12.45 x 12.45 mm CH592 tag PCB. -- [biemster/FindMy #74](https://github.com/biemster/FindMy/issues/74)
- [V] For comparison, the Make: article describes a genuine AirTag as advertising "every 2 seconds". -- [Make:](https://makezine.com/projects/find-my-diy-airtag-tracker/)

### Inferences
- [S] The ballpark is a few US dollars for the beacon and about $10-60 for an SWD programmer (any ST-Link clone works with openocd).
- [S] Weight is likely about 5-10 g including the CR2032, which is about 3 g. That is comparable to an AirTag (about 11 g), but these are not sourced figures.
- [S] Use a breakaway collar.
- [S] acalatrava's SoftDevice firmware exists specifically for better power efficiency. Months on a CR2032 is plausible at an interval of about 1-2 s, but unverified. Multi-key rotation costs extra power.

### Gaps
- I found no measured battery life for macless-haystack or acalatrava firmware, and no default advertising interval. Both would need reading `main.c` / `openhaystack.c`.
- I found no specific waterproof enclosure products with IP ratings, and no sourced weights.

## Reliability vs a genuine AirTag, anti-stalking alerts, and Apple blocking (iOS 26)

### Takeaway
A DIY tag has no UWB, no Precision Finding, no sound and no owner pairing. It depends entirely on passing Apple devices. Community reports since 2025 describe fewer reports for DIY tags. In **October 2026**, Apple stopped giving `searchPartyToken` to the Android-Anisette login that FindMy.py 0.10.2 uses by default, which broke report fetching for **all** keys, genuine AirTags included. The working fixes are a real Mac's native Anisette or emulated macOS CoreADI. A static-key tag is the kind that iOS anti-stalking can recognise, because the same key is seen over time. I found no direct test confirming that a DIY tag produces an iOS alert.

### Cited Findings
- [R] **2026-10-12 token change.** After a successful login, `com.apple.mobileme` returns only `mmeAuthToken`, with no `searchPartyToken`, and `acsnservice/fetch` returns HTTP 401.
  - The cause was traced to the platform of the Anisette identity. Android and Windows identities never get `searchPartyToken`, while macOS and iOS identities do.
  - Two fixes were confirmed by multiple users:
    1. A real Mac's native AOSKit through PyObjC. One user reports FindMy.py 0.10.2 fetching again from 2026-10-22 on macOS 26.2.
    2. Apple's macOS CoreADI (extracted from iTunes 12.8.3) emulated under Unicorn on Linux, at [sacca97/os-findmy-e](https://github.com/sacca97/os-findmy-e).
  - The issue was closed 2026-10-25. The FindMy.py maintainer said a patch for Anisette.py was being discussed; I found no release containing it yet.
  - Sources: [FindMy.py #278](https://github.com/malmeloo/FindMy.py/issues/278), [macless-haystack #248](https://github.com/dchristl/macless-haystack/issues/248)
- [R] Related login breakages in Sep-Oct 2026:
  - GSA returned HTTP 503 and then error `-80045`, fixed by a `X-MMe-Client-Info` header matching the Android platform.
  - 2FA is now signalled by `hsc: 409` rather than `au`.
  - The `-80045` issue on macless-haystack (#249, opened 2026-10-24) is still open.
  - Sources: [FindMy.py #278](https://github.com/malmeloo/FindMy.py/issues/278), [macless-haystack #249](https://github.com/dchristl/macless-haystack/issues/249), [#245](https://github.com/dchristl/macless-haystack/issues/245)
- [R] DIY tags getting fewer reports:
  - Around 2025-05-20, OpenHaystack tags were reportedly "ignored" by Apple's cloud, though other users still saw reports.
  - Since 2025-09-27, users report "less than half" the previous report volume, frequent empty HTTP 200 responses on `findmyservice/v2/fetch` (malmeloo: an Apple-side issue, retry after a few seconds), and an iPhone 8 on iOS 16.7.11 no longer uploading DIY tag locations.
  - Some iOS 26 users also saw no updates.
  - None of this was resolved or confirmed by Apple.
  - Sources: [openhaystack #273](https://github.com/seemoo-lab/openhaystack/issues/273), [biemster/FindMy #88](https://github.com/biemster/FindMy/issues/88), [macless-haystack issues](https://github.com/dchristl/macless-haystack/issues)
- [V] Finder iPhones cannot tell an AirTag from an OpenHaystack-based clone. That is the basis for DIY tags receiving reports at all. -- [Positive Security, Send My](https://positive.security/blog/send-my), [openhaystack README](https://github.com/seemoo-lab/openhaystack)
- [R] Apple says it alerts users when an accessory "separated from its owner is seen moving with you over time". This depends on recognising the same key over time; AirTags rotate their key only about daily. Positive Security's stealth clone defeated iOS and AirGuard alerts over 5+ days by cycling 2,000 keys, one beacon per key. The implication is that a static, single-key tag is recognisable. -- [Positive Security, Find You (2022-02-21)](https://positive.security/blog/find-you), [AirGuard paper](https://arxiv.org/pdf/2202.11813v1)
- [R] The PoPETs 2023 "Track You" paper found undisclosed status-byte bits in AirTag advertisements that suppress safety alerts. -- [Track You, PoPETs 2023](https://petsymposium.org/popets/2023/popets-2023-0102.pdf)
- [V] The OpenHaystack README warns that a fixed key lets nearby devices track the tag. -- [openhaystack](https://github.com/seemoo-lab/openhaystack)

### Inferences
- [S] **Most important for this repo:** switching to a DIY tag does not fix the October 2026 fetch breakage. The fetch side, meaning Anisette provenance, has to be fixed either way. A Mac running native AOSKit, or emulated macOS CoreADI, is now needed for `searchPartyToken`. This also affects the CLAUDE.md design, where `login.py` runs locally and Docker restores the session: the session is reportedly tied to the machine that minted the Anisette.
- [S] A static-key tag on a cat that roams near neighbours may eventually trigger "unknown accessory / found moving with you" alerts on their iPhones. The anti-stalking logic is built around a stable identifier seen moving with the same person, and nothing marks a DIY tag as "with its owner". A cat that stays near home rarely "moves with" a stranger, so the risk is probably low, but it is untested.
- [S] Report frequency in a dense urban area is plausibly similar to an AirTag's for the same key, given that iPhones cannot tell them apart. The 2025-2026 reports of lower volume add real uncertainty, and genuine AirTags may get preferential handling. This is unverified.
- [S] Do **not** use key-rotation or status-byte tricks to suppress alerts. They are the stalking-evasion techniques from find-you and "Track You", and they are ethically and legally fraught.

### Gaps
- I found no first-hand 2026 test of whether a static-key DIY tag triggers alerts on iOS 26.
- I found no Apple statement on blocking DIY tags.
- I found no quantified comparison of DIY tag vs AirTag report frequency.
- I could not confirm whether any FindMy.py release after 0.10.2 has integrated macOS-CoreADI Anisette; #279 "Fix and integrate with anisette mac backend" was open as of 2026-10-21.

## Legal, ethical and Apple ToS notes

### Takeaway
Tracking your own cat is generally lawful, but a DIY tag sits outside Apple's MFi/Find My Network program. FindMy.py, OpenHaystack and macless-haystack all use reverse-engineered, unofficial APIs, and Apple is actively changing auth to restrict non-Apple clients. Expect breakage and possible account action, and use a secondary Apple ID.

### Cited Findings
- [V] OpenHaystack states that it "is not affiliated with or endorsed by Apple Inc." and is experimental. -- [openhaystack README](https://github.com/seemoo-lab/openhaystack)
- [V] macless-haystack limits key generation to 1 by default and hides the multi-key flag behind `--thisisnotforstalking i_agree`. -- [generate_keys.py](https://github.com/dchristl/macless-haystack/blob/main/generate_keys.py)
- [R] An open "Account limit reached" issue (#86, active 2026-07) and an FAQ PR (#240) note that new Apple IDs need a physical device. -- [macless-haystack issues](https://github.com/dchristl/macless-haystack/issues)
- [R] The FindMy.py maintainer, on Apple restricting `searchPartyToken` to macOS/iOS identities (2026-10-16): "So Apple finally did the thing I was afraid they'd do all along." -- [FindMy.py #278](https://github.com/malmeloo/FindMy.py/issues/278)

### Inferences
- [S] Practical steps:
  - Use a dedicated Apple ID.
  - Keep `account.json` and the private key secret. Anyone holding the key can fetch the cat's location history, which is effectively your home location.
  - Do not tamper with anti-stalking features.
- [S] This is not legal advice. Laws on location trackers (anti-stalking statutes) target tracking people without consent. A tag on your own pet is ordinarily fine, but disabling alerts could be read as intent to evade.

### Gaps
- I did not retrieve or quote the specific clauses of Apple's Media Services / iCloud Terms covering reverse-engineered clients.
- I did not research jurisdiction-specific law.
