# Deploy na AWS

API em uma EC2 atrás do Caddy, banco no RDS, imagem no ECR, deploy pelo GitHub Actions sem chave de acesso. Toda a infraestrutura está em `infra/` (Terraform) e o que roda na máquina em `deploy/`. O porquê das escolhas está em `docs/DECISOES.md`, D38.

O front continua na Vercel, e o Render segue configurado (`render.yaml`) como reserva.

## Arquitetura

```mermaid
flowchart LR
  user([Navegador]) -->|HTTPS| vercel[Vercel<br/>front estático]
  user -->|HTTPS :443| caddy

  subgraph ec2 [EC2 t4g.micro · us-east-1a · Elastic IP]
    caddy[Caddy<br/>TLS Let's Encrypt] -->|HTTP, rede interna| api[API FastAPI<br/>porta não publicada]
  end

  api -->|5432, só do SG da EC2| rds[(RDS PostgreSQL 18<br/>db.t4g.micro · privado)]
  api -. logs awslogs .-> cw[CloudWatch Logs<br/>/cinerini/api, 7 dias]
  ec2 -. HealthCheck a cada minuto .-> alarms[Alarmes] --> sns[SNS → e-mail]

  gh[GitHub Actions] -->|OIDC, credencial temporária| ecr[ECR<br/>cinerini-api]
  gh -->|SSM Run Command| ec2
  ec2 -->|pull| ecr
  ec2 -->|segredos| ssm[SSM Parameter Store<br/>/cinerini/*]
```

| Peça | Recurso | Arquivo |
|---|---|---|
| Rede | VPC padrão, SG da API (80/443 públicas, 22 só do IP do administrador), SG do banco (5432 só do SG da API) | `infra/network.tf` |
| Máquina | EC2 t4g.micro, Amazon Linux 2023 arm64, IMDSv2 obrigatório, créditos de CPU `standard`, Elastic IP | `infra/ec2.tf` |
| Preparo da máquina | Docker, Compose fixo, 1 GB de swap, timer de saúde | `infra/user_data.sh.tftpl` |
| Banco | RDS PostgreSQL 18, gp3 20 GB criptografado, sem IP público, backup de 1 dia | `infra/rds.tf` |
| Imagens | ECR com tag imutável, varredura no push, retém as cinco últimas | `infra/ecr.tf` |
| Permissões | Role de deploy por OIDC, role da EC2 | `infra/github_oidc.tf`, `infra/ec2_role.tf` |
| Observabilidade | Log group, três alarmes, tópico SNS | `infra/monitoring.tf` |
| Runtime | Compose de produção, Caddyfile, script de deploy | `deploy/` |
| Pipeline | Testes → build arm64 → deploy | `.github/workflows/deploy-aws.yml` |

Endereço: `https://<ip-com-hífens>.sslip.io`, saída `api_domain` do Terraform. O sslip.io resolve o nome para o IP contido nele, o que dá ao Let's Encrypt um domínio válido sem registro próprio.

## Custo

Estimativa mensal em `us-east-1`, preço de tabela, antes de créditos:

| Recurso | US$/mês |
|---|---|
| RDS db.t4g.micro | 11,70 |
| RDS gp3 20 GB | 2,30 |
| EC2 t4g.micro | 6,10 |
| IPv4 público | 3,65 |
| EBS gp3 10 GB | 0,80 |
| ECR, logs, métrica customizada, alarmes, SNS | ~0,40 |
| **Total** | **~25** |

Ficam de fora de propósito: NAT Gateway (~32), Load Balancer (~16), Multi-AZ (dobra o RDS), endpoints de VPC (~7 cada). Parameter Store padrão, a chave `aws/ssm` e até dez alarmes não cobram.

A conta usa o plano gratuito com créditos, que limita a retenção de backup do RDS a um dia e encerra a conta ao fim do período se não houver upgrade.

## Segredos

| Parâmetro | Tipo | Origem |
|---|---|---|
| `/cinerini/secret-key` | SecureString | gerado à mão; assina sessões e QR. Trocá-lo invalida todo ingresso emitido |
| `/cinerini/db-password` | SecureString | gerado à mão; lido pelo Terraform por `ephemeral` e enviado ao RDS por `password_wo`, nunca gravado no estado |
| `/cinerini/tmdb-api-key` | SecureString | chave do TMDb |
| `/cinerini/cors-origins` | String | domínio do front |
| `/cinerini/db-host` | String | escrito pelo Terraform |

Os quatro primeiros existem antes do `terraform apply` e não são gerenciados por ele, para que nenhum valor passe pelo `terraform.tfstate`. Criação, sem o valor aparecer na tela nem no histórico:

```powershell
$v = python -c "import secrets; print(secrets.token_urlsafe(48))"
aws ssm put-parameter --name /cinerini/secret-key --type SecureString --value $v
$v = python -c "import secrets; print(secrets.token_urlsafe(32))"
aws ssm put-parameter --name /cinerini/db-password --type SecureString --value $v
Remove-Variable v
```

A senha do banco usa só `[A-Za-z0-9_-]` porque entra na `DATABASE_URL` sem escape. Trocar a senha: atualizar o parâmetro com `--overwrite`, incrementar `db_password_version` e aplicar. Trocar qualquer segredo da aplicação: atualizar o parâmetro e refazer o deploy, que regenera o `.env.api`.

## Subir do zero

Pré-requisitos: AWS CLI 2.32+ autenticada (`aws login`), Terraform 1.11+, um par de chaves em `~/.ssh/cinerini-aws`.

1. Criar os quatro parâmetros acima.
2. `infra/terraform.tfvars` a partir do `.example`: IP do administrador com `/32` e e-mail dos alarmes.
3. `terraform init && terraform apply` em `infra/`. Leva de 5 a 10 minutos, quase todos esperando o RDS.
4. Confirmar a assinatura do SNS no e-mail recebido.
5. Conferir que o `sub` em `github_oidc_subject` corresponde ao repositório. O GitHub emite `repo:<dono>@<id>/<repo>@<id>:ref:refs/heads/main`; um token recusado aparece no CloudTrail como `AssumeRoleWithWebIdentity` com `AccessDenied`, e o campo `userName` traz o `sub` exato.
6. Ajustar `ROLE_ARN` em `deploy-aws.yml` se a conta for outra, e fazer push na `main`.
7. Semear uma vez, de dentro da instância:

```bash
cd /opt/cinerini && docker compose -f docker-compose.prod.yml run --rm api python -m app.seed
```

8. Na Vercel, `VITE_API_URL` com a saída `api_domain` (com `https://`), e redeploy do front.

## Deploy

Push na `main` dispara `deploy-aws.yml`:

1. **test**: chama `ci.yml`, a suíte inteira num Postgres 18 de serviço. Falhou, nada é publicado.
2. **build**: runner `ubuntu-24.04-arm`, porque a EC2 é Graviton. Imagem marcada com o SHA completo do commit.
3. **deploy**: localiza a instância pela tag `Project=cinerini` e envia, por SSM Run Command, um comando que baixa `deploy/` do mesmo commit e executa `deploy.sh`. O script regenera `.env` e `.env.api` a partir do Parameter Store, aplica `alembic upgrade head` e só então troca os contêineres com `up -d --wait`. O job termina conferindo `/health` por HTTPS de fora.

A migration antes da troca é o que preserva a versão anterior no ar quando ela falha. O inverso não vale: migration que remove coluna quebra a versão em execução durante a janela entre migrar e trocar, e precisa ser feita em dois deploys.

A role de deploy só aceita a `main` deste repositório, só envia imagem para `cinerini-api` e só manda comando para instância com a tag do projeto, pelo documento `AWS-RunShellScript`.

## Rollback

*Actions → deploy-aws → Run workflow*, com o SHA completo de um commit cuja imagem ainda esteja no ECR (as cinco mais recentes):

```bash
aws ecr describe-images --repository-name cinerini-api \
  --query 'sort_by(imageDetails,&imagePushedAt)[].imageTags[0]' --output text
```

Testes e build são pulados, e compose e script vêm do mesmo commit da imagem. **Migration não é desfeita**: voltar para antes de uma migration exige `alembic downgrade` manual na instância antes do rollback.

## Dados de demonstração

O seed marca sessões pelas três semanas seguintes ao dia em que roda, e o catálogo só lista sessão futura. Passado esse prazo, o catálogo esvazia. Renovar, de dentro da instância:

```bash
cd /opt/cinerini && docker compose -f docker-compose.prod.yml run --rm api python -m app.seed --reset
```

O `--reset` apaga tudo antes de semear, inclusive ingressos vendidos.

## Acesso à instância

- **Session Manager:** console → EC2 → instância → *Conectar* → *Session Manager*, ou `aws ssm start-session --target <instance_id>` com o plugin instalado. Não usa porta.
- **SSH:** saída `ssh_command` do Terraform. Só aceita o IP em `admin_cidr`; com IP novo, atualizar o `terraform.tfvars` e aplicar.

Arquivos em `/opt/cinerini`. `.env.api` tem permissão 600.

## Observabilidade

Logs dos dois contêineres no log group `/cinerini/api`, um stream por contêiner, retenção de sete dias. Pelo terminal: `aws logs tail /cinerini/api --follow`.

| Alarme | Condição |
|---|---|
| `cinerini-api-health` | `GET /health` por HTTPS falhando por 3 minutos, ou métrica ausente |
| `cinerini-ec2-status` | `StatusCheckFailed` por 2 minutos |
| `cinerini-ec2-cpu` | CPU média acima de 80% por 15 minutos |

A métrica de saúde é publicada pela própria instância, a cada minuto, pelo timer `cinerini-health`, acessando o domínio público: cobre DNS, certificado, Caddy e API. Ausência de dado conta como falha, porque máquina parada não publica nada. Os três alarmes avisam também na volta ao normal.

## Apagar tudo

```bash
cd infra && terraform destroy
```

Remove EC2, Elastic IP, RDS (sem snapshot final), ECR com as imagens, roles, OIDC, alarmes, SNS e log group. Sobram, por não serem do Terraform:

- os quatro parâmetros criados à mão: `aws ssm delete-parameters --names /cinerini/secret-key /cinerini/db-password /cinerini/tmdb-api-key /cinerini/cors-origins`;
- a métrica `Cinerini/HealthCheck`, que expira sozinha sem novos dados e para de cobrar;
- os backups automáticos do RDS, apagados junto com a instância.

Antes de destruir, o front precisa voltar para o Render, ou fica sem API.

Conferência de sobra, por tag:

```bash
aws resourcegroupstaggingapi get-resources --tag-filters Key=Project,Values=cinerini
```
