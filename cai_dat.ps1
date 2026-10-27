# Cai dat he thong Giam sat chat luong khong khi TP.HCM tren Windows 10/11.
# Goi qua cai_dat.bat. Moi thu duoc cai vao thu muc runtime\ ben canh,
# khong can quyen quan tri, khong dong cham toi PostgreSQL co san tren may.
# Chay lai nhieu lan duoc: buoc nao da xong se bo qua.

# Loi cua cmdlet -> dung lai; chuong trinh ngoai (pip, pg_restore...) ghi stderr
# khong tinh la loi, chi xet ma thoat $LASTEXITCODE.
$ErrorActionPreference = 'Continue'
$PSDefaultParameterValues['*:ErrorAction'] = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$Goc  = Split-Path -Parent $MyInvocation.MyCommand.Path
$RT   = Join-Path $Goc 'runtime'
$Tai  = Join-Path $RT 'tai_ve'
$PG   = Join-Path $RT 'pgsql'
$Data = Join-Path $RT 'data'
$Venv = Join-Path $RT 'venv'
$Rel  = 'https://github.com/koisd/air_quality_hcm/releases/download/du-lieu'
$PyUrl = 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe'

function Buoc($so, $ten) { Write-Host ''; Write-Host "[$so/5] $ten" -ForegroundColor Cyan }
function Loi($tb) { throw $tb }

function Tai-Ve($url, $dich) {
    if (Test-Path $dich) { return }
    Write-Host "      Đang tải $(Split-Path -Leaf $dich) ..."
    $tam = "$dich.part"
    $curl = Join-Path $env:SystemRoot 'System32\curl.exe'
    if (Test-Path $curl) {
        & $curl -L --fail --retry 3 --progress-bar -o $tam $url
        if ($LASTEXITCODE -ne 0) { Loi "Không tải được $url (kiểm tra kết nối mạng)." }
    } else {
        Invoke-WebRequest $url -OutFile $tam -UseBasicParsing
    }
    Move-Item $tam $dich -Force
}

function Python-Hop-Le($exe, $them) {
    try {
        $kq = & $exe @them -c "import sys,struct;print(int((3,10)<=sys.version_info[:2]<=(3,13) and struct.calcsize('P')==8))" 2>$null
        return ($LASTEXITCODE -eq 0 -and "$kq".Trim() -eq '1')
    } catch { return $false }
}

function Tim-Python {
    foreach ($v in '3.12', '3.13', '3.11', '3.10') {
        if ((Get-Command py -ErrorAction SilentlyContinue) -and (Python-Hop-Le 'py' @("-$v"))) {
            return ,@('py', "-$v")
        }
    }
    $p = Get-Command python -ErrorAction SilentlyContinue
    if ($p -and $p.Source -notlike '*WindowsApps*' -and (Python-Hop-Le $p.Source @())) {
        return ,@($p.Source)
    }
    $rieng = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'
    if ((Test-Path $rieng) -and (Python-Hop-Le $rieng @())) { return ,@($rieng) }
    return $null
}

function Cong-Trong {
    foreach ($c in 5433..5460) {
        $l = $null
        try {
            $l = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, $c)
            $l.Start(); $l.Stop(); return $c
        } catch { } finally { if ($l) { $l.Stop() } }
    }
    Loi 'Không tìm được cổng trống cho PostgreSQL (5433–5460).'
}

try {
    Write-Host '=============================================================='
    Write-Host '  Cài đặt: Giám sát chất lượng không khí TP.HCM'
    Write-Host "  Thư mục: $Goc"
    Write-Host '=============================================================='
    New-Item -ItemType Directory -Force $Tai | Out-Null

    # ------------------------------------------------------------------ Python
    Buoc 1 'Kiểm tra Python'
    $py = Tim-Python
    if (-not $py) {
        Write-Host '      Chưa có Python 3.10–3.13 (64-bit), cài Python 3.12 cho người dùng hiện tại.'
        $bo = Join-Path $Tai 'python-3.12.10-amd64.exe'
        Tai-Ve $PyUrl $bo
        $p = Start-Process $bo -Wait -PassThru -ArgumentList `
            '/quiet', 'InstallAllUsers=0', 'PrependPath=0', 'Include_test=0', 'Include_launcher=0', 'Shortcuts=0'
        if ($p.ExitCode -ne 0) { Loi "Cài Python thất bại (mã $($p.ExitCode))." }
        $py = Tim-Python
        if (-not $py) { Loi 'Đã cài Python nhưng không chạy được.' }
    }
    $pyExe = $py[0]; $pyThem = @($py | Select-Object -Skip 1)
    Write-Host "      Dùng: $(& $pyExe @pyThem -c 'import sys;print(sys.executable, sys.version.split()[0])')"

    # ------------------------------------------------------------- Thu vien
    Buoc 2 'Cài thư viện Python (lần đầu mất vài phút)'
    $vpy = Join-Path $Venv 'Scripts\python.exe'
    if (-not (Test-Path $vpy)) {
        & $pyExe @pyThem -m venv $Venv
        if ($LASTEXITCODE -ne 0) { Loi 'Không tạo được môi trường Python riêng (venv).' }
    }
    & $vpy -c 'import fastapi, uvicorn, psycopg, pandas, pyarrow, xgboost, sklearn' 2>$null
    if ($LASTEXITCODE -ne 0) {
        & $vpy -m pip install --disable-pip-version-check -q --upgrade pip
        & $vpy -m pip install --disable-pip-version-check -r (Join-Path $Goc 'requirements-web.txt')
        if ($LASTEXITCODE -ne 0) { Loi 'Cài thư viện thất bại (kiểm tra kết nối mạng rồi chạy lại).' }
    }
    Write-Host '      Đã đủ thư viện.'

    # ------------------------------------------------------------ PostgreSQL
    Buoc 3 'Cài PostgreSQL 16 + PostGIS (bản chạy trong thư mục, không cần quyền quản trị)'
    if (-not (Test-Path (Join-Path $PG 'bin\pg_ctl.exe'))) {
        $zip = Join-Path $Tai 'pgsql_windows_x64.zip'
        Tai-Ve "$Rel/pgsql_windows_x64.zip" $zip
        Write-Host '      Đang giải nén ...'
        $tar = Join-Path $env:SystemRoot 'System32\tar.exe'
        if (Test-Path $tar) { & $tar -xf $zip -C $RT } else { Expand-Archive $zip $RT -Force }
        if (-not (Test-Path (Join-Path $PG 'bin\pg_ctl.exe'))) { Loi 'Giải nén PostgreSQL thất bại.' }
    }
    $bin = Join-Path $PG 'bin'
    Write-Host "      $(& (Join-Path $bin 'postgres.exe') --version)"

    # ---------------------------------------------------------------- Du lieu
    Buoc 4 'Khởi tạo cơ sở dữ liệu và nạp dữ liệu (1–3 phút)'
    $fCong = Join-Path $RT 'cong.txt'
    $xong = Join-Path $RT 'da_nap_du_lieu.txt'
    if (-not (Test-Path (Join-Path $Data 'PG_VERSION'))) {
        if (Test-Path $Data) { Remove-Item $Data -Recurse -Force }
        & (Join-Path $bin 'initdb.exe') -D $Data -U postgres -A trust -E UTF8 --locale=C | Out-Null
        if ($LASTEXITCODE -ne 0) { Loi 'initdb thất bại.' }
        $cong = Cong-Trong
        Add-Content (Join-Path $Data 'postgresql.conf') "`nport = $cong`nlisten_addresses = 'localhost'"
        Set-Content $fCong $cong -Encoding ascii
        if (Test-Path $xong) { Remove-Item $xong }
    }
    $cong = (Get-Content $fCong).Trim()
    & (Join-Path $bin 'pg_isready.exe') -q -p $cong
    if ($LASTEXITCODE -ne 0) {
        # Chay qua Start-Process de PowerShell khong doi tien trinh postgres chay nen
        $p = Start-Process (Join-Path $bin 'pg_ctl.exe') -WindowStyle Hidden -PassThru -ArgumentList `
            '-D', "`"$Data`"", '-l', "`"$Data\server.log`"", '-w', '-t', '180', 'start'
        $p.WaitForExit()
        & (Join-Path $bin 'pg_isready.exe') -q -p $cong
        if ($LASTEXITCODE -ne 0) { Loi "Không khởi động được PostgreSQL, xem $Data\server.log" }
    }
    if (-not (Test-Path $xong)) {
        $bk = Join-Path $Tai 'khong_khi.backup'
        Tai-Ve "$Rel/khong_khi.backup" $bk
        & (Join-Path $bin 'dropdb.exe') -U postgres -p $cong --if-exists khong_khi
        & (Join-Path $bin 'createdb.exe') -U postgres -p $cong khong_khi
        if ($LASTEXITCODE -ne 0) { Loi 'Không tạo được CSDL khong_khi.' }
        Write-Host '      Đang nạp dữ liệu ...'
        & (Join-Path $bin 'pg_restore.exe') -U postgres -p $cong -d khong_khi --no-owner $bk
        $n = & (Join-Path $bin 'psql.exe') -U postgres -p $cong -d khong_khi -Atc 'SELECT count(*) FROM quan_trac'
        if ($LASTEXITCODE -ne 0 -or [int64]"$n".Trim() -le 0) { Loi 'Nạp dữ liệu thất bại.' }
        Set-Content $xong (Get-Date -Format s) -Encoding ascii
        Write-Host ("      Đã nạp {0:N0} dòng quan trắc." -f [int64]"$n".Trim())
    } else {
        Write-Host '      Dữ liệu đã có sẵn.'
    }

    # ------------------------------------------------------------------ Xong
    Buoc 5 'Hoàn tất'
    Remove-Item (Join-Path $Tai '*.part') -ErrorAction SilentlyContinue
    Write-Host '      Mở ứng dụng: bấm đúp chay_web.bat (trình duyệt tự mở http://127.0.0.1:8000).'
    Write-Host '      Có thể xoá thư mục runtime\tai_ve để giải phóng ~250 MB.'
    exit 0
} catch {
    Write-Host ''
    Write-Host "LỖI: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host 'Sửa xong thì chạy lại cai_dat.bat, các bước đã xong sẽ được bỏ qua.'
    exit 1
}
