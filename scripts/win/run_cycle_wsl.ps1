$Repo = (Get-Location).Path
$WSLRepo = wsl.exe wslpath -a "$Repo"
wsl.exe bash -lc "cd '$WSLRepo' && python -c 'from src.orchestrator.cycle import run_cycle; run_cycle()'"
