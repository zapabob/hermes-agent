# Hermes Agent Windows Workstation Edition

<p align="right">
  <a href="README.md"><kbd>English</kbd></a>
  <a href="README.ja.md"><kbd>日本語</kbd></a>
  <a href="README.zh-CN.md"><kbd>简体中文</kbd></a>
</p>

> [!NOTE]
> 英語版の `README.md` が正本です。この日本語版は英語版に追随します。

Hermes Agent の Windows ファーストなダウンストリーム・ディストリビューションです。

これは非公式のダウンストリーム・ディストリビューションです。
Nous Research との提携関係はなく、同社による承認も受けていません。
オリジナルの Hermes Agent は Nous Research によって開発され、MIT License の下で提供されています。

[![Windows Workstation Tier-1 CI](https://github.com/zapabob/hermes-agent-windows/actions/workflows/fork-cicd.yml/badge.svg)](https://github.com/zapabob/hermes-agent-windows/actions/workflows/fork-cicd.yml)

Windows 11 AI ワークステーション向けに、Windows ネイティブで継続的に認定する
Hermes のダウンストリーム・ディストリビューションです。

- Python、Electron、Go、upstream API 互換、regression、security lock の Windows Tier-1 CI
- 非管理者・空白入り path を含む installer、portable、旧版からの upgrade E2E
- 移動しない upstream snapshot `1fe0f2f3ac9748ce799272eb93bee2937b5ab802`
- 公式 provider/memory seam 上の local llama.cpp/GGUF と embedding lifecycle
- Desktop/backend と任意 embedding を限定的に復旧する外部 Go watchdog
- GPU のない hosted CI と分離した consumer NVIDIA workstation の実機証拠

release candidate は `0.20.5-win.1`、対応 channel は `stable` と `preview` です。
認定済み成果物は対応 tag からのみ
[ダウンストリーム Releases](https://github.com/zapabob/hermes-agent-windows/releases)
へ公開します。最初の stable asset が存在するまでは source route を使用し、先行した
direct download button は表示しません。
[Windows 導入ガイド](docs/windows/INSTALL.md)、
[release policy](docs/windows/RELEASE_POLICY.md)、
[公式 upstream](https://github.com/NousResearch/hermes-agent)も参照してください。

## 1. 製品の位置づけ

Hermes Agent Windows Workstation Edition は、常時稼働するローカル AI
ワークステーション向けに機能を拡張した、Windows ファーストのダウンストリーム・
ディストリビューションです。Hermes CLI コマンド、公開契約、プラグインモデル、
upstream の履歴を維持しながら、Windows ネイティブ動作、ローカルモデル、メモリ、
音声、VR/Unity、復旧について明確なダウンストリーム方針を定めています。

製品台帳は [FEATURES.yaml](FEATURES.yaml) です。upstream 所有ファイルに保持する
直接パッチは [CARRY.yaml](CARRY.yaml) で別途追跡します。

## 2. Windows ファーストの目標

主対象は、ネイティブ Python、ネイティブ Node/Electron、対話型デスクトップ、
コンシューマー向け NVIDIA GPU を備えた Windows 11 x64 です。ローカル LLM と
embedding サービス、音声サービス、VRChat/Unity 連携、リモート管理を含む継続運用を
想定して設計しています。

Windows は upstream のプラットフォーム優先順位とは独立した Tier-1 対象です。
ネイティブ動作は `windows-latest` でテストし、Linux 上のクロスコンパイルは
Windows ランタイムの証拠として認めません。

## 3. 対象ユーザー

このディストリビューションは、Windows AI ワークステーションを運用し、ローカル推論、
長時間稼働サービス、メモリ、デスクトップ動作、復旧をソースレベルで管理する必要がある
オペレーターと開発者を対象としています。PowerShell、Git、Python 環境、Node
ツール、CI 結果の確認に慣れていることを前提とします。

最も簡潔な公式 Hermes の導入方法と upstream のサポートモデルを利用する場合は、
第 15 節のオリジナルプロジェクトを使用してください。

## 4. ダウンストリームの利点

このダウンストリームは、Windows ネイティブのランタイムと復旧契約、外部 Go
watchdog、ローカル llama.cpp/GGUF と embedding のライフサイクル、ローカル秘書と
provider 連携、semantic memory と cognitive memory の拡張、VRChat/Unity と
ローカル音声経路、OSINT/Shinka 拡張、Desktop の Git/review 画面、追加の
security と provider fallback のカバレッジを提供します。

これらの機能は公式 Hermes API と組み合わせて動作します。この fork は session、
approval、profile、gateway、model catalogue、tool registry について、並行する別の
正本を作りません。

## 5. 検証済み機能マトリクス

| 分野 | 検証済み実装 | 契約の証拠 |
| --- | --- | --- |
| Windows runtime | ネイティブ path、process、IPC、NTFS handoff、terminal、credential、power、GPU helper | `tests/downstream/test_windows_contracts.py` |
| Recovery | 外部 Go watchdog と watchdog 管理の Desktop backend | `scripts/windows/watchdog-go/*_test.go` |
| Local inference | llama.cpp/GGUF fallback と hot-swap script | `tests/hermes_cli/test_llama_fallback_runtime.py` |
| Local embeddings | watchdog embedding lifecycle と semantic graph backend | `scripts/windows/watchdog-go/embedding_test.go` |
| Local secretary | 公式 agent boundary 上の read/write action 分離 | `tests/downstream/test_upstream_api_contracts.py` |
| Providers | Hypura/local provider 連携と provider rotation/fallback | `tests/fork/test_hypura_oai_proxy.py` |
| Memory | Semantic Graph hybrid retrieval と Ebbinghaus cognitive extension | `tests/plugins/test_semantic_graph_registration.py` |
| VR and Unity | VRChat autonomy tooling と Unity bridge | `tests/plugins/test_vrchat_autonomy_plugin.py` |
| Voice | Irodori、VOICEVOX、local TTS route | `tests/plugins/test_irodori_tts_plugin.py` |
| AITuber | AITuber OnAir と AITuber Kit plugin | `tests/plugins/test_aituber_onair_plugin.py` |
| OSINT/Shinka | Shinka、SitDeck、WorldMonitor、OSINT plugin surface | `tests/plugins/test_shinka_osint_plugin.py` |
| Desktop | 公式 Desktop IPC と pane contract を用いた Git/review extension | `apps/desktop/electron/git-review-ops.test.ts` |
| Security | security guidance と強化された approval/execution boundary | `tests/plugins/test_security_guidance_plugin.py` |

機能ごとの所有者、公開 surface、upstream との重複、Windows 要件、テスト、統合方針は
すべて `FEATURES.yaml` に記録しています。

## 6. Windows Tier-1 サポート契約

Tier-1 の対象には、ネイティブ drive path、MSYS `/c/...` とサポート対象の WSL
`/mnt/c/...` alias、NTFS lock、ロック中の executable と extension module の
update、process tree、適用可能な Job Object 動作、PowerShell quoting、Git Bash
boundary、CP932/UTF-8 boundary、CRLF、venv `Scripts\\`、Electron stdio pipe が
含まれます。

ランタイム認定では、sleep/resume、network と loopback provider の復旧、Desktop
再起動、updater handoff、watchdog 復旧、llama restart と hot-swap、embedding
restart、profile/session persistence を検証します。規範となる契約は
[.codex/WINDOWS_PLATFORM_CONTRACT.md](.codex/WINDOWS_PLATFORM_CONTRACT.md) です。

## 7. ローカル AI アーキテクチャ

公式 Hermes の provider と model catalogue の契約を正本とします。ダウンストリームの
ローカルランタイムは、llama.cpp/GGUF を local fallback runtime、Hypura を
provider plugin seam、local embedding を Semantic Graph backend と watchdog 管理の
loopback service により、これらの契約へ接続します。

オペレーター用 script は `scripts/windows/` 配下に置きます。ランタイム plugin の
entrypoint は `plugins/` 配下に保ち、公式 discovery が引き続き機能するようにします。

## 8. Watchdog と復旧のアーキテクチャ

`scripts/windows/watchdog-go` は、外側に置かれる唯一の自動再起動権限です。packaged
Desktop の監視、prewarmed backend manifest の公開、設定済み local embedding
process の調整を行えます。Desktop、backend、llama、embedding の各 component は
health 公開や復旧要求を行えますが、独立した自動再起動 loop は形成しません。

ダウンストリームの Python service module は副作用のない契約です。実際の operator
startup と deployment は `scripts/windows/` 配下の PowerShell と Go surface に
残します。
## 9. メモリと semantic retrieval

Semantic Graph plugin は、公式 plugin interface と memory interface を通して、graph
storage、hybrid retrieval、embedding、fusion、abstention、cognitive helper を
提供します。Ebbinghaus provider は experience と retention policy を追加し、
Semantic Graph に bridge できます。両者とも独立した plugin entrypoint と対象を
絞った test suite を維持します。

## 10. VRChat、Unity、音声の統合

VRChat autonomy tool、observation/relay helper、Unity bridge package、VOICEVOX、
Irodori、その他の local TTS route は、ダウンストリーム所有の機能です。core を VR
または voice 専用 runtime に変更せず、公式の plugin、tool、TTS contract を使用します。

外部への公開と書き込み action は、引き続き明示的な approval を必要とします。local
generation は、外部 account への公開や変更を許可するものではありません。

## 11. インストール

Windows release workflow は、ユーザー単位の NSIS installer と portable ZIP を作成し、
stable tag で公開する前に clean install、起動、upgrade E2E を実行します。公開済みの
成果物は
[ダウンストリーム Releases](https://github.com/zapabob/hermes-agent-windows/releases)
からのみ取得し、`SHA256SUMS.txt` を確認してください。現在の candidate は
`release-manifest.json` に別の記録がない限り unsigned です。手順の正本は
[docs/windows/INSTALL.md](docs/windows/INSTALL.md) です。

source/development route は PowerShell から引き続き利用できます。

```powershell
git clone https://github.com/zapabob/hermes-agent-windows.git
Set-Location hermes-agent-windows
uv sync --locked --all-extras
uv run hermes --version
uv run hermes setup
```

Desktop 開発と source build は次のとおりです。

```powershell
npm ci
npm --workspace apps/desktop run typecheck
npm --workspace apps/desktop run build
```

24 時間稼働の service や Scheduled Task を有効にする前に、設定を確認してください。
API key と token は profile ごとの Hermes secret store、または Hermes の文書に従って
`.env` に保存し、secret ではない設定は `config.yaml` に保存します。

## 12. 更新と upstream 統合の方針

upstream は統合対象であり、ダウンストリーム製品の正本ではありません。各 campaign では
`.codex/UPSTREAM_SNAPSHOT.json` に正確な SHA を固定し、commit を
`UPSTREAM_ADOPTION.yaml` で分類し、直接保持する変更を `CARRY.yaml` に記録します。
`scripts/upstream/snapshot_sync.py` は明示的な SHA を受け取り、変動する最新 branch を
解決しません。

公式の public API を優先します。security と data integrity の修正は、検証済みのより
強いダウンストリーム特性と組み合わせます。upstream に似た名前の機能が加わったという
理由だけでダウンストリーム機能を削除せず、置き換えには parity の証拠を要求します。

## 13. アーキテクチャ

fork 所有の Python boundary は `downstream/` 配下に置きます。`compat/hermes` は公式
contract へ委譲し、`platform/windows` は native policy を所有し、`services` は
long-lived service contract を定義し、`features` は product ledger を検証します。
意図的に `platform` という名前の top-level Python package は設けません。

Hermes core は引き続き狭い共通境界です。plugin と skill が capability を保持し、
profile-aware な公式 path helper が state path を所有し、prompt cache と message role
の invariant は必須です。

## 14. セキュリティ

secret、個人の runtime data、profile database、model file、local artifact、生成された
credential を commit しないでください。write、publish、destructive、shell action は
明示的な approval の内側に置きます。child service の environment には ambient
credential を継承させず、必要な variable だけを渡してください。

security gate は、lock 済み Python graph、Python advisory、production npm advisory、
Go module integrity、OSV result、supply-chain policy、この repository の security
regression test を検査します。green の local unit test は、exact-head CI や live
runtime evidence の代わりにはなりません。

## 15. Upstream プロジェクト

オリジナルの Hermes Agent は Nous Research が保守しています。
[NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent)

公式 upstream の installer、website、documentation、issue tracker、support channel は
upstream distribution に適用されます。このダウンストリーム repository を install
または endorse するものではありません。

## 16. ライセンスと帰属表示

このダウンストリームには、引き続きリポジトリの MIT License が適用されます。
オリジナル Hermes Agent の copyright と contributor history は保持されています。
ダウンストリームの作業は fork contributor によって独立して保守され、upstream と
downstream の issue、release、製品上の主張は明確に区別する必要があります。
