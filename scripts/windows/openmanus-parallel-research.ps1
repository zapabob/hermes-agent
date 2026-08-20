# Fan out N OpenManus literature-search tasks in parallel using openmanus-venv.
# Bypasses `uv run` which is blocked by .venv lock from the running Hermes.
param(
    [int]$MaxSteps = 15
)

$ErrorActionPreference = "Continue"

$repoRoot = "C:\Users\downl\Documents\New project\hermes-agent"
$venvPy = "$repoRoot\_runtime\openmanus-venv\Scripts\python.exe"
$runnerPy = "$repoRoot\plugins\openmanus\runner.py"
$sourceRoot = "$repoRoot\vendor\openmanus"
$workspaceRoot = "$repoRoot\_runtime\research-workspace\meth-sar-synthesis"

$tasks = @(
    "学術文献調査：メタンフェタミン（1-フェニル-2-メチルアミノプロパン）の合成経路を収率・反応条件・副生成物の観点から整理せよ。P2P経路（Leuckart反応、還元アミノ化）とエフェドリン/プソイドエフェドリン経路（ヨウ素/赤リン還元、HI還元）を比較し、各経路の収率範囲、反応条件（温度、溶媒、触媒）、主要副生成物、d-体/l-体選択性を文献値で示せ。PubMed、学術論文、法科学文献を優先すること。",
    "学術文献調査：メタンフェタミンの構造活性相関（SAR）と薬理作用を整理せよ。フェネチラミン骨格における置換基の違いがトランスポーター親和性に与える影響、d-体とl-体の薬理活性差、代謝経路を文献値で示せ。",
    "学術文献調査：メタンフェタミンのアナログ（誘導体・類似物）を構造と活性の観点から整理せよ。MDMA以外のアナログも含め、構造変化が薬理活性・毒性・検出法に与える影響を文献値で示せ。",
    "学術文献調査：メタンフェタミンの法科学・分析化学データを整理せよ。GC-MS、LC-MS、NMR、IR、質量分析における特徴的なピーク・保持時間・フラグメントパターン、不純物プロファイルから合成経路を推定する手法を文献値で示せ。"
)

# Load secret
$envFile = "$env:USERPROFILE\.hermes\.env"
$secret = ""
Get-Content $envFile | Where-Object { $_ -match '^OPENMANUS_API_KEY=(.+)' } | ForEach-Object { $secret = $matches[1] }
if (-not $secret) { Write-Error "OPENMANUS_API_KEY not found"; exit 2 }

$procs = @()
for ($i = 0; $i -lt $tasks.Count; $i++) {
    $itemNum = ($i + 1).ToString("00")
    $wsDir = "$workspaceRoot\item-$itemNum"
    New-Item -ItemType Directory -Force -Path $wsDir | Out-Null
    $runId = "manual-$itemNum"
    $runRoot = "$env:USERPROFILE\.hermes\openmanus\runs\$runId"
    New-Item -ItemType Directory -Force -Path $runRoot | Out-Null

    Write-Host "Starting item-$itemNum ..."
    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = $venvPy
    $startInfo.Arguments = "$runnerPy --source-root `"$sourceRoot`" --workspace-root `"$wsDir`" --run-root `"$runRoot`" --model qwen3.8-27b-abliterated-mtp --base-url http://127.0.0.1:8080/v1 --api-type openai --api-key-env OPENMANUS_API_KEY --agent-mode manus --max-steps $MaxSteps --allow-network --network-scope llm_only"
    $startInfo.EnvironmentVariables["OPENMANUS_API_KEY"] = $secret
    $startInfo.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8"
    $startInfo.EnvironmentVariables["PYTHONUTF8"] = "1"
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $proc = [System.Diagnostics.Process]::Start($startInfo)
    $procs += @{ Id = $proc.Id; Item = $itemNum; Proc = $proc; RunRoot = $runRoot }
    Write-Host "  PID $($proc.Id)"
}

Write-Host "`nWaiting for all tasks to complete..."
foreach ($p in $procs) {
    $p.Proc.WaitForExit()
    Write-Host "Item-$($p.Item) (PID $($p.Id)) exit code: $($p.Proc.ExitCode)"
    $receiptPath = "$($p.RunRoot)\receipt.json"
    if (Test-Path $receiptPath) {
        $r = Get-Content $receiptPath -Raw | ConvertFrom-Json
        Write-Host "  receipt: status=$($r.status) steps=$($r.steps_taken)"
    } else {
        Write-Host "  NO RECEIPT at $receiptPath"
    }
}
Write-Host "`nALL_DONE"
