<#
.SYNOPSIS
    把当前工程打成可分发给客户的源码压缩包。

.DESCRIPTION
    产出的压缩包只包含“能编译 + 能运行 + 能看文档”的内容，并且**剥离一切 git 痕迹**，
    客户既拿不到仓库地址/历史，也无法用脚本拉取你的代码：

      * 不包含 .git / .gitmodules / .gitignore / .github —— 没有仓库地址、历史与远端配置；
      * 不包含 git 操作脚本（[Windows]git_pull_latest.cmd / [Linux]git_pull_latest.sh）；
      * 不包含内部资料（openspec、.workbuddy、AGENTS.md、docs/superpowers、tests/）；
      * 不包含依赖缓存与构建产物（libs、build、out、dist、csvfile、docs/html、__pycache__）；
      * 不包含开发工具（pytest.ini、pyrightconfig.json、Doxyfile、gen_docs.bat）。

    构建入口 [Windows]build.cmd 及其依赖的 MotionGlove3DViewer.spec 会**随包发出**，
    客户拿到源码后可直接构建 dist\MotionGlove3DViewer\MotionGlove3DViewer.exe；
    scripts\[Linux]build_dist.sh 仍属内部物料，不打包。

    third_party/MotionGloveSDK_cpp 的 **C++ 源码会完整保留**（客户可自行编译），
    只剔除其中的 .git 与内部资料。README 中“git submodule / 拉取脚本 / 内部发布流程”
    等说明会在暂存目录里自动删除或改写，避免误导客户。

    压缩包内有一层顶层目录 MotionGloveSDK_python_v<版本号>，解压后不会散落在当前目录。

.PARAMETER OutputDir
    压缩包输出目录，默认仓库根目录。

.PARAMETER Version
    覆盖版本号，默认取 third_party/MotionGloveSDK_cpp 的版本头（失败时取 CHANGELOG）。

.PARAMETER KeepStaging
    保留暂存目录（build/package/<包名>），便于检查打包内容。

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts\package_for_customer.ps1

.EXAMPLE
    scripts\[Windows]package_for_customer.cmd -Version 0.2.2 -KeepStaging
#>
[CmdletBinding()]
param(
    [string]$OutputDir = '',
    [string]$Version = '',
    [switch]$KeepStaging
)

$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$packageBaseName = 'MotionGloveSDK_python'

# ---------------------------------------------------------------------------
# 版本号
# ---------------------------------------------------------------------------
function Get-ProjectVersion {
    param([string]$Root)

    $versionHeader = Join-Path $Root 'third_party/MotionGloveSDK_cpp/MotionGloveSDK_examples/inc/motionGloveSDK_version.h'
    if (Test-Path -LiteralPath $versionHeader) {
        $text = Get-Content -LiteralPath $versionHeader -Raw
        $parts = @()
        foreach ($part in @('MAJOR', 'MINOR', 'PATCH')) {
            $pattern = '#define\s+MOTIONGLOVE_EXAMPLE_VERSION_' + $part + '\s+(\d+)'
            if ($text -match $pattern) { $parts += $Matches[1] }
        }
        if ($parts.Count -eq 3) { return ($parts -join '.') }
    }

    $changelog = Join-Path $Root 'CHANGELOG.md'
    if (Test-Path -LiteralPath $changelog) {
        $text = Get-Content -LiteralPath $changelog -Raw
        if ($text -match '(?m)^##\s*\[(\d+\.\d+\.\d+)\]') { return $Matches[1] }
    }

    return '0.0.0'
}

if (-not $Version) { $Version = Get-ProjectVersion -Root $repoRoot }

if (-not $OutputDir) {
    $OutputDir = $repoRoot
}
elseif (-not (Test-Path -LiteralPath $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}
$OutputDir = (Resolve-Path -LiteralPath $OutputDir).Path

$packageName = "${packageBaseName}_v$Version"
$stageRoot = Join-Path $repoRoot 'build\package'
$stageDir = Join-Path $stageRoot $packageName
$zipPath = Join-Path $OutputDir "$packageName.zip"

# ---------------------------------------------------------------------------
# 排除规则（robocopy 的 /XD、/XF 对任意层级生效）
# ---------------------------------------------------------------------------
$excludeDirs = @(
    '.git', '.github', '.vs', '.vscode', '.idea',
    '.venv', 'venv', 'node_modules',
    '.pytest_cache', '__pycache__', '.workbuddy',
    'openspec', 'superpowers',
    'libs', 'build', 'out', 'dist',
    'csvfile', 'tests',
    (Join-Path $repoRoot 'docs')
)
$excludeFiles = @(
    # 子模块工作区里的 .git 是文件（gitlink），/XD 只排除目录，必须同时按文件排除
    '.git', '.gitignore', '.gitattributes', '.gitmodules',
    '*git_pull_latest*',
    '*package_for_customer*', '*package_source*',
    # Windows 构建入口 [Windows]build.cmd 要随包发出，这里只排除 Linux 打包脚本
    '[Linux]build_dist.sh',
    'AGENTS.md',
    'pytest.ini', 'pyrightconfig.json',
    'Doxyfile', 'gen_docs.bat', 'doxygen_warnings.log', '*.log',
    '*.zip', '*.7z', '*.user', '*.bak', '*.tmp',
    '*.pyc', '*.pyo', 'Thumbs.db', '.DS_Store',
    # 仓库根目录遗留的独立 .qm 文件（真正的翻译在 translations/ 下，文件名不同，不受影响）
    '.qm'
)

Write-Host "[1/5] 复制工程文件到暂存目录：$stageDir"
if (Test-Path -LiteralPath $stageDir) { Remove-Item -LiteralPath $stageDir -Recurse -Force }
New-Item -ItemType Directory -Path $stageDir -Force | Out-Null

$robocopyArgs = @(
    $repoRoot, $stageDir, '/E', '/NFL', '/NDL', '/NJH', '/NJS', '/NP',
    '/XD'
) + $excludeDirs + @('/XF') + $excludeFiles
& robocopy @robocopyArgs | Out-Null
# robocopy 用 0~7 表示成功（有差异/已复制），>= 8 才是失败
if ($LASTEXITCODE -ge 8) { throw "复制工程文件失败（robocopy 退出码 $LASTEXITCODE）" }

# ---------------------------------------------------------------------------
# 改写分发包内的说明文字（只改暂存副本，仓库里的文件保持原样）
# ---------------------------------------------------------------------------
function Update-StagedText {
    param(
        [string]$Path,
        [object[]]$Ops = @(),
        [string[]]$DropLinePatterns = @(),
        [string[]]$DropSections = @()
    )

    if (-not (Test-Path -LiteralPath $Path)) { return $false }

    $bytes = [System.IO.File]::ReadAllBytes($Path)
    $hasBom = ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF)
    $text = [System.Text.Encoding]::UTF8.GetString($bytes)
    if ($hasBom) { $text = $text.Substring(1) }
    $original = $text

    if ($DropLinePatterns.Count -gt 0) {
        $kept = @()
        foreach ($line in ($text -split "\r?\n")) {
            $drop = $false
            foreach ($pattern in $DropLinePatterns) {
                if ($line -match $pattern) { $drop = $true; break }
            }
            if (-not $drop) { $kept += $line }
        }
        $text = $kept -join "`r`n"
    }

    foreach ($sectionPattern in $DropSections) {
        $regex = [regex]::new('(?ms)^' + $sectionPattern + '.*?(?=^##\s|\z)')
        $text = $regex.Replace($text, '')
    }

    foreach ($op in $Ops) {
        $text = [regex]::Replace($text, $op.Pattern, $op.Replacement)
    }

    if ($text -eq $original -and -not $DropSections) { return $false }
    if ($text -eq $original) { return $false }

    $encoding = New-Object System.Text.UTF8Encoding($hasBom)
    [System.IO.File]::WriteAllText($Path, $text, $encoding)
    return $true
}

Write-Host '[2/5] 删除/改写分发包内的 git 相关说明'

# 目录树里只给开发者看的脚本条目
$dropLinePatterns = @('git_pull_latest', 'package_for_customer', 'package_source', 'build_dist')

$commonOps = @(
    @{ Pattern = '请先初始化子模块[：:]\s*git submodule update --init --recursive';
       Replacement = '请确认 third_party/MotionGloveSDK_cpp 目录完整（第三方 C++ 源码随分发包提供）' },
    @{ Pattern = 'git submodule update --init --recursive';
       Replacement = '（第三方 C++ 源码随分发包提供，无需初始化子模块）' },
    @{ Pattern = '，以 git submodule 引入'; Replacement = '，源码随分发包提供' },
    @{ Pattern = '（git submodule，编译出'; Replacement = '（源码随分发包提供，编译出' },
    @{ Pattern = '，git submodule）'; Replacement = '，源码随分发包提供）' },
    @{ Pattern = '（git 忽略）'; Replacement = '（编译生成）' }
)

$readmeOps = $commonOps + @(
    # 分发包已带 C++ 源码，没有“初始化 submodule”这一步，顺带把编号收敛掉
    @{ Pattern = '(?s)###\s*1\.\s*初始化 submodule.*?###\s*2\.\s*编译'; Replacement = '### 编译' },
    @{ Pattern = '###\s*3\.\s*验证（可选）'; Replacement = '### 验证（可选）' },
    @{ Pattern = '重新执行第 2 步'; Replacement = '重新执行编译步骤' }
)

# 分发包里没有 tests/、Doxyfile、打包脚本，对应章节一并去掉
$readmeDropSections = @('##\s*测试（pytest）', '##\s*文档（Doxygen）', '##\s*打包客户分发包')
# C++ README 里的内部发布流程
$cppReadmeDropSections = @('##\s*发布', '##\s*源码分发包')

Update-StagedText -Path (Join-Path $stageDir 'README.md') -Ops $readmeOps `
    -DropLinePatterns $dropLinePatterns -DropSections $readmeDropSections | Out-Null
Update-StagedText -Path (Join-Path $stageDir 'CHANGELOG.md') -Ops $commonOps `
    -DropLinePatterns $dropLinePatterns | Out-Null
Update-StagedText -Path (Join-Path $stageDir 'third_party/MotionGloveSDK_cpp/README.md') -Ops $commonOps `
    -DropLinePatterns $dropLinePatterns -DropSections $cppReadmeDropSections | Out-Null
Update-StagedText -Path (Join-Path $stageDir 'scripts/[Windows]build_mgsdk_cpp.cmd') -Ops $commonOps | Out-Null
Update-StagedText -Path (Join-Path $stageDir 'scripts/[Linux]build_mgsdk_cpp.sh') -Ops $commonOps | Out-Null
Update-StagedText -Path (Join-Path $stageDir 'scripts/verify_native_abi.py') -Ops $commonOps | Out-Null

# config.json 里可能有开发者本机的绝对路径（如 blender.exe），清空让客户自行配置
$configPath = Join-Path $stageDir 'config.json'
if (Test-Path -LiteralPath $configPath) {
    $config = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
    if ($config.PSObject.Properties.Name -contains 'blender_exe') {
        $config.blender_exe = ''
        $configText = $config | ConvertTo-Json -Depth 6
        [System.IO.File]::WriteAllText($configPath, $configText, (New-Object System.Text.UTF8Encoding($false)))
    }
}

# ---------------------------------------------------------------------------
# 校验：确保分发包里没有任何 git 痕迹
# ---------------------------------------------------------------------------
Write-Host '[3/5] 校验分发包里没有残留 git 内容'
$problems = @()

# 构建入口必须随包发出，客户要靠它生成可执行文件
$requiredBuildFiles = @('[Windows]build.cmd', 'MotionGlove3DViewer.spec')
foreach ($required in $requiredBuildFiles) {
    if (-not (Test-Path -LiteralPath (Join-Path $stageDir $required))) {
        throw "分发包缺少构建所需文件：$required"
    }
}

$gitMetadataNames = @('.git', '.gitmodules', '.gitignore', '.gitattributes', '.gitconfig')
$problems += Get-ChildItem -LiteralPath $stageDir -Recurse -Force -ErrorAction SilentlyContinue |
    Where-Object { $gitMetadataNames -contains $_.Name -or $_.Name -like '.git.*' }
$problems += Get-ChildItem -LiteralPath $stageDir -Recurse -Force -Directory -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -eq '.git' }

$gitScriptNames = Get-ChildItem -LiteralPath $stageDir -Recurse -Force -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -like '*git*' }
$problems += $gitScriptNames

$textExtensions = @('.md', '.py', '.cmd', '.bat', '.sh', '.ps1', '.json', '.txt', '.yml', '.yaml')
$textFiles = Get-ChildItem -LiteralPath $stageDir -Recurse -Force -File -ErrorAction SilentlyContinue |
    Where-Object { $textExtensions -contains $_.Extension }

$problems += $textFiles | Select-String -Pattern '\bgit(\.exe)?\s+(fetch|pull|clone|push|remote|checkout|submodule|tag)\b' -ErrorAction SilentlyContinue
$problems += $textFiles | Select-String -Pattern 'github\.com/FOHEART|git@github\.com|\.gitmodules' -ErrorAction SilentlyContinue

if ($problems.Count -gt 0) {
    foreach ($item in $problems) {
        if ($item -is [System.IO.FileSystemInfo]) {
            Write-Host "  残留：$($item.FullName)"
        }
        else {
            Write-Host "  残留：$($item.Filename):$($item.LineNumber)  $($item.Line.Trim())"
        }
    }
    throw '分发包里仍有 git 相关内容，请补充排除规则'
}
Write-Host '  未发现 .git 目录/文件、git 操作脚本、脚本内的 git 命令或仓库地址'

# ---------------------------------------------------------------------------
# 压缩
# ---------------------------------------------------------------------------
Write-Host "[4/5] 压缩为 $zipPath"
if (Test-Path -LiteralPath $zipPath) { Remove-Item -LiteralPath $zipPath -Force }

$sevenZip = (Get-Command 7z -ErrorAction SilentlyContinue).Source
if (-not $sevenZip) {
    $candidate = Join-Path $env:ProgramFiles '7-Zip\7z.exe'
    if (Test-Path -LiteralPath $candidate) { $sevenZip = $candidate }
}

if ($sevenZip) {
    Push-Location $stageRoot
    try { & $sevenZip a -tzip -mx=5 $zipPath $packageName | Out-Null }
    finally { Pop-Location }
}
else {
    Compress-Archive -Path $stageDir -DestinationPath $zipPath -Force
}
if (-not (Test-Path -LiteralPath $zipPath)) { throw "压缩失败：未生成 $zipPath" }

$fileCount = (Get-ChildItem -LiteralPath $stageDir -Recurse -File | Measure-Object).Count
$sizeMb = [math]::Round((Get-Item -LiteralPath $zipPath).Length / 1MB, 1)

Write-Host '[5/5] 完成'
if ($KeepStaging) {
    Write-Host "  暂存目录：$stageDir（已按要求保留）"
}
else {
    Remove-Item -LiteralPath $stageDir -Recurse -Force
    if ((Test-Path -LiteralPath $stageRoot) -and -not (Get-ChildItem -LiteralPath $stageRoot -Force)) {
        Remove-Item -LiteralPath $stageRoot -Recurse -Force
    }
}

Write-Host "  压缩包：$zipPath"
Write-Host "  版本：v$Version　顶层目录：$packageName　文件数：$fileCount　大小：$sizeMb MB"
Write-Host "  已排除目录：$($excludeDirs -join '、')"
Write-Host '  提示：分发包不含 libs/ 与预编译动态库，客户可运行根目录 [Windows]build.cmd 一键装依赖 + 编译原生库 + 打包。'
