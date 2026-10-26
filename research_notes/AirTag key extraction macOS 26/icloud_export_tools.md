# iCloud/CloudKit-based Find My accessory key export tools (status late October 2026)

Scope note: this covers tools that pull an AirTag owner's OWN Find My accessory
keys (master/beacon keys) from Apple's CloudKit `com.apple.icloud.searchpartyd`
"BeaconStore" zone over iCloud, versus the older route of reading them from a
local Mac's `~/Library/com.apple.icloud.searchpartyd` files + Mac keychain.
All dates verified against GitHub API / primary pages on 2026-10-26 unless
marked speculative.

## export-findmy: issues, PRs, forks, failure modes, key-creation hazard

### Takeaway
`stek29/export-findmy` is the current working iCloud-escrow key exporter (Rust,
wraps a fork of OpenBubbles/rustpush). It descends from a Claude-coded tool by
`thisiscam` (Mar 2026). The repo has exactly one open PR (#1, the macOS 26 fix,
unmerged) and no open bug issues. The specific `BadMsg` and "Insert class key
not found" failures from the known context do NOT appear anywhere in its public
issues/PRs/worklog -- but the worklog independently confirms the tool creates
PCS master/service keys locally, corroborating the key-creation hazard.

### Cited Findings
- `stek29/export-findmy` README: "Export AirTag/FindMy accessory private keys from iCloud, producing `.plist` and `.json` files compatible with FindMy.py... Tested on MacOS 26." — [README](https://github.com/stek29/export-findmy)
- Repo metadata: default branch `main`, 6 stars, last push `2026-06-13T17:07:39Z`, open_issues_count 1 (that one is PR #1). Latest commits all `2026-06-10..06-13` (auth/escrow/export fixes); initial commit `2026-03-30` ("Initial commit: FindMy AirTag key export tool"). — [GitHub API /repos/stek29/export-findmy]
- Only issue/PR in the repo is **PR #1** by `MElkmeshi`, "Use native macOS anisette (AOSKit); fix export on macOS 26 (Tahoe)", opened `2026-08-14T18:59:27Z`, **state open, not merged, zero comments** as of 2026-10-26. — [GitHub API /repos/stek29/export-findmy/pulls/1]
- PR #1 rationale: on macOS 26, remote/emulated anisette servers (public and local `anisette-v3-server`) fail provisioning inside the emulated ADI lib -- `provision.adi.ADIException ... generic libc/file manipulation error (-45054)` surfacing as `EndProvisioningError`. Native macOS anisette (AOSKit, omnisette `default_provider`) uses the real system ADI and avoids this. Also fixes an `X-Mme-Client-Info` mismatch (tool hardcoded `<iPhone OS;...>` while native anisette carries `Mac15,6`, causing `loginDelegates` rejection `status:1 "We can not process your request..."`). Tested on macOS 26.5.2, Mac15,6, Apple Silicon. — [PR #1 body](https://github.com/stek29/export-findmy/pull/1)
- Lineage: `thisiscam/export-findmy` posted `2026-03-30` ("I let claude coded the key extraction tool and my airtags are finally useful again"); `stek29` rebased it on latest OpenBubbles, fixed forked libs, and published the working CLI on `2026-06-11`. — [FindMy.py issue #173 comments](https://github.com/malmeloo/FindMy.py/issues/173)
- Usage flow prompts for: Apple password, 2FA method (trusted device live-tested; SMS implemented but untested), 2FA code, **device passcode** (screen-lock PIN of an iPhone or Mac login password of a device on the account), and escrow-password setup. — [README](https://github.com/stek29/export-findmy)
- The tool CREATES a new escrow bottle / Octagon peer to join the clique, and provides `--delete-own-escrow-bottle` to remove the synthetic exporter bottle afterward ("After the keys have been exported and you no longer need this exporter to remain recoverable in iCloud Keychain, delete the escrow bottle it created"). It also persists trusted-peer state in `keychain_state.plist` (mode 0600) so later runs reuse the peer instead of adding new bottles. — [README](https://github.com/stek29/export-findmy)
- **Key-creation hazard corroboration (worklog):** stek29's worklog documents an "RFC 6637 AES key-wrap panic" in `rustpush::icloud::pcs::PCSKey::new` / `PCSShareProtection::decode`, and that "both wrapping and unwrapping were switched so locally generated PCS data uses the same code path" plus removal of an INFO log "that printed the unwrapped PCS master key." This confirms the code path generates/wraps PCS master keys locally. — [export-findmy worklog gist](https://gist.github.com/stek29/4b15b02cf420223cc4c5b11e4870f5e0)
- Worklog also documents a **post-join CloudKit decryption panic**: `CuttlefishEncItem::decrypt` used `.unwrap()`, `panic!("Bad padding!")` on malformed ISO/IEC 7816-4 padding, and could panic slicing the IV; stek29 converted these to `KeychainItemDecryptError` and skips bad items instead of terminating. Upstream OpenBubbles still had the panic-prone code at time of writing. — [worklog gist](https://gist.github.com/stek29/4b15b02cf420223cc4c5b11e4870f5e0)
- Worklog documents an escrow schema failure (`Serde("missing field passcodeGeneration")`) on an account returning "27 metadata record(s) and 4 viable Cuttlefish bottle(s)"; fixed by making `passcodeGeneration` `#[serde(default)]`. Confirms real-account escrow parsing is brittle to Apple schema variation. — [worklog gist](https://gist.github.com/stek29/4b15b02cf420223cc4c5b11e4870f5e0)
- A companion stek29 gist converts FindMy.py JSON/plist into an OpenTagViewer import zip (`findmy_json_to_opentagviewer_zip.py`, updated 2026-06-13). — [stek29 gists](https://api.github.com/users/stek29/gists)

### Inferences
- The specific `BadMsg` (rustpush `keychain.rs` during `join_clique_from_escrow`, signature verification) and the `panic "Insert class key not found" in insert_keychain` with `get_master_key`/`get_service_key` creating keys -- from the known context -- are almost certainly from the user's own live runs; they are not reproduced in any public export-findmy issue (there are none) or in the worklog. The worklog's PCS-key-generation path is the closest public corroboration that the library will mint new PCS master/service keys when they are missing.
- Because export-findmy's only maintainer-side public artifact is the worklog (June) and PR #1 (unmerged since August, no reply), the project is effectively low-activity / semi-abandoned at head; the macOS 26 fix lives only in the unmerged fork branch.

### Gaps
- No public record of `BadMsg` or "Insert class key not found" in export-findmy or rustpush issues; cannot confirm whether maintainers are aware of the key-creation hazard as a user-facing risk (not discussed in worklog or PRs).
- Whether `--delete-own-escrow-bottle` also removes the Octagon trust peer (vs. only the escrow bottle) is not documented; README wording implies it deletes the bottle only.

## rustpush (OpenBubbles + stek29 fork): Octagon/escrow issues on iOS/macOS 26

### Takeaway
`stek29/export-findmy` builds on `stek29/rustpush` (fork of
`OpenBubbles/rustpush`), branch `local/export-findmy-changes`. The owned-item
export path needs GSA/2FA + Cuttlefish/Octagon trust + PCS + CloudKit; remote
anisette suffices and no closed-source "absinthe" binary is required for this
path (contrary to an earlier belief).

### Cited Findings
- `stek29/rustpush` is a fork of `OpenBubbles/rustpush`, default branch `master`, last push `2026-06-11T02:26:39Z`; it has a dedicated branch **`local/export-findmy-changes`** alongside `master`. — [GitHub API /repos/stek29/rustpush]
- rustpush's owned-item export logic lives at `src/cloudkit.rs` (referenced ~L828 by malmeloo). — [FindMy.py issue #173](https://github.com/malmeloo/FindMy.py/issues/173)
- Per OpenBubbles/rustpush issue #18 (summarized in worklog): owned-item Find My export needs GSA/2FA, Cuttlefish/Octagon trust, PCS, and CloudKit; **remote anisette is sufficient**; Albert activation is NOT required for exporting the account owner's own items (APS activation only matters for sharing/iMessage). — [worklog gist](https://gist.github.com/stek29/4b15b02cf420223cc4c5b11e4870f5e0)
- malmeloo (FindMy.py maintainer): "There is no need to use any closed source binary dependencies for what we want to do. The closed source parts of rustpush are for anisette generation (which we've already nailed down) and something related to iMessage... they are now behind proper feature flags." (2026-03-31) -- contradicting mfcarroll's earlier claim (2025-10-19) that export needs rustpush's closed-source Network Absinthe Challenge component. — [FindMy.py issue #173](https://github.com/malmeloo/FindMy.py/issues/173)
- stek29 rebased the fork on latest OpenBubbles, ported a MobileMe-delegate parsing fix, but did NOT port upstream's switch to V2 authentication (needs validation data this headless CLI lacks; porting could break auth). Upstream at diagnosis time did not contain the 2FA-state-machine fix or the decryption-panic fixes. — [worklog gist](https://gist.github.com/stek29/4b15b02cf420223cc4c5b11e4870f5e0)

### Inferences
- The user's `BadMsg` signature-verification failure in `keychain.rs` during `join_clique_from_escrow` is plausibly tied to the un-ported V2 auth / newer-build escrow bottle changes (the user's failing bottle was escrowed July 2026, build 25F84 -- a macOS 26 build), while the stale Dec-2024 iOS 22B91 bottle joined but hit PCS/keychain decryption gaps. This matches the worklog's theme that newer Apple builds change escrow/keychain schemas faster than the fork tracks. (speculative -- no public issue confirms BadMsg specifically.)

### Gaps
- Could not read OpenBubbles/rustpush issue #18 or #11 directly (only via worklog summary); exact current upstream stance on a maintained export CLI not re-confirmed as of Oct 2026.
- No public changelog entry addressing macOS 26 / iOS 26 escrow signature-verification (`BadMsg`) changes in either rustpush tree.

## FindMy.py: built-in iCloud export plans and timeline

### Takeaway
FindMy.py does NOT yet have built-in iCloud export. The macOS 26 route is
documented only via the unmerged docs PR #260 pointing at export-findmy;
maintainer malmeloo calls the method experimental and intends to build it into
FindMy.py "hopefully soon" with CI-built binaries first. Latest release is
v0.10.2 (2026-09-14).

### Cited Findings
- **PR #260** by `MElkmeshi`, "docs: document macOS 26 (Tahoe) key export via export-findmy", opened `2026-08-14`, last updated `2026-10-10`, **state open, not merged**. Adds a README section because `python -m findmy decrypt` no longer works on macOS 26: the `BeaconStoreKey` is guarded by an Apple-only keychain access-group entitlement `com.apple.icloud.searchpartyuseragent`. Says the iCloud Keychain escrow route "works today, with no second Mac and without disabling SIP." Verified end-to-end on macOS 26.5.2 Apple Silicon. — [PR #260](https://github.com/malmeloo/FindMy.py/pull/260)
- malmeloo on PR #260 (2026-08-14): "this method is still a bit experimental and bound to change... This functionality will be built into FindMy.py directly at some point, hopefully soon. Let's reconsider this in a few weeks... I expect I will at least have a full CI pipeline implemented with releases. That way people won't have to compile it manually. Then we add it to the docs, I'll publish an announcement and we'll see if it breaks... If all works fine it will then be integrated into FindMy.py." — [PR #260 comment](https://github.com/malmeloo/FindMy.py/pull/260)
- Tracking issue **#173 "Import accessories from iCloud Keychain"** (open since 2025-09-11) lays out integration plan: build the rust blob via CI for all platforms, communicate anisette over JSONL stdin/stdout, (re)store rust-side session, ideally inherit FindMy.py's existing session (else reuse anisette to skip 2FA), export to FindMy.py JSON, wrap a Python API resembling the 2FA sign-in flow. — [issue #173](https://github.com/malmeloo/FindMy.py/issues/173)
- Issue **#177 "MacOS Accessory Dumping Compatibility"** matrix: macOS 14 works with `python -m findmy decrypt`; macOS 15 needs `pajowu/beaconstorekey-extractor` + `plist_to_json.py`; **macOS 26 = marked (fails)**. malmeloo is "hesitant to put effort into fixing [the decrypt script]... I'd rather work on getting rid of this hacky solution altogether." — [issue #177](https://github.com/malmeloo/FindMy.py/issues/177)
- Releases after 0.10.2: none. Release history: v0.10.2 (2026-09-14), v0.10.1 (2026-06-01), v0.10.0 (2026-05-04), v0.9.8 (2026-01-08). — [GitHub API /repos/malmeloo/FindMy.py/releases]
- Recent FindMy.py issues show ongoing fetch/alignment breakage independent of key export: #278 (closed) "Since 2026-10-12: mobileme returns only mmeAuthToken (no searchPartyToken)... report fetch 401"; #275/#274/#273 key-alignment issues for AirTag 2nd gen (Oct 2026). — [GitHub API search /repos/malmeloo/FindMy.py issues]

### Inferences
- As of 2026-10-26, no built-in export has shipped: PR #260 remains open/unmerged ~2 months later, no release past 0.10.2, and issue #173 still open. The "hopefully soon" from mid-August has not materialized into a release.
- The mid-October mobileme token change (#278) suggests Apple-side churn that could also affect the export path's auth, though that issue is about report fetching, not key export.

### Gaps
- No public FindMy.py branch/PR actually implementing the built-in rust-backed export yet (only the docs PR and the tracking issue); cannot date an implementation.

## Other tools: method, macOS 26 support, Apple-ID requirement, risk

### Takeaway
Only two routes reach keys over iCloud today: export-findmy (escrow join) and,
newly, OpenTagViewer's in-app "iCloud login method." Everything else
(beaconstorekey-extractor, searchparty-keys, OpenTagViewer's export wizard,
AirPinpoint) reads keys from a locally-signed-in Mac's files + keychain and is
OS-version-fragile; macless-haystack/OpenHaystack are for self-made tags, not
owner AirTag extraction.

### Cited Findings
- **OpenTagViewer** (`parawanderer/OpenTagViewer`, Android app, 444 stars, last push `2026-10-23`): now offers TWO ways to get keys -- (1) "Read them from iCloud, in the app (requires only your Android phone)" via an "iCloud login method" (owner of official Find My devices), and (2) export a `.zip` on a computer via CLI/Wizard then import. Only the account that OWNS a tag can export it; shared tags cannot be exported. — [OpenTagViewer README](https://github.com/parawanderer/OpenTagViewer)
- OpenTagViewer's maintainer (parawanderer) drove the cross-OS iCloud solution discussion and intended to deprecate the OS-version-bound export wizard: "All tools + workarounds that people came up with that are OS-bound broke on the latest release of MacOS (again), so this [iCloud] would be the only proper long-term way to do it." (2026-10-09) — [FindMy.py issue #177](https://github.com/malmeloo/FindMy.py/issues/177)
- OpenTagViewer's macOS export wizard is the Mac-local route (reads `OwnedBeacons`/`MasterBeacons` folders); users confirmed it works where `findmy decrypt` fails, incl. one on macOS 12.7.4. — [FindMy.py issue #177](https://github.com/malmeloo/FindMy.py/issues/177)
- **pajowu/beaconstorekey-extractor** (37 stars, last push `2025-04-16`): extracts the BeaconStore decryption key for the macOS 15 route; FindMy.py issue #177 recommends it for macOS 15 + `plist_to_json.py`. Local-Mac method. — [GitHub API /repos/pajowu/beaconstorekey-extractor]; [issue #177](https://github.com/malmeloo/FindMy.py/issues/177)
- **denysvitali/searchparty-keys** (Go): inputs are the `OwnedBeacons` folder (from macOS or iOS) + a BeaconStore decryption key taken from the Keychain; `generate-keys` emits private + advertisement keys per beacon. Requires local access to the beacon files and keychain key, not iCloud. Sample output dated 2024. A related `airy10` gist decrypts `~/Library/com.apple.icloud.searchpartyd` files while Find My runs. — [searchparty-keys (pkg.go.dev)](https://beta.pkg.go.dev/github.com/denysvitali/searchparty-keys); [airy10 gist](https://gist.github.com/airy10)
- **AirPinpoint** (commercial, ~$11.99/device/month, unlimited retention, no 32-tag Apple ID cap): setup runs on YOUR Mac where you are already signed into iCloud. Docs: "Sign into your iCloud account on the Mac User you want to use", "Full Disk Access is required to read protected system files containing FindMy data", "Xcode is required to read the FindMy device keys", and a Keychain prompt for your Mac password "grants access to your FindMy devices." Page does NOT state it collects your Apple ID credentials or logs into iCloud for you; it reads keys locally once ("nothing will be kept running on your Mac"). — [AirPinpoint setup docs](https://app.airpinpoint.com/docs/setup); [AirPinpoint location-history guide](https://airpinpoint.com/guides/airtag-location-history)
- **OpenHaystack** (`seemoo-lab/openhaystack`, 13.9k stars) and **macless-haystack** (`dchristl/macless-haystack`, 2.2k stars, last push 2026-03-15): frameworks to BUILD your own Find My tags (you generate the keys), not tools to extract an existing AirTag's Apple-held keys. OpenTagViewer explicitly supports importing self-made OpenHaystack/Macless-Haystack tags. — [GitHub API /repos]; [OpenTagViewer README](https://github.com/parawanderer/OpenTagViewer)

### Risk summary (per tool)
- export-findmy: **high risk** -- joins iCloud Keychain as a new synthetic Octagon peer, needs Apple password + 2FA + a real device passcode, and will mint new PCS master/service keys if missing (account-wide crypto side effects). iCloud route, macOS 26 only via unmerged PR #1.
- OpenTagViewer iCloud login: iCloud route, needs Apple ID login in-app; same class of concern as any third-party that authenticates to your Apple account (credentials + 2FA handled by the Android app). Owner-only.
- AirPinpoint: local-Mac route, needs iCloud already signed in on the Mac + Full Disk Access + Xcode + Mac password; does not (per docs) take your Apple ID password. Commercial, closed.
- beaconstorekey-extractor / searchparty-keys / OpenTagViewer wizard: local-Mac (or iOS files) route, no Apple ID login, but OS-version-fragile and broken on macOS 26.
- macless-haystack / OpenHaystack: not applicable to owner-AirTag key extraction.

### Gaps
- Could not read OpenTagViewer's wiki pages ("How-To: Connect Your iCloud Account") to confirm whether its in-app iCloud method uses the same escrow-join mechanism as export-findmy or a different approach; README confirms the capability but not the mechanism.
- find-my-timeline and FindMySync: not located as distinct current projects via available searches (no reliable source found) -- likely minor/renamed; treat as unconfirmed.
- AirPinpoint does not disclose where keys/data are sent or stored (points to support email).

## Security/privacy: joining iCloud Keychain as a synthetic peer

### Takeaway
Joining via an escrow bottle makes your exporter a trusted Octagon peer with
access to iCloud Keychain sync (including PCS-protected Find My data). It is a
real trust-circle member, carries account-wide crypto reach, and should be
removed after use; the self-created escrow bottle is deletable via the CLI, but
whether this fully departs the Octagon peer is not clearly documented.

### Cited Findings
- Octagon is Apple's trust system behind iCloud Keychain; a "clique" object handles trust operations, and joining a new device uses a bottle + entropy (the bottled-peer / escrow mechanism). Escrow recovery is "performed to attempt to join an account." — [Apple Security source: OTClique.h](https://opensource.apple.com/source/Security/Security-59306.80.4/keychain/ot/OTClique.h.auto.html); [OctagonTrustEscrowRecoverer.h](https://opensource.apple.com/source/Security/Security-59754.80.3/keychain/OctagonTrust/categories/OctagonTrustEscrowRecoverer.h.auto.html)
- Octagon supports removing peers: a peer can be dropped from the device list and remaining peers update trust to exclude it; there is a "depart" command to leave the trust circle; and a bottled-peer entry "can be scrubbed and deleted when it can never be used again." — [OctagonTests+DeviceList.swift](https://opensource.apple.com/source/Security/Security-59306.41.2/keychain/ot/tests/octagon/OctagonTests+DeviceList.swift.auto.html); [otctl.m](https://opensource.apple.com/source/Security/Security-59754.140.13/keychain/otctl/otctl.m.auto.html)
- export-findmy provides `--delete-own-escrow-bottle` to delete the exporter's self-created escrow bottle after extraction, and warns to verify metadata so you don't delete a real device's bottle. — [export-findmy README](https://github.com/stek29/export-findmy)
- Each successful join commits a new bottle to the account (worklog: a panicked run still left a 5th bottle on the account because the join was committed before the later panic), i.e., failed/interrupted runs can leave orphaned bottles/peers behind. — [worklog gist](https://gist.github.com/stek29/4b15b02cf420223cc4c5b11e4870f5e0)

### Inferences
- A peer joined via escrow gets the same iCloud Keychain sync access a new Apple device would, which is why it can read PCS-protected BeaconStore records; this is broad access, not scoped to Find My. Removing only the escrow bottle (recoverability) is not obviously the same as departing the Octagon peer from the trust circle -- so the synthetic peer may persist in trust even after bottle deletion. (speculative; not confirmed by export-findmy docs.)
- Whether the synthetic peer appears in the user's Apple ID device list is not documented; escrow bottles clearly are enumerable (the tool lists them by device name/model/serial), but trust-circle peer visibility in Settings is unconfirmed.

### Gaps
- No primary source confirms whether `--delete-own-escrow-bottle` issues an Octagon "depart"/peer removal, nor whether the synthetic peer/bottle shows in iCloud device lists or can be revoked from another Apple device.
- No security writeup specifically analyzing the risk of third-party escrow-based keychain joins for Find My export was found (only Apple's own source and general iCloud Keychain articles).
