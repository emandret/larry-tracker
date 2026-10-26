# Local (on-device) BeaconStore/OwnedBeacons key extraction on macOS 26 (Tahoe) + macOS VM route

Scope: whether any currently-known method (as of 2026-10-26) lets a user read the
BeaconStore keychain key or decrypt `~/Library/com.apple.icloud.searchpartyd/OwnedBeacons/*.record`
on macOS 26 on Apple Silicon, for loading into FindMy.py 0.10.2; plus whether a
macOS 14 (or earlier) VM on Apple Silicon can sign into iCloud and sync Find My items.

Local environment verified on this Mac (2026-10-26):
- `sw_vers`: macOS 26.6.2, build 25G83. `uname -m`: arm64. `hw.model`: Mac16,12.
- `security find-generic-password -l BeaconStore` => "The specified item could not be found in the keychain." (matches the known-context claim).
- SIP: `csrutil status` => "System Integrity Protection status: enabled."
- `~/Library/com.apple.icloud.searchpartyd/OwnedBeacons/` does not exist on this machine (directory absent -- likely Find My never populated it, or no owned accessory on this Mac). This is a verified local fact, not from a source.

Bottom line up front: As of 2026-10-26 there is **no known working local on-device method** to read the BeaconStoreKey or decrypt OwnedBeacons `.record` files on macOS 26. The macOS 15 SIP+AMFI workaround is reported broken on macOS 26. The macOS 14 VM route is a dead end (iCloud sign-in in a VM requires both host and guest on macOS 15+). The only route reported working on macOS 26 is a *non-local* iCloud Keychain **escrow** export over the network (stek29/export-findmy), which is out of scope of "local on-device" but documented below because it is the live path.

## What changed in macOS 15 and macOS 26 re BeaconStore key storage

### Takeaway
Since macOS 15 (Sequoia) the BeaconStoreKey is locked to an Apple-only keychain access group (`com.apple.icloud.searchpartyuseragent`), so only Apple-signed FindMy binaries can read it; macOS 26 additionally defeats the SIP/AMFI workaround that still worked on 15, leaving `security find-generic-password -l BeaconStore` and `findmy decrypt` dead on this machine.

### Cited Findings
- Since macOS 15 (Sequoia), the BeaconStoreKey can only be queried by binaries holding the correct keychain-access-group entitlement (`com.apple.icloud.searchpartyuseragent`); only Apple-signed binaries typically have it. -- [pajowu/beaconstorekey-extractor](https://github.com/pajowu/beaconstorekey-extractor); [DeepWiki summary](https://deepwiki.com/pajowu/beaconstorekey-extractor)
- Pre-macOS-15, the key was readable via `security find-generic-password -l "BeaconStore" -g` / `-w` and used to AES-GCM-decrypt the searchpartyd `.plist`/`.record` payloads. -- [hajekj/OfflineFindRecovery](https://github.com/hajekj/OfflineFindRecovery); [YeapGuy gist](https://gist.github.com/YeapGuy/f473de53c2a4e8978bc63217359ca1e4)
- airy10 (author of the widely-used decrypt script), 2025-02-07: "Apple changed the permissions on the keychain item in recent OS." Only FindMy-related Apple processes can now access it, and "there is no known workaround for now." -- [YeapGuy gist comment](https://gist.github.com/YeapGuy/f473de53c2a4e8978bc63217359ca1e4)
- A user on macOS 15.2 (M1), 2025-02-05, ran the decrypt script and got `SecItemCopyMatching status: -25300` and "The specified item could not be found in the keychain" -- confirming the lockout on 15.x. -- [YeapGuy gist comment](https://gist.github.com/YeapGuy/f473de53c2a4e8978bc63217359ca1e4)
- FindMy.py issue #177 (opened 2025-09-17 by maintainer malmeloo) compatibility table: macOS 14 = works (`python3 -m findmy decrypt`); macOS 15 = unconfirmed, use beaconstorekey-extractor + `plist_to_json.py`; **macOS 26 = marked broken (X), "See #176."** No method is reported working on macOS 26 in that thread. -- [FindMy.py issue #177](https://github.com/malmeloo/FindMy.py/issues/177)
- FindMy.py PR #260 (2026-08-14): on macOS 26 the built-in `python -m findmy decrypt` "no longer works there" because the BeaconStoreKey is "guarded by an Apple-only keychain access-group entitlement," which the docs previously called a "dead end (issue #177)." -- [FindMy.py PR #260](https://github.com/malmeloo/FindMy.py/pull/260)

### Inferences
- The macOS 15 restriction is an access-group/entitlement change (data-protection keychain), not merely a label change: the item is present but unreadable by non-Apple callers, which is why it surfaces as "item not found" / `-25300` rather than a permission-denied error.
- On macOS 26 the gating is effectively the same entitlement barrier, but the difference vs 15 is that the AMFI/SIP bypass that let a self-signed binary fake the entitlement no longer takes effect (see next section).

### Gaps
- No official Apple Platform Security guide text or developer doc was found that names BeaconStoreKey or the macOS 15/26 access-group change; all sourcing is third-party projects and the FindMy.py maintainers. Issue #176 (the referenced macOS 26 tracking issue) was not fetched; its exact contents are unconfirmed here.

## macOS 15 workarounds and whether any work on macOS 26

### Takeaway
The published macOS 15 workaround (SIP off + AMFI disabled via `amfi_get_out_of_my_way=1` + a developer-signed binary carrying the searchparty keychain-access-group entitlement) is explicitly reported to **no longer help on macOS 26**; no LLDB/Frida/memory-dump local method is documented as working on 26.

### Cited Findings
- pajowu/beaconstorekey-extractor README (derived from seemoolab's airdrop-keychain-extractor): "should work at least for macOS 15 (Sequoia)"; does **not** mention macOS 26, so Tahoe is unconfirmed/unsupported there. Steps: (1) in Recovery, `csrutil enable --without nvram`, reboot; (2) `sudo nvram boot-args="amfi_get_out_of_my_way=1"`, reboot (disabling AMFI/amfid so the entitlement check is bypassed); if it still fails, `csrutil disable` fully; (3) build+run (`make run`) with a developer certificate and the repo's `entitlements.plist`; it prints the key; (4) restore with `nvram -d boot-args` + `csrutil enable`; (5) `make decrypt` with the printed key. Re-enabling SIP means you must repeat extraction to get the key again, so save the key. "used at the user's own risk." -- [pajowu/beaconstorekey-extractor README](https://github.com/pajowu/beaconstorekey-extractor)
- liamschwie/find-my-timeline README, section "Getting the keys on macOS 15 and later": "on macOS 26 the SIP-disabling workaround no longer helps either"; and "On those versions `import-keys` cannot succeed, and says so." It implies macOS 14 or earlier works for local extraction; 15 and 26 do not. Recommended alternative: export keys on a macOS 14-or-earlier Mac (or via OpenTagViewer), then `import-keys --from` (accepts findmy `.json` or decrypted `.plist`; rejects still-encrypted `.record`). -- [liamschwie/find-my-timeline README](https://github.com/liamschwie/find-my-timeline)
- No Frida-based method and no reliable LLDB memory-dump write-up targeting BeaconStoreKey were found. A general macOS memory-dumping guide mentions LLDB can capture process memory, but nothing ties it to this key on any macOS version, let alone 26. -- [cyberlibrary macOS memory dumping](https://www.cyberlibrary.fr/en/docs/old/macos-memory-dumping); (negative result on Frida/LLDB specifics)
- Required security reductions for the macOS 15 method: SIP disabled (fully, or `--without nvram`) + AMFI disabled via boot-arg; these are set in Recovery and on Apple Silicon require lowering the boot policy to Reduced Security / "Permissive" to allow the boot-args and kext/AMFI changes. (The README uses `csrutil` + `nvram boot-args`, which on Apple Silicon require Reduced Security.) -- [pajowu/beaconstorekey-extractor README](https://github.com/pajowu/beaconstorekey-extractor)

### Inferences
- The macOS 15 method worked by using AMFI disablement to let an ad-hoc/developer-signed binary present the `com.apple.icloud.searchpartyuseragent` keychain-access-group entitlement without Apple's signature; macOS 26 apparently enforces the access group independently of AMFI (or validates it via a path AMFI-off no longer covers), which is why disabling SIP/AMFI "no longer helps." This is an inference from the two READMEs; the exact enforcement mechanism change on 26 is not documented in the sources found.
- Because no local method is reported working on 26, LLDB-attaching to `searchpartyd`/FindMy or dumping its memory is the only theoretically-remaining local avenue, but it is speculative: SIP must be off to attach to Apple system daemons, and no source reports success on 26.

### Security / account risks (flagged per method)
- SIP off + AMFI off + Reduced Security boot policy: broadly weakens the Mac. Documented/known side effects of this posture include Apple Pay being disabled, and some iCloud/DRM and iOS-app-on-Mac functionality breaking while security is reduced; it is reversible by restoring SIP/boot-args and raising the boot policy, but requires reboots in Recovery. (The extractor README only warns generically "temporarily disables security features ... at your own risk"; the specific Apple Pay/iOS-app side effects are general Apple-Silicon Reduced-Security consequences, not stated in that README -- treat as known-platform-behavior, verify if load-bearing.)
- The extracted key material lets whoever holds it track the owner's devices (including offline) -- treat the key and decrypted plists as passwords. -- [beaconstorekey-extractor caution](https://github.com/pajowu/beaconstorekey-extractor); [YeapGuy gist](https://gist.github.com/YeapGuy/f473de53c2a4e8978bc63217359ca1e4)

### Gaps
- Nobody in the sources reports testing the SIP/AMFI extractor on macOS 26 and documenting the exact failure; the "no longer helps" claim is liamschwie's README assertion, not a step-by-step failure log.
- Whether an LLDB/Frida attach to searchpartyd succeeds on macOS 26 with SIP off is untested in any source found.

## Tools / projects implementing or discussing these

### Takeaway
The active ecosystem (FindMy.py maintainers, find-my-timeline, OpenTagViewer, Lost_Apples, searchparty-keys) has converged on "local extraction is dead on 15/26; use a macOS 14 export or the network escrow route"; the one macOS-26-live tool is stek29/export-findmy via iCloud Keychain escrow (not a local keychain read).

### Cited Findings
- **stek29/export-findmy** -- exports AirTag/FindMy accessory private keys from iCloud into `.plist`/`.json` compatible with FindMy.py. Flow: SRP auth + 2FA -> MobileMe delegate tokens via the iOS `iosbuddy` login endpoint -> **joins the iCloud Keychain trust circle via escrow recovery using a device passcode** -> fetches encrypted `BeaconStore` records from **CloudKit** -> decrypts with PCS keys from the keychain -> writes plist/json. README: "Tested on MacOS 26." Requires Apple ID password (prompted, hidden), a device passcode for an existing escrow device (e.g. an iPhone already in your iCloud Keychain), Rust + `openssl` + `protoc`. Recommends `--delete-own-escrow-bottle` after; warns "Never delete a bottle belonging to a real Apple device." Only the trusted-device 2FA flow is live-tested. -- [stek29/export-findmy README](https://github.com/stek29/export-findmy)
- **FindMy.py PR #260** (MElkmeshi, 2026-08-14) documents using export-findmy for macOS 26: "The iCloud Keychain escrow route works today, with no second Mac and without disabling SIP." Author reports verifying on macOS 26.5.2 (Apple Silicon) by exporting an AirTag's keys and fetching a live location. Maintainer malmeloo (2026-08-14): "this method is still a bit experimental and bound to change"; "This functionality will be built into FindMy.py directly at some point, hopefully soon"; "Let's reconsider this in a few weeks." PR is **open, unmerged, no reviews** as of fetch. -- [FindMy.py PR #260](https://github.com/malmeloo/FindMy.py/pull/260)
- **stek29/export-findmy PR #1** "Use native macOS anisette (AOSKit); fix export on macOS 26 (Tahoe)" (MElkmeshi, 2026-08-14) -- **open, not merged**, single commit 8ed58dc. Fixes macOS 26 where export failed despite successful auth: (1) remote/emulated anisette failed provisioning (`provision.adi.ADIException ... -45054` -> EndProvisioningError); (2) client sent an iPhone OS marker in `X-Mme-Client-Info`, so Apple's gateway rejected the MobileMe delegate with status:1. Fix derives the OS marker from device model and uses native anisette (AOSKit via omnisette) -- "the real system ADI" / "the Mac's real Apple Device Identity," no remote server; on macOS this becomes default and ignores `--anisette-url`. Author tested on macOS 26.5.2 (Mac15,6), exported an AirTag. -- [stek29/export-findmy PR #1](https://github.com/stek29/export-findmy/pull/1)
- **FindMy.py issue #177** thread (through 2026-04): macOS 14 confirmed working with `python3 -m findmy decrypt`; macOS 11 works but uses older "MasterBeacons" folder (rename to "OwnedBeacons"); maintainer points to issue #173 "Fully macless accessory dumping" where "someone made some huge progress recently" (2026-04-08); a contributor (smoothscholar) got the macless tool working 2026-04-09, noting "the key only needs to be pulled once per tag." -- [FindMy.py issue #177](https://github.com/malmeloo/FindMy.py/issues/177)
- **joshuahickman1/Lost_Apples** (forensic) and **thebinaryhick.blog "Old Dog, New Tricks," 2026-03-22**: Lost Apples 2.0 decrypts OwnedBeacon plist files and computes primary/secondary key schedules, but the blog does **not** describe how to obtain the key on macOS 15/26; for iPhone/iPad it states "a FFS [full file system] extraction is needed along with the associated keychain," not available from an iTunes backup or logical extraction -- i.e. it assumes forensic key access, not a live macOS read. -- [thebinaryhick.blog Old Dog New Tricks](https://thebinaryhick.blog/2026/03/22/old-dog-new-tricks-lost-apples-2-0/); [joshuahickman1/Lost_Apples](https://github.com/joshuahickman1/Lost_Apples)
- **denysvitali/searchparty-keys** (Go): takes the BeaconStore key as *input* to derive keys from an OwnedBeacons record -- it consumes a key you already have, it does not extract it. -- [searchparty-keys](https://github.com/denysvitali/searchparty-keys)
- OpenTagViewer is cited by find-my-timeline as an alternative way to export keys (for feeding `import-keys --from`); details not independently fetched. -- [liamschwie/find-my-timeline](https://github.com/liamschwie/find-my-timeline)

### Inferences
- The escrow route (export-findmy) is genuinely different from the "local BeaconStore keychain read": it recovers key material from the iCloud Keychain **escrow service over the network via CloudKit**, so it sidesteps the local access-group entitlement entirely. It is the only thing reported working on macOS 26, but it is "macless-ish" (needs an Apple ID + an existing escrow device passcode) rather than reading the local `.record` files. If the larry-tracker goal is simply "get keys FindMy.py can load on macOS 26," this is the current path; if the goal is strictly local `.record` decryption, that remains unavailable.
- Both macOS-26 fixes depend on one contributor (MElkmeshi) and are unmerged/experimental as of 2026-08-14; the maintainer expects churn -- treat as fragile.

### Gaps
- Merge status after 2026-08-14 not reconfirmed (fetch reflects state at crawl time). FindMy.py 0.10.2's exact `FindMyAccessory.from_plist`/`decrypt_plist` behavior vs these exported files was not separately verified, though the tools advertise FindMy.py-compatible output.
- Issue #173 / #176 contents not fetched in full.

## macOS VM route (Apple Silicon)

### Takeaway
A macOS 14 (Sonoma) or earlier guest **cannot sign into Apple ID / iCloud at all** -- Apple requires **both host and guest to run macOS 15.0+** -- so the "run old macOS in a VM to use the dead-simple local decrypt" plan is a dead end; and a macOS 15+ VM inherits the same BeaconStore access-group lockout as bare metal.

### Cited Findings
- Apple's Virtualization framework supports iCloud / Apple Account sign-in in macOS guests only since macOS 15 Sequoia, and requires macOS 15+ as **both guest and host**; older guests/hosts do not qualify. -- [Apple Developer Forums thread 707682](https://developer.apple.com/forums/thread/707682); [Michael Tsai blog, 2024-06-13](https://mjtsai.com/blog/2024/06/13/using-apple-accounts-with-macos-virtual-machines/); [Daring Fireball, 2024-06-12](https://daringfireball.net/linked/2024/06/12/macos-15-vms-icloud)
- eclecticlight.co (2026-04-29): iCloud support "wasn't made available in VMs until Sequoia" and "now requires that both the guest and host must be running macOS 15.0 or later." VMs upgraded from an earlier macOS "still can't support iCloud or iCloud Drive." A VM "can't be signed into the App Store." -- [eclecticlight.co](https://eclecticlight.co/2026/04/29/virtualisation-on-apple-silicon-macs-is-different/)
- Only brand-new VMs created from a macOS 15+ install image (.ipsw) can use iCloud; upgrading an older VM to 15 does not unlock it. Feature is Apple-Silicon-only. -- [heise.de](https://www.heise.de/en/news/macOS-as-a-virtual-machine-Apple-removes-annoying-iCloud-restriction-9760690.html); [MacObserver](https://www.macobserver.com/mac/mac-virtual-machines-now-support-icloud-in-macos-sequoia/)
- Each VM gets its own identity derived from the host's Secure Enclave; moving the VM to another Mac host forces re-authentication to resume iCloud sync. -- [Apple Developer Forums thread 707682](https://developer.apple.com/forums/thread/707682) (as summarized across sources)

### Inferences
- Even a compliant macOS 15+ VM does not help: it can sign into iCloud, but the BeaconStoreKey in a 15+ environment is behind the Apple-only access group, identical to bare-metal 26 -- so `findmy decrypt` / `security find-generic-password` fail inside the VM too. The VM buys nothing for local extraction.
- The only thing a VM could theoretically offer is a macOS 14 environment with the old readable keychain; but since a macOS 14 guest cannot join iCloud/iCloud Keychain, no Find My owned-beacon key material would ever sync into it. Both halves of the VM plan fail. (Inference from the combined version requirement + the 14-works/15-broken extraction facts.)
- Whether Find My owned-accessory items specifically sync into a macOS 15+ VM's iCloud Keychain is not directly documented; but it is moot given the access-group lockout.

### Gaps
- No source explicitly tested "Find My items syncing into a VM" or running beaconstorekey-extractor inside a VM; the conclusion is inferred from the version requirement plus the 15/26 lockout.
- Intel-Mac / real-hardware-downgrade alternatives for running macOS 14 with iCloud (on genuinely old hardware that supports 14) were not researched in depth; on supported older hardware macOS 14 does sign into iCloud normally and the old local decrypt worked there (per issue #177 "macOS 14 = works"), but that requires hardware whose latest-supported OS is <= 14, which this Mac is not.

## Older-OS / external-disk route on this Mac (Mac16,12)

### Takeaway
This Mac (Mac16,12, M4 MacBook Air) shipped with macOS 15.3 as its minimum and **cannot boot macOS 14 or earlier** (bare metal or external disk), so the "boot macOS 14 to use the old local decrypt" option is not available on this hardware.

### Cited Findings
- A reseller spec listing for the 13-inch M4 MacBook Air (model ID Mac16,12) states it supports macOS 15.3 Sequoia through macOS 26.x Tahoe and ships pre-installed with macOS 15.3 or later; oldest supported OS can vary slightly by manufacture date. -- [eshop.macsales.com (Mac16,12 listing)](https://eshop.macsales.com/item/Apple/KQ1HS33XXXXXB/)
- Mac16,12/Mac16,13 first appeared referenced in the macOS 15.2 software (MacRumors / Notebookcheck), consistent with a Sequoia-era launch. -- [Notebookcheck](https://www.notebookcheck.net/MacOS-15-2-gives-away-clues-about-new-MacBook-releases.931446.0.html)

### Inferences
- Apple Silicon Macs cannot boot a macOS older than the build they shipped with; with a 15.3 floor, macOS 14 will not install or boot on this machine on internal or external disk. So the externally-booted-old-macOS path is closed here (even setting aside that macOS 14's local decrypt path needs a keychain that only populates when signed into iCloud on 14, which is fine on real 14 hardware but impossible on this Mac).

### Gaps
- The 15.3 minimum comes from a third-party reseller listing, not Apple's official tech-specs page (Apple spec page not fetched). The general Apple-Silicon rule "cannot boot an OS older than the shipping build" is well-established platform behavior but not cited to a specific doc here.
