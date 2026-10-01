param(
    [string]$Docker = 'docker',
    [string]$Image = 'domio:0.1.1'
)
$ErrorActionPreference = 'Stop'
$testId = 'domio-smoke-' + [Guid]::NewGuid().ToString('N').Substring(0, 10)
$broker = "$testId-broker"
$app = "$testId-app"
$volume = "$testId-data"
$configVolume = "$testId-config"

function Invoke-Docker {
    $DockerArgs = $args
    $output = & $Docker @DockerArgs
    if ($LASTEXITCODE -ne 0) { throw "Docker failed: $DockerArgs" }
    return $output
}

function Get-ServicePid([string]$service) {
    $status = Invoke-Docker exec $app s6-svstat "/run/service/$service"
    if ($status -notmatch 'up \(pid (\d+)[ )]') { throw "Service unavailable: $status" }
    return $Matches[1]
}

function Wait-Services {
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        try {
            $scgi = Get-ServicePid 'domio-scgi'
            $mqtt = Get-ServicePid 'domio-mqtt'
            Start-Sleep -Seconds 2
            if (($scgi -eq (Get-ServicePid 'domio-scgi')) -and
                ($mqtt -eq (Get-ServicePid 'domio-mqtt'))) { return }
        } catch { }
        Start-Sleep -Seconds 1
    }
    throw 'Services did not stabilize'
}

try {
    # No host networking or published ports: PLC broadcasts stay in Docker.
    Invoke-Docker run -d --name $broker eclipse-mosquitto:2 | Out-Null
    Invoke-Docker volume create $volume | Out-Null
    Invoke-Docker volume create $configVolume | Out-Null
    # Check first-install seeding, then simulate an upgrade from private /data.
    Invoke-Docker run --rm --network none -v "${volume}:/data" -v "${configVolume}:/config" --entrypoint /bin/sh $Image -ec 'sh /usr/local/bin/domio-init; cmp /config/config.ini /opt/domio-defaults/config.ini; cp /config/config.ini /data/config.ini; echo "; legacy marker" >> /data/config.ini; rm /config/config.ini; sh /usr/local/bin/domio-init; cmp /data/config.ini /config/config.ini'
    Write-Output 'PASS: default configuration and migration from /data'
    Invoke-Docker run -d --name $app --network "container:$broker" -v "${volume}:/data" -v "${configVolume}:/config" $Image | Out-Null
    Wait-Services
    $log = (Invoke-Docker logs $app 2>&1) -join "`n"
    Write-Output $log
    foreach ($service in @('domio-scgi', 'domio-mqtt')) {
        $before = Get-ServicePid $service
        Invoke-Docker exec $app s6-svc -k "/run/service/$service"
        Start-Sleep -Seconds 3
        Wait-Services
        if ($before -eq (Get-ServicePid $service)) { throw "$service did not restart" }
        Write-Output "PASS: restart $service"
    }
    # Edit through a separate container, as an external editor would do.
    Invoke-Docker run --rm --network none -v "${configVolume}:/config" --entrypoint /bin/sh $Image -ec 'echo "; external edit marker" >> /config/config.ini'
    Invoke-Docker exec $app sh -ec 'cmp /opt/domio/config.ini /config/config.ini; grep -q "external edit marker" /opt/domio/config.ini'
    $hash = Invoke-Docker exec $app sha256sum /config/config.ini
    Invoke-Docker stop -t 10 $app | Out-Null
    $exitCode = Invoke-Docker inspect --format '{{.State.ExitCode}}' $app
    if ($exitCode -ne '0') { throw "Unexpected container exit code: $exitCode" }
    Invoke-Docker rm $app | Out-Null
    Invoke-Docker run -d --name $app --network "container:$broker" -v "${volume}:/data" -v "${configVolume}:/config" $Image | Out-Null
    Wait-Services
    if ($hash -ne (Invoke-Docker exec $app sha256sum /config/config.ini)) {
        throw 'Configuration changed across container recreation'
    }
    Write-Output 'PASS: external editing, clean shutdown and existing config preserved over legacy config'
} finally {
    & $Docker logs --tail 30 $app
    & $Docker rm -f $app $broker | Out-Null
    & $Docker volume rm $volume $configVolume | Out-Null
}
