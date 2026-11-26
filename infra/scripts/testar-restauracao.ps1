# Teste de restauração do RDS: RPO e RTO medidos, não presumidos.
#
#     powershell -ExecutionPolicy Bypass -File infra\scripts\testar-restauracao.ps1
#
# Restaura o banco para o ponto mais recente numa instância temporária,
# confere pela EC2 que os dados estão lá e apaga a instância. Não toca no
# banco em uso. Custo: uma db.t4g.micro por cerca de uma hora, menos de
# US$ 0,05.
#
# RPO: distância entre agora e o último ponto restaurável, o quanto de dado
#      se perderia se o banco sumisse neste instante.
# RTO: do pedido de restauração até a instância aceitar conexão.

$ErrorActionPreference = 'Stop'
$origem  = 'cinerini'
$destino = 'cinerini-restore-test'

function Aws { $out = & aws @args; if ($LASTEXITCODE) { throw "aws $($args -join ' ') falhou" }; $out }

$sg = Aws ec2 describe-security-groups --filters Name=group-name,Values=cinerini-db `
  --query 'SecurityGroups[0].GroupId' --output text
$instancia = Aws ec2 describe-instances `
  --filters Name=tag:Project,Values=cinerini Name=instance-state-name,Values=running `
  --query 'Reservations[0].Instances[0].InstanceId' --output text

$ultimo = [datetime](Aws rds describe-db-instances --db-instance-identifier $origem `
  --query 'DBInstances[0].LatestRestorableTime' --output text)
$rpo = (Get-Date) - $ultimo
Write-Host ("Ultimo ponto restauravel: {0:u}  (RPO {1:N0} s)" -f $ultimo.ToUniversalTime(), $rpo.TotalSeconds)

$inicio = Get-Date
Write-Host "Restaurando em $destino..."
Aws rds restore-db-instance-to-point-in-time `
  --source-db-instance-identifier $origem `
  --target-db-instance-identifier $destino `
  --use-latest-restorable-time `
  --db-instance-class db.t4g.micro `
  --db-subnet-group-name cinerini `
  --vpc-security-group-ids $sg `
  --no-publicly-accessible --no-multi-az `
  --backup-retention-period 0 `
  --tags Key=Project,Value=cinerini Key=Purpose,Value=restore-test | Out-Null

try {
  # O waiter da CLI desiste em 30 minutos; restauração costuma levar de 10 a 20.
  Aws rds wait db-instance-available --db-instance-identifier $destino
  $rto = (Get-Date) - $inicio
  Write-Host ("Instancia disponivel. RTO {0:mm\:ss}" -f $rto)

  $endpoint = Aws rds describe-db-instances --db-instance-identifier $destino `
    --query 'DBInstances[0].Endpoint.Address' --output text

  # Conferido de dentro da EC2, a única máquina que alcança o banco. A URL é
  # a de produção com o host trocado: mesma senha, que a restauração preserva.
  $conferir = @"
cd /opt/cinerini
url=`$(sed -n 's/^DATABASE_URL=//p' .env.api | sed 's/@[^:]*:/@$endpoint:/')
docker compose -f docker-compose.prod.yml run --rm -e DATABASE_URL="`$url" api python -c "
from sqlalchemy import text
from app.db import engine
with engine.connect() as c:
    for t in ('users', 'events', 'showings', 'tickets'):
        print(t, c.execute(text(f'select count(*) from {t}')).scalar())
"
"@
  $params = @{ commands = @($conferir) } | ConvertTo-Json -Compress
  $params | Out-File -Encoding ascii "$env:TEMP\restore-params.json"
  $cmd = Aws ssm send-command --instance-ids $instancia --document-name AWS-RunShellScript `
    --parameters "file://$env:TEMP\restore-params.json" --comment 'teste de restauracao' `
    --query 'Command.CommandId' --output text
  do {
    Start-Sleep -Seconds 5
    $status = & aws ssm get-command-invocation --command-id $cmd --instance-id $instancia --query Status --output text 2>$null
  } while ($status -in @('Pending', 'InProgress', 'Delayed', $null, ''))
  Write-Host "Contagem no banco restaurado ($status):"
  Aws ssm get-command-invocation --command-id $cmd --instance-id $instancia `
    --query StandardOutputContent --output text
}
finally {
  Write-Host "Apagando $destino..."
  & aws rds delete-db-instance --db-instance-identifier $destino `
    --skip-final-snapshot --delete-automated-backups | Out-Null
  & aws rds wait db-instance-deleted --db-instance-identifier $destino
  Write-Host 'Instancia temporaria apagada.'
}

Write-Host ''
Write-Host ("RPO: {0:N0} segundos  |  RTO: {1:mm\:ss}" -f $rpo.TotalSeconds, $rto)
