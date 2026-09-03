// Hermes Agent Windows Workstation - Multilingual Dictionary
// Supported Locales: en-GB (King's English), ja (Japanese), zh-CN (Simplified Chinese)

const translations = {
  "en-GB": {
    meta: {
      title: "Hermes Agent Windows Workstation | Re-centring the OS around Autonomous Intelligence",
      description: "Moving beyond adding AI to an IDE. A high-performance Windows AI workstation engineered for persistent, 24/7 autonomous agents.",
      langLabel: "English (UK)"
    },
    nav: {
      brand: "Hermes Workstation",
      edition: "Windows Edition",
      paradigm: "Paradigm Shift",
      features: "Key Architecture",
      security: "Security Centre",
      metrics: "Live Statistics",
      quickstart: "Quick Start",
      github: "GitHub Repository",
      readArticle: "Read Original Article"
    },
    hero: {
      badge: "Open Source AI Workstation for Windows",
      headline: "Ceasing to merely attach AI to an IDE.",
      subheadline: "Re-centring the entire Windows operating system around autonomous agents.",
      lead: "Traditional IDEs place the human at the centre of a manual loop. For an autonomous agent that operates 24/7, the entire OS environment—Git operations, web research, local LLM inference, cognitive memory, and ClamAV/YARA security—must be consolidated into a unified workstation.",
      primaryCta: "Explore on GitHub",
      secondaryCta: "Read Zenn Article",
      copyCommand: "git clone https://github.com/zapabob/hermes-agent-windows.git",
      copied: "Command Copied to Clipboard!",
      statClones: "9,808+",
      statClonesLabel: "Git Clones (14 Days)",
      statCloners: "237+",
      statClonersLabel: "Unique Developers",
      statComposed: "723+",
      statComposedLabel: "Upstream Recomposed Commits",
      statUptime: "24/7",
      statUptimeLabel: "Go Watchdog Resilience"
    },
    paradigm: {
      sectionTitle: "Paradigm Shift",
      sectionSubtitle: "From 'IDE with an AI Plugin' to an 'Agent-Centric Workstation'",
      quote: "Why must an autonomous AI be confined to a miniature chat drawer inside an editor designed for humans? If the agent is doing the heavy lifting, the entire workstation must serve its operational lifecycle.",
      traditionalTitle: "The Conventional Developer Loop (Human-Centric)",
      traditionalDesc: "Optimised solely for human fingers typing into a text buffer.",
      agentTitle: "The Autonomous Agent Operational Loop (Workstation-Centric)",
      agentDesc: "Coding is merely one step. The agent must research, reason, audit, automate, and recover autonomously.",
      loopCompareNote: "Fragmenting this across disconnected terminal windows and browser tabs destroys context. Hermes Workstation unifies the complete surface on a singular canvas."
    },
    showcase: {
      sectionTitle: "Workstation in Action",
      sectionSubtitle: "Real Screenshots from the Operational Windows Desktop",
      tabHome: "Agent Desktop & Integrated Browser",
      tabSecurity: "Security Centre & Quarantine Manager",
      homeCaption: "The Hermes Agent Home Desktop: Unified chat core flanked by live social/web research panes, session switcher, and real-time Git repository workspace.",
      securityCaption: "The Built-in Security Centre: Active file integrity monitoring, ClamAV/YARA scan engine, and automated quarantine to safeguard autonomous execution.",
      clickToZoom: "Click image to inspect high-resolution details",
      legendTitle: "Integrated Panes",
      legendLeft: "Left: Session hierarchy, Telegram, Discord, Cron scheduler, & Kanban",
      legendCentre: "Centre: High-contrast Agent reasoning canvas & Local LLM orchestrator",
      legendRightTop: "Top-Right: Built-in Chromium browser pane for live web verification",
      legendRightBottom: "Bottom-Right: Interactive Git operations tree & human review diffs"
    },
    pillars: {
      sectionTitle: "Five Structural Breakthroughs",
      sectionSubtitle: "What Radically Sets Hermes Workstation Apart from Conventional Setups",
      p1Title: "1. Co-equal Git Operations for Human & Agent",
      p1Desc: "A first-class Git repository tree is permanently docked on the right. Both human and agent execute commits, review branch diffs, operate worktrees, and supervise workspace health concurrently—eliminating window-hopping fatigue.",
      p2Title: "2. The Web Browser as a Native Workspace Pane",
      p2Desc: "Rather than relying on disjointed external applications, Chromium is deeply integrated into the desktop canvas. The agent's autonomous navigation synchronises seamlessly with human visual oversight.",
      p3Title: "3. An Integrated Security Centre (ClamAV & YARA)",
      p3Desc: "Giving an agent unrestricted local disk writing, shell invocation, and external MCP tools demands real-time threat telemetry. A built-in security console scans files, inspects malware hashes, and isolates suspicious artefacts.",
      p4Title: "4. External Go Watchdog: Surviving 24/7",
      p4Desc: "Prevents memory leaks and silent process deaths. Implements a strict 'Single Authority for Restarts' via an external Go daemon, avoiding cascading supervisor failures and guaranteeing genuine 365-day uptime.",
      p5Title: "5. Ebbinghaus Cognitive Memory with Semantic Graphs",
      p5Desc: "Dumping endless raw chat logs into model prompts degrades reasoning. Hermes implements true cognitive long-term memory: hybrid vector search, semantic knowledge graphs, and mathematical forgetting-curve decay.",
      p6Title: "6. Embodiment: Voice, Unity & VRChat",
      p6Desc: "Not merely a terminal output: integrates VOICEVOX local TTS, OSC control protocols, and virtual avatar pipelines for AITuber operations and physical presence in 3D worlds."
    },
    security: {
      sectionTitle: "Enterprise-Grade Defence for Agent Agency",
      sectionSubtitle: "Why Does an AI Workstation Require an Anti-Virus Console?",
      intro: "Demoware can afford to disregard security. But when you entrust an agent with raw shell privileges, file-system write authority, and autonomous network tools for 24 hours a day, observability and quarantine become non-negotiable.",
      layerHeader: "Protection Layer",
      engineHeader: "Technology & Engines",
      row1Layer: "Malware & Exploit Detection",
      row1Engine: "ClamAV 1.5.4 / YARA Rules / Windows Defender",
      row2Layer: "File Integrity & Reputation",
      row2Engine: "Cryptographic Hash Reputation & Heuristics",
      row3Layer: "Isolation & Defusal",
      row3Engine: "Automated Quarantine Manager & Process Bounds",
      row4Layer: "Audit & Forensic Trail",
      row4Engine: "Continuous Tool Execution & Terminal History Logs"
    },
    sync: {
      sectionTitle: "Under the Bonnet: Upstream Synchronization",
      sectionSubtitle: "How We Keep Pace with Nous Research's Rapid Evolution",
      lead: "A blind 'git merge upstream/main' destroys downstream Windows optimisations in seconds. We operate a disciplined Semantic Integration Pipeline that categorises every upstream commit:",
      adoptTitle: "ADOPT",
      adoptDesc: "Directly accepted upstream enhancements.",
      composeTitle: "COMPOSE (70%+)",
      composeDesc: "Re-engineered to align with Windows permissions, ConPTY bridge, and multi-threaded architecture.",
      deferTitle: "DEFER",
      deferDesc: "Held back where upstream patterns break cross-platform safety.",
      keepTitle: "KEEP_DOWNSTREAM",
      keepDesc: "Preserved custom Windows supervisor and security layers.",
      statsLead: "In our latest synchronisation campaign across 1,049 upstream commits and 414 collision files, over 723 commits were harmoniously recomposed."
    },
    metrics: {
      sectionTitle: "The Mystery of 9,800+ Clones & 6 Stars",
      lead: "Prior to any formal release binary or public installer, repository telemetry revealed an extraordinary phenomenon:",
      stat1Val: "9,808",
      stat1Label: "Total Git Clones in 14 Days",
      stat2Val: "237",
      stat2Label: "Unique Developers Cloning the Code",
      stat3Val: "6",
      stat3Label: "GitHub Stars at the Time of Writing",
      story: "Developers globally were quietly downloading and running the raw code, yet we had failed to communicate our vision to the broader world. This workstation is our manifesto for the future of developer operating environments."
    },
    cta: {
      title: "Join the Experiment in Agent-Centred Computing",
      desc: "Licensed under the permissive MIT Open Source License. Explore the code, file an issue, submit a pull request, or bestow a star on GitHub.",
      starBtn: "Star on GitHub",
      readZennBtn: "Read Full Zenn Article",
      docsBtn: "Architecture Guide"
    },
    footer: {
      copyright: "© 2026 zapabob / Hermes Agent Windows Downstream. Released under the MIT Licence.",
      builtWith: "Engineered with Vanilla Web Standards for zero-dependency GitHub Pages performance.",
      top: "Back to top ↑"
    }
  },

  "ja": {
    meta: {
      title: "Hermes Agent Windows ワークステーション | AIエージェントを中心にOSを再構築した話",
      description: "「IDEにAIを足す」のをやめた。自律型AIエージェントを中心に据え、Git・ブラウザ・ローカルLLM・セキュリティセンターまで統合したWindows AIワークステーション。",
      langLabel: "日本語"
    },
    nav: {
      brand: "Hermes Workstation",
      edition: "Windows Edition",
      paradigm: "パラダイムシフト",
      features: "主要アーキテクチャ",
      security: "セキュリティセンター",
      metrics: "稼働・統計実績",
      quickstart: "クイックスタート",
      github: "GitHub リポジトリ",
      readArticle: "Zenn元記事を読む"
    },
    hero: {
      badge: "Windows向けオープンソースAIワークステーション",
      headline: "「IDEにAIを足す」のをやめた。",
      subheadline: "AIエージェントを作業の中心に据えて、Windows環境そのものを組み直した話。",
      lead: "一般的なIDEは「人間が主役のループ」で作られています。しかし、24時間自律稼働するAIエージェントに必要なのは、Git操作、Web調査、ローカル推論、複合記憶、そしてClamAV/YARAによるセキュリティまでをワンストップで統合した新しいデスクトップ環境です。",
      primaryCta: "GitHubで見る",
      secondaryCta: "Zenn記事を読む",
      copyCommand: "git clone https://github.com/zapabob/hermes-agent-windows.git",
      copied: "クローンコマンドをクリップボードにコピーしました！",
      statClones: "9,808+",
      statClonesLabel: "Gitクローン数 (直近14日)",
      statCloners: "237+",
      statClonersLabel: "ユニーククローン開発者",
      statComposed: "723+",
      statComposedLabel: "Upstream再構成コミット",
      statUptime: "24/7",
      statUptimeLabel: "Go Watchdog常駐稼働"
    },
    paradigm: {
      sectionTitle: "パラダイムシフト",
      sectionSubtitle: "「IDE＋AIチャット」から「Agent中心のWorkstation」へ",
      quote: "「なぜ人間用のエディタの片隅に、無理やりAIを同居させているのか？」「AIエージェントが仕事をするなら、エージェントを中心にOS環境を再構築すべきではないか？」",
      traditionalTitle: "従来の開発ループ（人間が主役）",
      traditionalDesc: "エディタのテキストバッファに人間が文字を打ち込むことだけに最適化されている。",
      agentTitle: "自律AIエージェントの業務ループ（Workstation中心）",
      agentDesc: "コードを書くのはほんの1ステップ。調査、推論、監査、実行、自動化、自己復旧までが1つの業務。",
      loopCompareNote: "これを別ウィンドウや別アプリでやらせるとコンテキストが分断されます。すべてを同一ワークスペースに集約しました。"
    },
    showcase: {
      sectionTitle: "実際の稼働画面",
      sectionSubtitle: "Windowsデスクトップ上で実際に動作しているスクリーンショット",
      tabHome: "エージェントホーム画面 ＆ 統合ブラウザ",
      tabSecurity: "セキュリティセンター ＆ 検疫管理",
      homeCaption: "Hermes Agent ホーム画面：中央の対話コア、右上のWebブラウザ調査ペイン、右下のGitリポジトリツリーと差分レビューを同一画面に配置。",
      securityCaption: "中央に鎮座する Security Center：リアルタイムファイル完全性検証、ClamAV/YARAスキャン、検疫ログで自律エージェントの暴走・感染を防御。",
      clickToZoom: "画像をクリックすると高解像度で拡大表示できます",
      legendTitle: "画面のペイン構成",
      legendLeft: "左ペイン: セッション階層、Telegram、Discord、CRONジョブ、Kanbanボード",
      legendCentre: "中央: 高コントラスト対話画面 ＆ ローカルLLMオーケストレーター",
      legendRightTop: "右上: 一次情報調査のための統合Chromiumブラウザペイン",
      legendRightBottom: "右下: Git CRUD操作、Diffレビュー、ブランチ操作ツリー"
    },
    pillars: {
      sectionTitle: "既存環境と決定的に違う5つの特徴",
      sectionSubtitle: "なぜHermes Agent Windows Workstationは唯一無二なのか",
      p1Title: "1. 「IDE並みのGit操作」を人間とエージェントが共有",
      p1Desc: "デスクトップ右側にGitツリーが常駐。差分レビュー、コミット、ブランチ・ワークツリー操作をエージェントと人間が同一画面でリアルタイムに実行できます。",
      p2Title: "2. ブラウザも「別アプリ」ではなくワークスペースの1ペイン",
      p2Desc: "Web調査→リポジトリ確認→実装→テストのループが1秒も途切れません。エージェントのブラウザ自動操作と人間の視線が完全に同期します。",
      p3Title: "3. なぜ「Security Center」が同居しているのか？",
      p3Desc: "強い権限（ローカルファイル書き換え、Shell実行、MCP接続）を渡すからこそ、ClamAV/YARA/検疫によるリアルタイム監視と防御が不可欠です。",
      p4Title: "4. 外部Go Watchdogによる「24時間死なない」常駐機構",
      p4Desc: "プロセスの死やメモリリークを自律検知。「再起動の権限（Restart Authority）を唯一化」するシングルオーソリティ設計でカスケード障害を防ぎます。",
      p5Title: "5. 「チャット履歴」を捨て、「忘却と意味グラフ」を持つ記憶モデル",
      p5Desc: "会話履歴をプロンプトに垂れ流すのは記憶ではありません。ベクトル検索＋知識グラフ＋エビングハウスの忘却曲線モデルによる生きた長期記憶を搭載。",
      p6Title: "6. コーディングだけじゃない：Voice・Unity・VRChatへの受肉",
      p6Desc: "黒い画面にとどまらず、VOICEVOX音声対話やOSC経由でのVRChat/Unity受肉アバター連携まで直結。Windowsネイティブだからこその自由度です。"
    },
    security: {
      sectionTitle: "エージェントの権限と防御",
      sectionSubtitle: "なぜAIワークステーションにアンチウイルスが必要なのか？",
      intro: "オモチャのデモならセキュリティは無視できます。しかし、本気で24時間自律作業を任せるなら、「防御と観測」はワークステーションの第一級機能でなければなりません。",
      layerHeader: "監視・防御レイヤー",
      engineHeader: "使用エンジン・技術",
      row1Layer: "ウイルス・マルウェア検知",
      row1Engine: "ClamAV 1.5.4 / YARA ルール / Windows Defender",
      row2Layer: "ファイル完全性検証",
      row2Engine: "Hash Reputation ＆ 静的ヒューリスティクス",
      row3Layer: "隔離・遮断",
      row3Engine: "Quarantine（検疫）自動管理 ＆ 権限バウンダリ",
      row4Layer: "実行ログ・履歴",
      row4Engine: "Scan & Execution Audit History（完全監査ログ）"
    },
    sync: {
      sectionTitle: "泥臭い裏側：Upstreamへのセマンティック追従",
      sectionSubtitle: "Nous Research本体の猛スピード開発にどう追いつくか？",
      lead: "単純にgit mergeを繰り返すだけでは、Windows独自拡張は一瞬で壊れます。upstreamのコミットを1つずつ精査する「セマンティック統合」パイプラインを運用しています：",
      adoptTitle: "ADOPT（そのまま採用）",
      adoptDesc: "upstreamの最新機能をそのままクリーンに取り込み。",
      composeTitle: "COMPOSE（再合成：70%以上）",
      composeDesc: "Windowsの権限モデル、ConPTYブリッジ、マルチスレッド環境に合わせて再構築。",
      deferTitle: "DEFER（保留）",
      deferDesc: "プラットフォーム互換性や安定性の観点から慎重に保留。",
      keepTitle: "KEEP_DOWNSTREAM（独自維持）",
      keepDesc: "Go Watchdogやセキュリティセンターなど独自の堅牢性を堅持。",
      statsLead: "直近のキャンペーンでは、1,049件のupstreamコミット・414の衝突ファイル中、723件を単なるコピペではなく再合成して統合しました。"
    },
    metrics: {
      sectionTitle: "クローン9,800回でStarが6個だった話",
      lead: "インストーラーや正式Releaseバイナリすらまだ出していない段階で、GitHub Trafficに異様な数字が現れました：",
      stat1Val: "9,808",
      stat1Label: "直近14日間のGitクローン数",
      stat2Val: "237",
      stat2Label: "クローンしたユニーク開発者数",
      stat3Val: "6",
      stat3Label: "記事執筆時のGitHub Star数（笑）",
      story: "「何を作っているのか外に全然伝わっていない」と痛感しました。コードだけ書いて満足せず、目指している未来を言語化して届けるためにこの記事を書きました。"
    },
    cta: {
      title: "「AIがOSを作業場にする」未来を一緒に作りませんか？",
      desc: "すべてオープンソース（MIT License）で開発中。Star、Issue、PR、大歓迎です！",
      starBtn: "GitHubでStarをつける",
      readZennBtn: "Zennの元記事を読む",
      docsBtn: "開発ガイド（AGENTS.md）"
    },
    footer: {
      copyright: "© 2026 zapabob / Hermes Agent Windows Downstream. MIT License.",
      builtWith: "Vanilla Web Standardsで構築された高速・高信頼なGitHub Pagesショーケース。",
      top: "ページトップへ ↑"
    }
  },

  "zh-CN": {
    meta: {
      title: "Hermes Agent Windows 工作站 | 告别在IDE旁硬塞AI，以自主智能体为中枢重构操作系统",
      description: "不再把AI当成IDE边栏的聊天插件。以24小时自主运行的AI Agent为核心，深度集成Git、浏览器、本地大模型与ClamAV/YARA安全中心的新一代Windows AI工作站。",
      langLabel: "简体中文"
    },
    nav: {
      brand: "Hermes Workstation",
      edition: "Windows Edition",
      paradigm: "范式跃迁",
      features: "核心架构",
      security: "安全中心",
      metrics: "运行数据",
      quickstart: "快速上手",
      github: "GitHub 仓库",
      readArticle: "阅读Zenn原文"
    },
    hero: {
      badge: "面向 Windows 的开源自主 AI Agent 专属工作站",
      headline: "彻底告别“在IDE边栏加个AI对话框”。",
      subheadline: "以自主智能体（AI Agent）为核心，彻底重构整个 Windows 操作系统环境。",
      lead: "传统IDE围绕人类手工敲代码设计。而面对24小时常驻的自主Agent，代码编辑仅仅是其中一环——Git操作、网页调研、本地LLM推理、Ebbinghaus认知记忆，乃至ClamAV/YARA反病毒安全监控，全部必须高度整合在同一工作站画布中。",
      primaryCta: "前往 GitHub 仓库",
      secondaryCta: "阅读 Zenn 原文",
      copyCommand: "git clone https://github.com/zapabob/hermes-agent-windows.git",
      copied: "克隆命令已复制到剪贴板！",
      statClones: "9,808+",
      statClonesLabel: "Git克隆次数 (近14天)",
      statCloners: "237+",
      statClonersLabel: "独立克隆开发者",
      statComposed: "723+",
      statComposedLabel: "Upstream重组重构提交",
      statUptime: "24/7",
      statUptimeLabel: "Go Watchdog永不宕机"
    },
    paradigm: {
      sectionTitle: "范式跃迁 (Paradigm Shift)",
      sectionSubtitle: "从“IDE挂载AI插件”转变为“以Agent为中枢的独立工作站”",
      quote: "“为什么要把自主AI委屈地塞在人类编辑器的角落抽屉里？”“如果真正由AI Agent主导繁重工作，难道不应该以Agent为中心重塑整个OS环境吗？”",
      traditionalTitle: "传统人类开发循环 (Human-Centric)",
      traditionalDesc: "仅仅针对人类手指在文本框中键入字符这一狭窄场景进行了优化。",
      agentTitle: "自主Agent全业务生命周期 (Workstation-Centric)",
      agentDesc: "编写代码只是其中一步。Agent必须能够自主感知、调研、推理、审查、执行运维、自动化与自愈。",
      loopCompareNote: "把这些环节割裂在不同的窗口和软件中，会导致上下文严重断裂。Hermes Workstation 将全套能力无缝汇聚在单一屏幕。"
    },
    showcase: {
      sectionTitle: "真实桌面运行截图",
      sectionSubtitle: "在实际 Windows 环境中高负荷运转的工作站界面",
      tabHome: "Agent主屏与内置浏览器",
      tabSecurity: "安全中心与隔离区管理",
      homeCaption: "Hermes Agent 主工作界面：中央为主交互与推理核，右上角为实时网页调研窗格，右下角为全功能Git仓库树与Diff审查。",
      securityCaption: "中央专属 Security Center：实时文件完整性校验、ClamAV/YARA扫描引擎与自动隔离区，确保高权限Agent免受攻击与投毒。",
      clickToZoom: "点击图片可全屏高分辨率查看",
      legendTitle: "窗格布局与架构",
      legendLeft: "左侧: 会话列表、Telegram、Discord、CRON定时调度与Kanban多Agent协作板",
      legendCentre: "中央: 高对比度思考推理画布与本地LLM编排器",
      legendRightTop: "右上: 专供深度研究与自动化的内置Chromium浏览器窗格",
      legendRightBottom: "右下: 与IDE同级的Git CRUD、分支管理与差异审查树"
    },
    pillars: {
      sectionTitle: "区别于传统工具的5大核心突破",
      sectionSubtitle: "为什么说 Hermes Agent Windows 是独一无二的硬核之作",
      p1Title: "1. 人机对等的“专业级Git操作”同屏共治",
      p1Desc: "桌面右侧常驻Git仓库树。并非单纯查看文件，而是人类与Agent实时同屏执行CRUD、Diff审核、分支与Worktree操作，彻底告别频繁切屏。",
      p2Title: "2. 浏览器不再是外置软件，而是工作区原生窗格",
      p2Desc: "网页调研→查看源码→编码实现→测试报错→再搜索的闭环秒级完成。Agent的浏览器自动化操作与人类视野完全同频共振。",
      p3Title: "3. 为什么画面正中央会有一个“安全中心”？",
      p3Desc: "授予Agent修改磁盘、运行PowerShell与调用外部MCP的高权限时，若无实时防御与审计，没人敢让它24小时常驻。ClamAV与YARA构筑了坚固防线。",
      p4Title: "4. 外部 Go Watchdog 守护“24小时永不宕机”",
      p4Desc: "彻底终结内存泄露和默默闪退。坚持“重启权限归一化（Single Restart Authority）”原则，由外部Go守护进程统一管理，杜绝级联故障。",
      p5Title: "5. 抛弃无脑聊天记录堆砌，引入“遗忘与语义图谱”记忆模型",
      p5Desc: "把所有历史记录塞进Prompt不是记忆，只是简单粗暴的日志倾倒。基于艾宾浩斯遗忘曲线＋知识图谱＋混合向量检索，赋予Agent持久演进的长期记忆。",
      p6Title: "6. 不仅限于代码：Voice语音、Unity与VRChat实体具身",
      p6Desc: "告别单调黑底白字：无缝直连VOICEVOX本地TTS语音合成、OSC协议，以及Unity/VRChat虚拟化身，打造真正具备“具身智能”的超级助手。"
    },
    security: {
      sectionTitle: "为高权限Agent构筑企业级防线",
      sectionSubtitle: "为什么AI工作站必须标配反病毒与隔离安全中心？",
      intro: "几分钟的玩具Demo可以无视安全；但如果你打算让Agent整天整夜在生产机器上自主工作，实时观测与威胁隔离就是第一优先级的硬性指标。",
      layerHeader: "防御与监控层级",
      engineHeader: "所用技术与防护引擎",
      row1Layer: "恶意代码与漏洞防御",
      row1Engine: "ClamAV 1.5.4 / YARA 规则库 / Windows Defender",
      row2Layer: "文件完整性校验",
      row2Engine: "哈希信誉库 (Hash Reputation) 与静态启发式分析",
      row3Layer: "恶意样本自动隔离",
      row3Engine: "Quarantine 隔离区管理与动态权限沙箱",
      row4Layer: "全生命周期审计日志",
      row4Engine: "完整终端指令与扫描审计追踪历史记录"
    },
    sync: {
      sectionTitle: "硬核工程底色：对Upstream主线的语义重构",
      sectionSubtitle: "面对Nous Research主线日新月异的高频更新，如何做到绝不掉队？",
      lead: "简单粗暴地执行 `git merge upstream/main` 只会让Windows专属增强瞬间遭遇冲突崩溃。我们采用严谨的“语义合并流水线”逐条分类处理：",
      adoptTitle: "ADOPT (直接采纳)",
      adoptDesc: "与平台无关的新特性直接干净合入。",
      composeTitle: "COMPOSE (深度重组：占70%以上)",
      composeDesc: "结合Windows权限模型、ConPTY虚拟终端与多线程架构进行全新重塑。",
      deferTitle: "DEFER (审慎推迟)",
      deferDesc: "对破坏跨平台稳定性的变动保持克制与观望。",
      keepTitle: "KEEP_DOWNSTREAM (坚守原生特性)",
      keepDesc: "坚定维持Windows Go守护进程、安全中心等独家壁垒。",
      statsLead: "在最近一次涵盖1,049个upstream提交和414个冲突文件的更新战役中，我们成功重组了多达723个关键提交。"
    },
    metrics: {
      sectionTitle: "近万次克隆与仅有6颗Star背后的故事",
      lead: "在甚至还没正式打包安装包和Release的极早期源码阶段，GitHub统计数据展现出令人惊讶的反差：",
      stat1Val: "9,808",
      stat1Label: "14天内Git代码克隆总次数",
      stat2Val: "237",
      stat2Label: "下载代码的独立开发者人数",
      stat3Val: "6",
      stat3Label: "文章撰写时的GitHub Star数量",
      story: "我们深切意识到：光埋头写好代码还不够，如果不把“我们在为什么而战”清晰表达出来，就无法触达更多同路人。这也是写下这篇深度长文的原动力。"
    },
    cta: {
      title: "携手探索“让AI将操作系统作为作业场”的崭新时代",
      desc: "全部代码基于宽松的 MIT 许可证完全开源。诚挚欢迎 Star、提交 Issue 或发起 PR！",
      starBtn: "在 GitHub 上点亮 Star",
      readZennBtn: "阅读 Zenn 日文长文",
      docsBtn: "查看开发手册 (AGENTS.md)"
    },
    footer: {
      copyright: "© 2026 zapabob / Hermes Agent Windows Downstream. 采用 MIT 开源协议。",
      builtWith: "基于原生Web标准构建，零外部依赖，极速轻量适配 GitHub Pages。",
      top: "返回顶部 ↑"
    }
  }
};

// Expose globally
if (typeof window !== "undefined") {
  window.HermesTranslations = translations;
}
