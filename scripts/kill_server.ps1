
$port = 8000
$tcp = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
if ($tcp) {
    $pid_ = $tcp.OwningProcess
    Stop-Process -Id $pid_ -Force
    Write-Host "Killed process $pid_ on port $port"
} else {
    Write-Host "No process on port $port"
}
